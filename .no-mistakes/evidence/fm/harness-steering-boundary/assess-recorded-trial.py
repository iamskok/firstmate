import datetime, hashlib, json, pathlib, shutil, subprocess
from zoneinfo import ZoneInfo
p=pathlib.Path('/Users/vladimir/.local/share/firstmate/data/harness-steering-boundary/autonomous-boundary-once')
out=pathlib.Path('/Users/vladimir/.no-mistakes/evidence/01M64634C9P9711DWYJR5PT2KT')
copy=out/'recorded-autonomous-trial';copy.mkdir(exist_ok=True)
m=json.loads((p/'manifest.json').read_text()); pre=json.loads((p/'prelaunch-manifest.json').read_text())
checks=[]
assert len(m['files'])==20
for entry in m['files']:
    f=pathlib.Path(entry['path']); relative=f.relative_to(p); data=f.read_bytes()
    assert len(data)==entry['bytes'] and hashlib.sha256(data).hexdigest()==entry['sha256'], f
    dest=copy/relative; dest.parent.mkdir(parents=True,exist_ok=True); dest.write_bytes(data)
(copy/'manifest.json').write_bytes((p/'manifest.json').read_bytes())
(copy/'outer.sb').write_bytes((p/'outer.sb').read_bytes())
checks.append('All 20 named artifact sizes and SHA-256 hashes match; copied named evidence without modifying the source evidence.')
for entry in pre['sources']:
    data=subprocess.check_output(['git','show',pre['candidate']+':'+entry['path']])
    assert hashlib.sha256(data).hexdigest()==entry['sha256']
    assert pathlib.Path(entry['path']).read_bytes()==data
    checks.append(entry['path']+': candidate source hash matches; current file bytes are identical.')
for ref in [pre['candidate'],'fd1a5b3668ad31c84eefe68140a76ac90e978f9b','eecd9060f3984e39d1ef0832837af3e5b45af351']:
    subprocess.run(['git','merge-base','--is-ancestor',ref,'HEAD'],check=True)
checks.append('The trial candidate and both retained repair commits are ancestors of current HEAD 4a81a203bf8fbc4f3cf3f9731c4dda9debc4239b.')
for file,key in [('workspace/emitted-inbox.md','emitted_instruction_sha256'),('workspace/prompt.txt','prompt_sha256'),('workspace/workload.py','workload_sha256')]:
    assert hashlib.sha256((p/file).read_bytes()).hexdigest()==pre[key]
prompt=(p/'workspace/prompt.txt').read_text(); emitted=(p/'workspace/emitted-inbox.md').read_text()
assert prompt.count(emitted)==1
prefix,suffix=prompt.split(emitted)
assert 'checkpoint' not in prefix.lower() and 'acknowledge' not in prefix.lower()
assert suffix.strip()=='Task: execute `python3 workload.py first`, then `python3 workload.py second`, as separate foreground commands, waiting for each to finish. After both commands finish, append a short result to report.md and finish. These are finite innocuous workloads.'
checks.append('Actual prompt contains the generated inbox section unchanged once. Its wrapper restricts scope and preserves the keyed choice; task instructions add no inbox timing or acknowledgement coaching.')
launch=json.loads((p/'launch.json').read_text()); args=launch['args']
assert args[0].endswith('/codex') and args[1]=='exec'
for arg in ['--ignore-user-config','--strict-config','--ephemeral','--sandbox','workspace-write','model_reasoning_effort="medium"','service_tier="default"','sandbox_workspace_write.network_access=false','sandbox_workspace_write.exclude_tmpdir_env_var=true','sandbox_workspace_write.exclude_slash_tmp=true','project_doc_max_bytes=0']:
    assert arg in args,arg
assert args[args.index('--model')+1]=='gpt-6.1-sol'
result=json.loads((p/'result.json').read_text())
assert result['pid']==launch['pid'] and result['exit']==0 and not result['timed_out'] and result['controller_error'] is None
assert launch['trial']==1 and (result['end_ns']-launch['start_ns'])/1e9<240
probe=json.loads((p/'sandbox-direct-probe.json').read_text())
assert probe['exit']==0 and json.loads(probe['stdout'])=={'inside_write':True,'outside_write_denied':True}
checks.append('Launch requests one ephemeral real Codex gpt-6.1-sol medium/default process with workspace-write sandbox and network disabled; existing-login status is recorded. Direct sandbox probe denies an outside write. Earlier outer/nested sandbox probes failed and are not counted as successful restriction evidence.')
checks.append('Sandbox launch flags and direct probe support restriction, not a claim of an independently observed complete filesystem write audit or a successful outer sandbox.')
raw=(p/'stdout.jsonl').read_text().splitlines(); timed=[json.loads(x) for x in (p/'timed-events.jsonl').read_text().splitlines()]
assert [r['raw'] for r in timed]==raw
assert all(a['time_ns']<=b['time_ns'] for a,b in zip(timed,timed[1:]))
stream=[json.loads(x) for x in raw]
assert sum(x['type']=='thread.started' for x in stream)==1
assert sum(x['type']=='turn.completed' for x in stream)==1
completed=[(i,x['item']) for i,x in enumerate(stream) if x['type']=='item.completed' and x['item']['type']=='command_execution']
assert all(item['exit_code']==0 for _,item in completed)
first_idx=next(i for i,item in completed if "python3 workload.py first" in item['command'])
read_idx=next(i for i,item in completed if 'repr(p.read_text())' in item['command'])
ack_idx=next(i for i,item in completed if 'mv home/state/synthetic-worker.inbox/001.msg' in item['command'])
second_start_idx=next(i for i,x in enumerate(stream) if x['type']=='item.started' and x['item'].get('type')=='command_execution' and 'python3 workload.py second' in x['item']['command'])
assert first_idx<read_idx<ack_idx<second_start_idx
read_item=stream[read_idx]['item']; ack_item=stream[ack_idx]['item']
assert read_item['aggregated_output'].index('001.msg')<read_item['aggregated_output'].index('002.msg')
assert ack_item['command'].index('Pending accepted instruction')<ack_item['command'].index('mv home/state/synthetic-worker.inbox/001.msg')<ack_item['command'].index('mv home/state/synthetic-worker.inbox/002.msg')
rows=[json.loads(x) for x in (p/'workspace/events.jsonl').read_text().splitlines()]
a,b,c,d=rows
assert [x['event'] for x in rows]==['first-start','first-end','second-start','second-end']
observed=result['observations']; deliveries=[x for x in observed if x['event']=='delivered']
assert len(deliveries)==2 and all(a['time_ns']<x['time_ns']<b['time_ns'] for x in deliveries)
before=next(x for x in observed if x['event']=='before-release')
release=next(x for x in observed if x['event']=='release-first')
assert before['first_pid_alive'] and before['pending']==['001.msg','002.msg'] and before['handled']==[]
assert before['time_ns']<release['time_ns']<b['time_ns']<c['time_ns']
assert a['pid']==b['pid'] and b['pending']==['001.msg','002.msg'] and b['handled']==[]
assert c['pending']==[] and c['handled']==['001.msg','002.msg']
assert 'CORRECTION_APPLIED' in c['report'] and 'Pending accepted instruction: append DEFERRED_DONE only after the second workload succeeds.' in c['report']
assert '\nDEFERRED_DONE\n' not in c['report']
assert all(x['decision']==a['decision'] for x in rows)
assert (p/'workspace/decision.status').read_text()==a['decision']
assert '\nDEFERRED_DONE\n' in (p/'workspace/report.md').read_text()
checks.append('Raw JSON event stream matches timestamped capture. One thread and one completed turn contain a successful first command, ordered reads, deferred-condition record then ordered moves, and only then a second command.')
checks.append('Both messages were delivered during the first command. It stayed alive, returned normally with both messages pending, and both were handled at second-command start. Deferred completion occurred after the second workload. The keyed choice stayed byte-identical.')
def local(ns): return datetime.datetime.fromtimestamp(ns/1e9,ZoneInfo('America/New_York')).isoformat()
checks.extend([f"Recorded first command: {local(a['time_ns'])} to {local(b['time_ns'])}.", f"Recorded second command starts: {local(c['time_ns'])}; child exits 0 at {local(result['end_ns'])}."])
checks.append('Identity limit: manifest run '+m['run']+' differs from current Test run 01M64634C9P9711DWYJR5PT2KT. This is historical supplemental evidence, applicable through verified source equality and ancestry, not a new live trial in this run.')
checks.append('Assessment: the record supports the missing behavior for this single synthetic Codex trial. It does not prove universal or future model compliance, enforcement, a counterfactual before-fix failure, or worker behavior on other models. No trial was repeated and no worker lifecycle was invoked.')
plan=pathlib.Path('/Users/vladimir/.no-mistakes/run-inputs/01M64634C9P9711DWYJR5PT2KT/verification-plan.txt').read_bytes()
assert hashlib.sha256(plan).hexdigest()=='1afdee35207af5ad9d010fddd437093f1f8b6f2a2fe5608555e054757667d1bb'
checks.append('Captured verification-plan bytes match the supplied SHA-256. No captured plan or source evidence was changed.')
(out/'recorded-trial-assessment.md').write_text('# Independent assessment of the recorded autonomous trial\n\n'+'\n\n'.join(checks)+'\n')
print('\n'.join(checks))
