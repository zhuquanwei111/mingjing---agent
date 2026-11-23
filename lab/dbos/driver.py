"""Fault controller, observer and assertions. It has independent credentials for both PG instances."""
import base64
import json
import os
import pickletools
import re
import subprocess
import sys
import time
from pathlib import Path
from uuid import uuid4

import psycopg
from dbos import DBOSClient
from psycopg import sql
from psycopg.rows import dict_row

from rounds import SCHEMA, product

OUT=Path(os.environ['LAB_OUT'])
CASES=('naked','known','unknown','cancel','legacy','wrong')

def write(name,data):
    (OUT/name).write_text(json.dumps(data,ensure_ascii=False,indent=2,default=str))

def witness():
    return psycopg.connect(os.environ['WITNESS_DSN'],row_factory=dict_row)

def snapshot(scope):
    with product() as c:
        row=c.execute('SELECT * FROM task WHERE scope=%s',(scope,)).fetchone()
        events=c.execute('SELECT * FROM trace WHERE scope=%s ORDER BY seq',(scope,)).fetchall()
    with witness() as c:
        req=c.execute('SELECT * FROM requests WHERE scope=%s ORDER BY seq',(scope,)).fetchall()
        effects=c.execute('SELECT e.* FROM effects e JOIN jobs j USING(op) WHERE j.scope=%s',(scope,)).fetchall()
        fees=c.execute('SELECT f.* FROM fees f JOIN jobs j USING(op) WHERE j.scope=%s ORDER BY arrival',(scope,)).fetchall()
    return dict(task=row,trace=events,requests=req,effects=effects,fees=fees)

def records(s,kind):
    return [r['detail'] for r in s['requests'] if r['kind']==kind]

def counts(s):
    return [len(records(s,'arrival')),len(s['effects']),len(s['fees']),len(records(s,'model')),len(records(s,'delivery'))]

def wait(scope, process, condition):
    deadline=time.monotonic()+50
    while time.monotonic()<deadline:
        if process.poll() is not None:
            raise RuntimeError(f'{scope}: worker exited {process.returncode}')
        s=snapshot(scope)
        if condition(s):
            return s
        time.sleep(.15)
    write(scope+'-timeout.json',s)
    raise TimeoutError(f'{scope}: {s["task"]["state"]} {counts(s)}')

def worker(scope,mode,gen):
    # Receiver credentials are deliberately absent from both work processes.
    env={k:os.environ[k] for k in ('PATH','PRODUCT_DSN','ENGINE_DSN','HOME')}
    old_format='0' if scope=='legacy' else '1'
    env.update(GENERATION=gen,WRITER_FORMAT=old_format if gen=='one' else '2',
               READER_FORMATS=old_format if gen=='one' else '1,2',
               DBOS_DISABLE_ANONYMOUS_STATS='true',PYTHONUNBUFFERED='1')
    with (OUT/(scope+'-'+mode+'.log')).open('ab') as log:
        return subprocess.Popen([sys.executable,str(Path(__file__).with_name('rounds.py')),mode,scope],
                                stdout=log,stderr=subprocess.STDOUT,env=env)

def kill(p):
    if p.poll() is None:
        p.kill()
    p.wait(timeout=8)

def engine(client,scope):
    handle=client.retrieve_workflow('run-'+scope)
    st=handle.get_status()
    return dict(status=st.status,workflow=st.workflow_id,executor=st.executor_id,
                version=st.app_version,input=st.input,output=st.output,error=str(st.error) if st.error else None,
                steps=client.list_workflow_steps('run-'+scope))

def write_stage(scope,stage,s,client):
    s['engine']=engine(client,scope)
    write(scope+'-'+stage+'.json',s)
    print(scope,stage,counts(s),s['task']['state'],s['engine']['status'],flush=True)
    return s['engine']

def job_switch(scope,field):
    assert field in ('enabled','visible')
    with witness() as c:
        c.execute(sql.SQL('UPDATE scenario SET {}=true WHERE scope=%s').format(sql.Identifier(field)),(scope,))

def inspect_storage(client):
    with psycopg.connect(os.environ['ENGINE_DSN']) as c:
        tables=c.execute("SELECT tablename FROM pg_tables WHERE schemaname='dbos' ORDER BY 1").fetchall()
        raw={}
        for (table,) in tables:
            cmd=sql.SQL("SELECT to_jsonb(t) FROM dbos.{} t").format(sql.Identifier(table))
            raw[table]=[r[0] for r in c.execute(cmd)]
    assert raw.get('workflow_status') and raw.get('operation_outputs')
    write('engine-all-tables.json',raw)
    decoded={}
    for status in client.list_workflows():
        decoded[status.workflow_id]={'input':status.input,'output':status.output,'error':str(status.error) if status.error else None,
                                     'steps':client.list_workflow_steps(status.workflow_id)}
    assert all('run-'+scope in decoded for scope in CASES)
    write('engine-public-decoded.json',decoded)
    return raw,decoded

def searchable(raw):
    # Decode arbitrary base64 strings (DBOS 3.6.0 default uses pickle/base64) without executing pickle.
    text=json.dumps(raw,ensure_ascii=False)
    data=text.encode()
    for token in set(re.findall(r'[A-Za-z0-9+/]{12,}={0,2}',text)):
        try:
            decoded=base64.b64decode(token,validate=True)
            data+=b'\0'+decoded
            if decoded.startswith(b'\x80'):
                for _,value,_ in pickletools.genops(decoded):
                    if isinstance(value,str):
                        data+=b'\0'+value.encode()
                    elif isinstance(value,bytes):
                        data+=b'\0'+value
        except ValueError:
            pass
    return data

def run_case(scope,client):
    marker='PROMPT_MARK_'+uuid4().hex
    tool='lookup_'+uuid4().hex[:14]
    with witness() as c:
        c.execute('INSERT INTO scenario(scope,name,marker) VALUES(%s,%s,%s)',(scope,tool,marker))
    with product() as c:
        c.execute('INSERT INTO task(scope,name,marker) VALUES(%s,%s,%s)',(scope,tool,marker))
    p=worker(scope,'start','one')
    try:
        wait(scope,p,lambda s: any(t['kind']=='accepted' for t in s['trace']))
        before=snapshot(scope)
        assert counts(before)==[1,0,0,1,0]
        job_switch(scope,'enabled')
        first=wait(scope,p,lambda s: counts(s)==[1,1,1,1,0])
        h=write_stage(scope,'kill',first,client)
        assert h['status']=='PENDING' and first['task']['receipt'] is None and first['task']['spent']==0
        assert not any(st['function_name'].endswith('send_job') for st in h['steps'])
        old_pid=p.pid
        kill(p)
        assert p.returncode==-9
        p=worker(scope,'recover','two')
        restarted=wait(scope,p,lambda s: len([t for t in s['trace'] if t['kind']=='send-step'])==2)
        entries=[t for t in restarted['trace'] if t['kind']=='send-step']
        assert [t['pid'] for t in entries]==[old_pid,p.pid] and old_pid!=p.pid
        assert len({(t['wf'],t['step']) for t in entries})==1 and entries[0]['wf']=='run-'+scope
        if scope=='naked':
            end=wait(scope,p,lambda s: counts(s)==[2,1,2,1,0] and engine(client,scope)['status']=='SUCCESS')
            a,b=records(end,'arrival')
            assert a==b
        else:
            pending=wait(scope,p,lambda s: s['task']['state']=='pending')
            ph=write_stage(scope,'pending',pending,client)
            assert ph['status']=='PENDING' and counts(pending)==[1,1,1,1,0]
            assert (pending['task']['held'],pending['task']['spent'])==(3,0)
            if scope=='unknown':
                kill(p)
                p=worker(scope,'recover','two')
                # Wait for the fresh process to launch and begin startup recovery before rereading both DBs.
                wait(scope,p,lambda s: (OUT/(scope+'-recover.log')).read_text().count('WORKER_READY recover')>=2)
                nlook=len(records(pending,'lookup'))
                client.send('run-'+scope,'check','receipt',idempotency_key='unknown-recheck')
                end=wait(scope,p,lambda s: len(records(s,'lookup'))>nlook and engine(client,scope)['status']=='PENDING')
                assert records(end,'lookup')[-1]['found'] is False
                assert counts(end)==[1,1,1,1,0] and (end['task']['held'],end['task']['spent'])==(3,0)
                assert engine(client,scope)['status']=='PENDING' and end['task']['state']=='pending'
            elif scope=='cancel':
                with product() as c:
                    c.execute("UPDATE task SET active=false,state='cancelled' WHERE scope=%s",(scope,))
                client.cancel_workflow('run-'+scope)
                assert engine(client,scope)['status']=='CANCELLED'
                job_switch(scope,'visible')
                late=worker(scope,'late','two')
                try:
                    end=wait(scope,late,lambda s: len([t for t in s['trace'] if t['kind']=='settled'])==2)
                    assert sorted(t['detail']['new'] for t in end['trace'] if t['kind']=='settled')==[False,True]
                finally:
                    kill(late)
                assert counts(end)==[1,1,1,1,0] and engine(client,scope)['status']=='CANCELLED'
                assert end['task']['state']=='cancelled' and (end['task']['held'],end['task']['spent'])==(0,1)
            else:
                job_switch(scope,'visible')
                for _ in range(2):
                    client.send('run-'+scope,'available','receipt',idempotency_key='trigger-'+scope)
                end=wait(scope,p,lambda s: engine(client,scope)['status']=='SUCCESS')
                expected={'known':'delivered','legacy':'quarantine','wrong':'rejected'}[scope]
                writer,=[t for t in end['trace'] if t['kind']=='write_checkpoint']
                reader,=[t for t in end['trace'] if t['kind']=='read_checkpoint']
                assert writer['pid']==old_pid and reader['pid']==p.pid
                assert writer['detail']['written_format']==reader['detail']['seen']==(0 if scope=='legacy' else 1)
                assert reader['detail']['supported']==[1,2]
                assert end['task']['state']==expected and (end['task']['held'],end['task']['spent'])==(0,1)
                if scope=='known':
                    assert counts(end)==[1,1,1,2,1]
                    row=end['task']
                    assert row['first_run']!=row['resumed_run'] and row['conversation']==row['resumed_conversation']
                    m1,m2=records(end,'model')
                    call=m1['reply']['tool_calls'][0]['id']
                    returned,=[m for m in m2['request']['messages'] if m['role']=='tool']
                    assert call==row['call']==returned['tool_call_id']
                    assert end['effects'][0]['receipt'] in returned['content']
                    assert records(end,'delivery')==[{'call':call,'op':row['op'],'receipt':row['receipt']}]
                else:
                    assert counts(end)==[1,1,1,1,0]
        h2=write_stage(scope,'final',end,client)
        assert (h2['executor'],h2['version'])==(h['executor'],h['version'])
        assert end['task']['history']==first['task']['history']
        return end
    finally:
        kill(p)

def main():
    with product() as c:
        c.execute(SCHEMA)
    # Public client is initialized after the worker creates the system schema.
    from rounds import DBOS
    DBOS.migrate(os.environ['ENGINE_DSN'])
    client=DBOSClient(system_database_url=os.environ['ENGINE_DSN'])
    final={scope:run_case(scope,client) for scope in CASES}
    raw,decoded=inspect_storage(client)
    data=searchable(raw)
    public=json.dumps(decoded,default=str).encode()
    assert b'NAKED_INPUT_MARK_naked' in data and b'NAKED_INPUT_MARK_naked' in public
    forbidden=[]
    for scope,s in final.items():
        if scope!='naked':
            tokens=[s['task']['marker'],s['task']['call'],s['effects'][0]['receipt']]
            rec=json.dumps(s['requests'])
            assert all(token in rec for token in tokens)
            forbidden.extend(tokens)
    assert all(v.encode() not in data and v.encode() not in public for v in forbidden)
    write('summary.json',dict(count_order=['tool sends','effects','fees','model calls','deliveries'],
          counts={k:counts(s) for k,s in final.items()},protected_tokens=len(forbidden),
          naked_marker_present=True,head=os.environ['TEST_HEAD'],ci=os.environ['CI_RUN']))

if __name__=='__main__':
    main()
