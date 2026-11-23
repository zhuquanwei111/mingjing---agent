import assert from 'node:assert/strict';
import { setTimeout as delay } from 'node:timers/promises';
import { Agent } from '@mastra/core/agent';
import { Mastra } from '@mastra/core/mastra';
import { createDurableAgent } from '@mastra/core/agent/durable';
import { createTool } from '@mastra/core/tools';
import { PostgresStore } from '@mastra/pg';
import { createOpenAI } from '@ai-sdk/openai';
import pg from 'pg';
import { z } from 'zod';

const {SCOPE:scope, RUN_ID:runId, MODE:mode, DB_URL, WITNESS_URL} = process.env;
const raw = scope === 'native';
const db = new pg.Pool({connectionString:DB_URL});
const row = async () => (await db.query('SELECT * FROM ops WHERE scope=$1',[scope])).rows[0];
async function post(action,data) {
  const response = await fetch(WITNESS_URL+'/'+scope+'/'+action,{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify(data)});
  assert.ok(response.ok,action+' '+response.status);
  return response.json();
}
async function modelFetch(url,init) {
  const op = await row();
  if (!raw && (op.cancelled || ['waiting','mismatch','incompatible'].includes(op.status))) throw Error('model egress closed');
  const data=JSON.parse(init.body);
  if (!raw) {
    for (const msg of data.messages) {
      if (msg.role==='user') msg.content=msg.content.replace('prompt-ref:'+op.op,op.prompt);
      if (msg.role==='tool') {
        assert.equal(msg.tool_call_id,op.call_id); assert.ok(op.receipt);
        assert.ok(msg.content.includes('receipt-ref:'+op.op));
        msg.content=msg.content.replace('receipt-ref:'+op.op,op.receipt);
      }
    }
  }
  return fetch(url,{...init,body:JSON.stringify(data)});
}
const model = createOpenAI({apiKey:'local-synthetic',baseURL:WITNESS_URL+'/'+scope+'/v1',fetch:modelFetch}).chat('fixture');
const inspect = createTool({
  id:'inspect',description:'Submit an asynchronous inspection and return its confirmed receipt.',inputSchema:z.object({}),
  execute:async (_,ctx)=>{
    const call=ctx.agent.toolCallId;
    const original=await row();
    await db.query('INSERT INTO entries(scope,pid,mode,call_id) VALUES($1,$2,$3,$4)',[scope,process.pid,mode,call]);
    const claim=await db.query("UPDATE ops SET call_id=$2,status='inflight' WHERE scope=$1 AND status='prepared' RETURNING op",[scope,call]);
    if (claim.rowCount || raw) await post('submit',{op:original.op,call});
    if (mode==='start') await new Promise(()=>{});
    const found=await post('lookup',{op:original.op});
    let stop;
    if (!found.known) stop='waiting';
    else if (!raw && (found.op!==original.op || found.call!==original.call_id || call!==original.call_id)) stop='mismatch';
    else if (!raw && original.version!==Number(process.env.READER_VERSION)) stop='incompatible';
    if (stop) {
      await db.query('UPDATE ops SET status=$2 WHERE scope=$1',[scope,stop]);
      return await ctx.agent.suspend({status:stop,operation:original.op});
    }
    await db.query("UPDATE ops SET receipt=$2,spent=$3,held=0,status='confirmed' WHERE scope=$1",[scope,found.receipt,found.units]);
    return {receipt:raw?found.receipt:'receipt-ref:'+original.op};
  }
});
const agent = new Agent({id:'inspector',name:'Inspector',instructions:'Verify the inspection with the tool and report its receipt.',model,tools:{inspect}});
const durable=createDurableAgent({agent,maxSteps:3,shouldPersistSnapshot:()=>true});
const storage=new PostgresStore({id:'lab',connectionString:DB_URL,schemaName:'mastra_'+scope});
const mastra=new Mastra({agents:{inspector:durable},storage,logger:false});
try {
  await storage.init();
  const op=await row();
  console.log('worker',mode,process.pid,runId);
  const result=mode==='start'?await durable.stream(raw?op.prompt:'prompt-ref:'+op.op,{runId}):await durable.recover(runId,{closeOnSuspend:true});
  console.log('framework run',result.runId); assert.equal(result.runId,runId);
  let answer='';
  for await (const item of result.output.fullStream) {
    if (item.type==='error') throw Error(JSON.stringify(item));
    if (item.type==='text-delta') answer+=item.payload?.text || item.text || '';
  }
  console.log('stream done',JSON.stringify({answer}));
  const final=await row();
  if (final.status==='confirmed') {
    assert.equal(answer,'inspection confirmed');
    await post('deliver',{op:final.op,answer,receipt:final.receipt});
  }
  process.exit(0);
} catch(e) {console.error(e);await delay(50);process.exit(1);}
