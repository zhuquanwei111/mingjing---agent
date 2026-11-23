import assert from 'node:assert/strict';
import { fork } from 'node:child_process';
import { once } from 'node:events';
import { randomUUID } from 'node:crypto';
import { mkdirSync, writeFileSync, openSync, closeSync } from 'node:fs';
import { resolve } from 'node:path';
import { DatabaseSync } from 'node:sqlite';
import { setTimeout as delay } from 'node:timers/promises';
import pg from 'pg';
import { PostgresStore } from '@mastra/pg';

const out=process.env.LAB_OUT;
mkdirSync(out,{recursive:true});
const save=(name,d)=>writeFileSync(resolve(out,name+'.json'),JSON.stringify(d,null,2)+'\n');
const db=new pg.Pool({connectionString:process.env.DB_URL});
await db.query(`CREATE TABLE ops(scope text PRIMARY KEY,op text UNIQUE,run_id text,prompt text,call_id text,receipt text,
 version integer DEFAULT 1,status text DEFAULT 'prepared',held integer DEFAULT 3,spent integer DEFAULT 0,cancelled boolean DEFAULT false);
 CREATE TABLE entries(id serial PRIMARY KEY,scope text,pid int,mode text,call_id text);`);
const children = new Set();
function child(file,env,log) {
  const fd=openSync(resolve(out,log+'.log'),'a');
  const proc=fork(file,[],{env:{...process.env,...env},stdio:['ignore',fd,fd,'ipc']});
  closeSync(fd);children.add(proc);proc.once('exit',()=>children.delete(proc));return proc;
}
const witnessFile=resolve(out,'witness.sqlite');
const witness=child('witness.mjs',{WITNESS_DB:witnessFile},'witness');
const [{url}]=await once(witness,'message');
const view=new DatabaseSync(witnessFile,{readOnly:true});
async function poll(f,label,ms=60000) {
  const until=Date.now()+ms;
  while(Date.now()<until) {const val=await f();if(val)return val;await delay(100);}
  throw Error('Timed out: '+label);
}
async function scenario(scope) {
  const raw=scope==='native';
  const run=randomUUID(),op='op-'+randomUUID(),prompt='PROMPT_MARK_'+randomUUID();
  await db.query('INSERT INTO ops(scope,op,run_id,prompt) VALUES($1,$2,$3,$4)',[scope,op,run,prompt]);
  const product=async()=>(await db.query('SELECT * FROM ops WHERE scope=$1',[scope])).rows[0];
  const request=async(action,data={})=>{
    const res=await fetch(url+'/'+scope+'/'+action,{method:'POST',body:JSON.stringify(data)});assert.ok(res.ok);return res.json();
  };
  const read=(table)=>view.prepare('SELECT * FROM '+table+' WHERE scope=?').all(scope);
  const events=()=>read('events').map(e=>({...e,payload:JSON.parse(e.payload)}));
  const of=kind=>events().filter(e=>e.kind===kind);
  function counts() {
    const fees=read('fees');
    return {tools:of('submit-http').length,effects:read('effects').length,toolFees:fees.filter(f=>f.kind==='tool').length,
      models:of('model-http').length,modelFees:fees.filter(f=>f.kind==='model').length,deliveries:of('deliver').length};
  }
  async function snapshot(stage) {
    const schema='mastra_'+scope, tables={};
    const list=await db.query("SELECT tablename FROM pg_tables WHERE schemaname=$1 AND (tablename ILIKE '%workflow%' OR tablename ILIKE '%ownership%') ORDER BY tablename",[schema]);
    for(const {tablename} of list.rows) {
      assert.match(tablename,/^[a-zA-Z_0-9]+$/);
      tables[tablename]=(await db.query('SELECT * FROM "'+schema+'"."'+tablename+'"')).rows;
    }
    save(scope+'-'+stage+'-framework',tables);
    const reader=new PostgresStore({id:'reader',pool:db,schemaName:schema});
    const workflows=await reader.getStore('workflows');
    const outer=await workflows.loadWorkflowSnapshot({workflowName:'durable-agentic-loop',runId:run});
    const nestedRun=outer?.context?.['durable-agentic-execution']?.metadata?.nestedRunId || run;
    const nested=await workflows.loadWorkflowSnapshot({workflowName:'durable-agentic-execution',runId:nestedRun});
    save(scope+'-'+stage+'-logical',{run,nestedRun,outer,nested});
    const encoded=JSON.stringify({outer,nested});
    const physical=JSON.stringify(tables);
    const firstCall=of('model')[0]?.payload.call;
    const receipt=read('effects')[0]?.receipt;
    const markerScan=text=>({call:!!firstCall&&text.includes(firstCall),prompt:text.includes(prompt),receipt:!!receipt&&text.includes(receipt)});
    const owners=Object.entries(tables).filter(([name])=>name.includes('owner')).flatMap(([,rows])=>rows);
    const owner=owners.find(o=>o.runId===run);
    const scan={running:outer?.status==='running',rows:Number(!!outer)+Number(!!nested),run:!!outer,
      outerStatus:outer?.status,nestedStatus:nested?.status,nestedRun,outerSteps:Object.keys(outer?.context||{}),nestedSteps:Object.keys(nested?.context||{}),
      owner:owner?{id:owner.ownerId,generation:owner.generation}:null,physical:markerScan(physical),...markerScan(encoded)};
    const state={stage,product:await product(),counts:counts(),scan,tables:Object.fromEntries(Object.entries(tables).map(([k,v])=>[k,v.length]))};
    save(scope+'-'+stage,state);console.log(scope,stage,JSON.stringify({counts:state.counts,scan,tables:state.tables}));
    return state;
  }
  function worker(mode){
    const p=child('worker.mjs',{SCOPE:scope,MODE:mode,RUN_ID:run,WITNESS_URL:url,READER_VERSION:scope==='incompatible'&&mode==='recover'?'2':'1'},scope+'-'+mode);
    const exit=once(p,'exit').then(([code,signal])=>({code,signal}));
    return {p,exit};
  }
  const started=[];
  async function waitLive(entry,f,label) {
    return Promise.race([poll(f,label),entry.exit.then(end=>{throw Error(label+' worker exited '+JSON.stringify(end));})]);
  }
  try {
    await request('setup');
    const first=worker('start'); started.push(first.p);
    await waitLive(first,()=>of('submit').length,'initial dispatch');
    assert.deepEqual(counts(),{tools:1,effects:0,toolFees:0,models:1,modelFees:1,deliveries:0});
    await request('control',{enabled:true});
    await waitLive(first,()=>read('effects').length && counts().toolFees===1,'effect and fee');
    const before=await snapshot('before-kill');
    assert.equal(before.product.receipt,null);assert.equal(before.product.status,'inflight');
    assert.equal(before.scan.rows,2);assert.ok(before.scan.run&&before.scan.running);
    assert.ok(before.scan.owner&&before.scan.call);
    assert.deepEqual(before.scan.physical,{call:true,prompt:raw,receipt:false});
    assert.equal(before.scan.receipt,false);assert.equal(before.scan.prompt,raw);
    const originalCall=of('model')[0].payload.call;
    assert.equal(originalCall,before.product.call_id);
    first.p.kill('SIGKILL');assert.equal((await first.exit).signal,'SIGKILL');
    const allow=scope!=='unknown';
    await request('control',{visible:allow});
    await delay(16000);
    const second=worker('recover');started.push(second.p);assert.notEqual(first.p.pid,second.p.pid);
    save(scope+'-pids',{run,old:first.p.pid,new:second.p.pid,signal:'SIGKILL',forcedRecovery:false});
    if (raw||scope==='known') {
      await waitLive(second,()=>of('model').some(e=>e.payload.request.messages.some(m=>m.role==='tool')),'resumed model');
      const after=await snapshot('tool-returned');
      assert.equal(after.scan.prompt,raw);assert.equal(after.scan.receipt,raw);
      assert.deepEqual(after.scan.physical,{call:true,prompt:raw,receipt:raw});
      assert.ok(Number(after.scan.owner?.generation)>Number(before.scan.owner.generation));
      assert.notEqual(after.scan.owner?.id,before.scan.owner.id);
      await request('control',{release:true});assert.deepEqual(await second.exit,{code:0,signal:null});
      const models=of('model'),pair=models.at(-1).payload.request.messages.findLast(m=>m.role==='tool');
      assert.ok(models[0].payload.request.messages.some(m=>typeof m.content==='string'&&m.content.includes(prompt)));
      assert.deepEqual(JSON.parse(pair.content),{receipt:read('effects')[0].receipt});assert.equal(pair.tool_call_id,originalCall);
      const sentCalls=models.at(-1).payload.request.messages.flatMap(m=>m.tool_calls||[]).filter(t=>t.id===originalCall);
      assert.equal(sentCalls.length,1);assert.equal(sentCalls[0].function.name,'inspect');
      const c=counts();assert.equal(c.effects,1);assert.equal(c.modelFees,c.models);assert.equal(c.toolFees,c.tools);
      assert.equal(c.deliveries,1);assert.equal(of('deliver')[0].payload.receipt,read('effects')[0].receipt);
      if(raw) assert.ok(c.tools>1||c.models>2,'no native duplicate observed');
      else assert.deepEqual(c,{tools:1,effects:1,toolFees:1,models:2,modelFees:2,deliveries:1});
    } else {
      assert.deepEqual(await Promise.race([second.exit,delay(60000).then(()=>({timeout:true}))]),{code:0,signal:null});
      const state=await snapshot('held');
      assert.equal(state.product.status,scope==='unknown'?'waiting':scope);
      assert.equal(state.product.receipt,null);assert.equal(state.product.held,3);assert.equal(state.product.spent,0);
      const expected={tools:1,effects:1,toolFees:1,models:1,modelFees:1,deliveries:0};
      assert.deepEqual(counts(),expected);
      if(scope==='unknown'||scope==='incompatible') {
        if(scope==='unknown') await db.query('UPDATE ops SET cancelled=true WHERE scope=$1',[scope]);
        await request('control',{visible:true});
        const settlements=[];
        for(let i=0;i<2;i++) {
          const receipt=await request('lookup',{op});
          assert.ok(receipt.known);assert.equal(receipt.op,op);assert.equal(receipt.call,originalCall);
          const applied=await db.query("UPDATE ops SET held=0,spent=$2,receipt=$3 WHERE scope=$1 AND receipt IS NULL AND call_id=$4 AND op=$5 RETURNING held,spent",
              [scope,receipt.units,receipt.receipt,receipt.call,receipt.op]);settlements.push(applied.rowCount);
        }
        assert.deepEqual(settlements,[1,0]);const end=await product();
        assert.equal(end.held,0);assert.equal(end.spent,1);assert.equal(end.version,1);assert.deepEqual(counts(),expected);
        save(scope+'-settled',{settlements,product:end,counts:counts()});
      }
    }
    return {scope,ok:true,counts:counts()};
  } finally {
    for(const p of started)if(p.exitCode===null&&p.signalCode===null)p.kill('SIGKILL');
    save(scope+'-events',events());save(scope+'-fees',read('fees'));
    save(scope+'-entries',(await db.query('SELECT * FROM entries WHERE scope=$1 ORDER BY id',[scope])).rows);
  }
}
const results=[];
try {
  for(const scope of ['native','known','unknown','incompatible','mismatch']){
    try {results.push(await scenario(scope));}catch(e){console.error(scope,e);results.push({scope,ok:false,error:String(e)});}
  }
} finally {
  save('results',results);console.log('RESULTS',JSON.stringify(results));
  for(const p of children)p.kill('SIGKILL');
  await db.end();
}
process.exit(results.length===5&&results.every(r=>r.ok)?0:1);
