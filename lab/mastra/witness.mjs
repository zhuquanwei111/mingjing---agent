import { createServer } from 'node:http';
import { randomUUID } from 'node:crypto';
import { DatabaseSync } from 'node:sqlite';
import { setTimeout as delay } from 'node:timers/promises';

const db = new DatabaseSync(process.env.WITNESS_DB);
db.exec(`PRAGMA journal_mode=WAL;
 CREATE TABLE controls(scope TEXT PRIMARY KEY, enabled INTEGER DEFAULT 0, visible INTEGER DEFAULT 0, release INTEGER DEFAULT 0);
 CREATE TABLE events(seq INTEGER PRIMARY KEY, scope TEXT, kind TEXT, payload TEXT);
 CREATE TABLE jobs(op TEXT PRIMARY KEY,scope TEXT,call_id TEXT,receipt TEXT);
 CREATE TABLE fees(seq INTEGER PRIMARY KEY, scope TEXT, kind TEXT, units INTEGER);
 CREATE TABLE effects(op TEXT PRIMARY KEY,scope TEXT,receipt TEXT);`);
const log = (s,k,v) => Number(db.prepare('INSERT INTO events(scope,kind,payload) VALUES(?,?,?)').run(s,k,JSON.stringify(v)).lastInsertRowid);
const controls = s => db.prepare('SELECT * FROM controls WHERE scope=?').get(s);
setInterval(() => {
  db.exec('BEGIN');
  for (const j of db.prepare('SELECT j.* FROM jobs j JOIN controls c USING(scope) WHERE c.enabled AND j.receipt IS NULL').all()) {
    const receipt = 'EFFECT_MARK_' + randomUUID();
    db.prepare('INSERT INTO effects VALUES(?,?,?)').run(j.op,j.scope,receipt);
    db.prepare('UPDATE jobs SET receipt=? WHERE op=?').run(receipt,j.op);
    log(j.scope,'effect',{op:j.op,receipt});
  }
  db.exec("INSERT OR IGNORE INTO fees SELECT e.seq,e.scope,'tool',1 FROM events e JOIN controls c USING(scope) WHERE e.kind='submit-http' AND c.enabled");
  db.exec('COMMIT');
}, 50);

const app = createServer(async (req,res) => {
  try {
    let body = ''; for await (const part of req) body += part;
    const [,scope,action] = req.url.split('/');
    if (action === 'v1' || action === 'submit') {
      db.exec('BEGIN');
      const seq = log(scope,action==='v1'?'model-http':'submit-http',{method:req.method,path:req.url,body});
      if (action==='v1') db.prepare("INSERT INTO fees VALUES(?,?,'model',1)").run(seq,scope);
      db.exec('COMMIT');
    }
    const data = JSON.parse(body || '{}');
    const reply = (status,obj) => {res.writeHead(status,{'Content-Type':'application/json'});res.end(JSON.stringify(obj));};
    if (action === 'setup') {
      db.prepare('INSERT INTO controls(scope) VALUES(?)').run(scope);
      return reply(200,{ok:true});
    }
    if (action === 'control') {
      for (const key of ['enabled','visible','release']) {
        if (key in data) db.prepare('UPDATE controls SET '+key+'=? WHERE scope=?').run(Number(data[key]),scope);
      }
      log(scope,'control',data); return reply(200,{ok:true});
    }
    if (action === 'submit') {
      db.exec('BEGIN');
      log(scope,'submit',data);
      db.prepare('INSERT OR IGNORE INTO jobs(op,scope,call_id) VALUES(?,?,?)').run(data.op,scope,data.call);
      db.exec('COMMIT'); return reply(202,{accepted:true});
    }
    if (action === 'lookup') {
      const j = db.prepare('SELECT * FROM jobs WHERE op=? AND scope=?').get(data.op,scope);
      const known = Boolean(controls(scope).visible && j?.receipt);
      const out = known ? {known,op:j.op,call:scope==='mismatch'?'incorrect':j.call_id,receipt:j.receipt,units:1} : {known};
      log(scope,'lookup',out); return reply(200,out);
    }
    if (action === 'deliver') {log(scope,action,data);return reply(200,{received:true});}
    if (action === 'v1') {
      const tool = data.messages.findLast(m=>m.role==='tool');
      const call = tool ? null : 'call_'+randomUUID().replaceAll('-','');
      const seq=log(scope,'model',{request:data,call});
      if (tool) {
        const original=db.prepare('SELECT * FROM jobs WHERE scope=?').get(scope);
        const paired=data.messages.flatMap(m=>m.tool_calls || []).filter(t=>t.id===tool.tool_call_id);
        if (!original || paired.length!==1 || paired[0].function.name!=='inspect' ||
            JSON.parse(tool.content).receipt!==original.receipt || tool.tool_call_id!==original.call_id) {
          return reply(422,{error:'receipt or call mismatch'});
        }
      }
      if (tool) while (!controls(scope).release) await delay(50);
      const delta = tool ? {content:'inspection confirmed'} : {tool_calls:[{index:0,id:call,type:'function',function:{name:'inspect',arguments:'{}'}}]};
      const chunk = (d,reason) => ({id:'cmpl-'+seq,object:'chat.completion.chunk',created:1,model:'fixture',choices:[{index:0,delta:d,finish_reason:reason}]});
      res.writeHead(200,{'Content-Type':'text/event-stream'});
      for (const c of [chunk({role:'assistant'},null),chunk(delta,null),chunk({},tool?'stop':'tool_calls')]) res.write('data: '+JSON.stringify(c)+'\n\n');
      return res.end('data: [DONE]\n\n');
    }
    return reply(404,{});
  } catch(e) {console.error(e);res.writeHead(500);res.end('witness error');}
});
app.listen(0,'127.0.0.1',()=>process.send({url:'http://127.0.0.1:'+app.address().port}));
