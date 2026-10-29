import json,os,pathlib,sys,time
root=pathlib.Path(__file__).resolve().parent
stage=sys.argv[1]
def event(name):
 inbox=root/'home/state/synthetic-worker.inbox'
 row={'event':name,'time_ns':time.time_ns(),'pid':os.getpid(),'pending':sorted(p.name for p in inbox.glob('*.msg')),'handled':sorted(p.name for p in (inbox/'handled').glob('*.msg')),'report':(root/'report.md').read_text(),'decision':(root/'decision.status').read_text()}
 with (root/'events.jsonl').open('a') as f:f.write(json.dumps(row)+'\n');f.flush()
 print(name,flush=True)
event(stage+'-start')
if stage=='first':
 deadline=time.monotonic()+45
 while not (root/'release-first').exists():
  if time.monotonic()>deadline:raise SystemExit('first command release timed out')
  time.sleep(.05)
else:time.sleep(2)
event(stage+'-end')
