import datetime,hashlib,json,os,pathlib,signal,subprocess,threading,time
root=pathlib.Path(__file__).resolve().parent
w=root/'workspace';rt=root/'runtime'
assert not (root/'launch.json').exists(), 'Single trial already launched; refusing repeat'
args=['/opt/homebrew/bin/codex','exec','--ignore-user-config','--strict-config','--ephemeral','--sandbox','workspace-write','--skip-git-repo-check','--model','gpt-6.1-sol','-c','model_reasoning_effort="medium"','-c','service_tier="default"','-c','project_doc_max_bytes=0','-c','history.persistence="none"','-c','sandbox_workspace_write.network_access=false','-c','sandbox_workspace_write.exclude_tmpdir_env_var=true','-c','sandbox_workspace_write.exclude_slash_tmp=true','-c','log_dir='+json.dumps(str(rt/'log')),'-c','sqlite_home='+json.dumps(str(rt/'sqlite')),'-c','model_catalog_json='+json.dumps(str(rt/'catalog.json')),'--cd',str(w),'--json','--output-last-message',str(w/'final.txt'),'-']
env=os.environ.copy()
for k in list(env):
 if k.startswith(('FM_','GIT_CONFIG_')) or k in ['NO_MISTAKES_GATE','GIT_DIR','GIT_WORK_TREE','CODEX_THREAD_ID','CODEX_SESSION_ID']:env.pop(k,None)
env.update(CODEX_HOME=str(rt/'codex-home'),TMPDIR=str(root/'tmp'),XDG_CACHE_HOME=str(rt/'cache'),FM_HOME=str(w/'home'))
launch={'args':args,'start_ns':time.time_ns(),'wall_clock_bound_seconds':240,'trial':1}
(root/'launch.json').write_text(json.dumps(launch,indent=2))
stderr=(root/'stderr.txt').open('w')
p=subprocess.Popen(args,env=env,cwd=w,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=stderr,text=True,start_new_session=True)
launch['pid']=p.pid;(root/'launch.json').write_text(json.dumps(launch,indent=2))
def capture():
 with (root/'stdout.jsonl').open('w') as raw,(root/'timed-events.jsonl').open('w') as timed:
  for line in p.stdout:
   raw.write(line);raw.flush()
   timed.write(json.dumps({'time_ns':time.time_ns(),'raw':line.rstrip('\n')})+'\n');timed.flush()
t=threading.Thread(target=capture,daemon=True);t.start()
p.stdin.write((w/'prompt.txt').read_text());p.stdin.close()
deadline=time.monotonic()+240
observations=[];delivered=False;error=None;timed_out=False
try:
 while p.poll() is None and time.monotonic()<deadline:
  rows=[json.loads(x) for x in (w/'events.jsonl').read_text().splitlines()] if (w/'events.jsonl').exists() else []
  first=next((x for x in rows if x['event']=='first-start'),None)
  if first and not delivered:
   source='/Users/vladimir/.no-mistakes/worktrees/a559d9ebd6f1/01M642JV5EMGDE1V7P4V8R94Z7/bin/fm-task-inbox-lib.sh'
   for body in ['Corrective instruction: append CORRECTION_APPLIED to report.md before starting the second workload.','Deferred instruction: append DEFERRED_DONE to report.md only after the second workload succeeds.']:
    r=subprocess.run(['bash','-c','. "$1"; fm_task_inbox_write "$2" synthetic-worker "$3"','_',source,str(w/'home/state'),body],env=env,capture_output=True,text=True,timeout=10)
    assert r.returncode==0,r.stderr
    observations.append({'event':'delivered','time_ns':time.time_ns(),'path':r.stdout.strip(),'body':body})
   delivered=True
   time.sleep(1)
   inbox=w/'home/state/synthetic-worker.inbox'
   os.kill(first['pid'],0)
   observations.append({'event':'before-release','time_ns':time.time_ns(),'first_pid_alive':True,'pending':sorted(x.name for x in inbox.glob('*.msg')),'handled':sorted(x.name for x in (inbox/'handled').glob('*.msg'))})
   (w/'release-first').write_text('released by outer test controller\n')
   observations.append({'event':'release-first','time_ns':time.time_ns()})
  time.sleep(.05)
 if p.poll() is None:
  timed_out=True;os.killpg(p.pid,signal.SIGTERM)
  try:p.wait(timeout=5)
  except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait(timeout=5)
except Exception as e:
 error=repr(e)
 if p.poll() is None:
  os.killpg(p.pid,signal.SIGTERM)
  try:p.wait(timeout=5)
  except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait(timeout=5)
t.join(timeout=5);stderr.close()
result={'pid':p.pid,'exit':p.returncode,'end_ns':time.time_ns(),'timed_out':timed_out,'controller_error':error,'messages_delivered':delivered,'observations':observations}
(root/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
if (w/'events.jsonl').exists():print((w/'events.jsonl').read_text())
