"""Observe a warm standby, then explicitly request recovery after death or a false alarm."""
import json
import os
import signal
import time
from uuid import uuid4

from dbos import DBOSClient
from driver import OUT, counts, engine, job_switch, kill, product, records, snapshot, wait, witness, worker, write, write_stage


def new_task(scope):
    marker='PROMPT_MARK_'+uuid4().hex
    name='lookup_'+uuid4().hex[:12]
    with product() as c:
        c.execute('INSERT INTO task(scope,name,marker) VALUES(%s,%s,%s)',(scope,name,marker))
    with witness() as c:
        c.execute('INSERT INTO scenario(scope,name,marker) VALUES(%s,%s,%s)',(scope,name,marker))


def run(scope,client):
    new_task(scope)
    old=worker(scope,'start','one')
    standby=None
    try:
        wait(scope,old,lambda s: any(t['kind']=='accepted' for t in s['trace']))
        standby=worker(scope,'standby','two')
        log=OUT/(scope+'-standby.log')
        wait(scope,standby,lambda _: 'WORKER_READY standby' in log.read_text())
        assert old.poll() is None and standby.poll() is None
        job_switch(scope,'enabled')
        ready=wait(scope,old,lambda s: counts(s)==[1,1,1,1,0])
        h=write_stage(scope,'before',ready,client)
        assert ready['task']['receipt'] is None and h['executor']=='round-'+scope and h['status']=='PENDING'
        assert all(not st['function_name'].endswith('send_job') for st in h['steps'])
        job_switch(scope,'visible')
        if scope=='takeover':
            kill(old)
            assert old.returncode==-9
        samples=[]
        start=time.monotonic()
        while True:
            current=snapshot(scope)
            state=engine(client,scope)
            elapsed=time.monotonic()-start
            samples.append(dict(seconds=elapsed,executor=state['executor'],status=state['status'],counts=counts(current),
                                old_exit=old.poll(),standby_exit=standby.poll(),
                                identity=[[t['pid'],t['wf'],t['step']] for t in current['trace'] if t['kind']=='send-step']))
            assert standby.poll() is None
            if elapsed>=8:
                break
            time.sleep(.3)
        automatic=any(any(e[0]==standby.pid for e in item['identity']) for item in samples)
        data=dict(samples=samples,automatic_observed=automatic,old_pid=old.pid,standby_pid=standby.pid)
        write(scope+'-observation.json',data)
        if scope=='false_recovery':
            assert old.poll() is None
        # The standby has been alive continuously since before the fault window.
        start_request=time.monotonic()-start
        os.kill(standby.pid,signal.SIGUSR1)
        wait(scope,standby,lambda s: 'EXPLICIT_RECOVER ' in log.read_text())
        returned=json.loads(log.read_text().split('EXPLICIT_RECOVER ',1)[1].splitlines()[0])
        if scope=='takeover' and not automatic:
            assert returned=={'ids':['run-'+scope],'error':None}
        if scope=='takeover':
            s=wait(scope,standby,lambda s: s['task']['state']=='delivered' and engine(client,scope)['status']=='SUCCESS')
            end=write_stage(scope,'final',s,client)
            assert end['executor']=='standby-'+scope and counts(s)==[1,1,1,2,1]
            assert (s['task']['held'],s['task']['spent'])==(0,1) and s['task']['first_run']!=s['task']['resumed_run']
            assert s['task']['conversation']==s['task']['resumed_conversation']
            model=records(s,'model')
            original=model[0]['reply']['tool_calls'][0]['id']
            response,=[m for m in model[1]['request']['messages'] if m['role']=='tool']
            assert response['tool_call_id']==original==s['task']['call'] and s['task']['receipt'] in response['content']
            assert records(s,'delivery')==[{'op':s['task']['op'],'call':original,'receipt':s['task']['receipt']}]
        else:
            # Observe either duplicate or effective suppression during a further bounded interval.
            deadline=time.monotonic()+8
            while time.monotonic()<deadline:
                s=snapshot(scope)
                if counts(s)==[2,1,2,1,0]:
                    break
                time.sleep(.15)
            end=write_stage(scope,'final',s,client)
            assert old.poll() is None and standby.poll() is None
            assert counts(s) in ([2,1,2,1,0],[1,1,1,1,0])
            if len(records(s,'arrival'))==2:
                a,b=records(s,'arrival')
                assert a==b
        entries=[t for t in s['trace'] if t['kind']=='send-step']
        assert len({(t['wf'],t['step']) for t in entries})==1 and entries[0]['pid']==old.pid
        pids=[t['pid'] for t in entries]
        if scope=='takeover' or (scope=='false_recovery' and counts(s)==[2,1,2,1,0] and end['executor']=='standby-'+scope):
            assert pids==[old.pid,standby.pid]
        if scope=='false_recovery' and counts(s)==[2,1,2,1,0]:
            # A re-enqueued workflow is available to any compatible worker. Attribute each actual send by PID.
            assert len(pids)==2 and pids[1] in (old.pid,standby.pid)
            acknowledgements=[t['pid'] for t in s['trace'] if t['kind']=='accepted']
            assert acknowledgements==pids
            data['second_sender']='standby' if pids[1]==standby.pid else 'original'
        data.update(explicit_at_seconds=start_request,returned_workflows=returned,final_status=end['status'],
                    final_executor=end['executor'],counts=counts(s),final_old_exit=old.poll(),final_standby_exit=standby.poll(),
                    reentry_pids=[t['pid'] for t in entries],op=s['task']['op'])
        write(scope+'-observation.json',data)
        return data
    finally:
        kill(old)
        if standby is not None:
            kill(standby)

if __name__=='__main__':
    db=DBOSClient(system_database_url=os.environ['ENGINE_DSN'])
    results={scope:run(scope,db) for scope in ('takeover','false_recovery')}
    write('takeover-summary.json',{k:{n:v for n,v in j.items() if n!='samples'} for k,j in results.items()})
