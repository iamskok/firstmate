import hashlib, json, os, pathlib, re, subprocess, tempfile
root=pathlib.Path.cwd()
out=pathlib.Path('/Users/vladimir/.no-mistakes/evidence/01M64634C9P9711DWYJR5PT2KT')
prior=pathlib.Path('/Users/vladimir/.local/share/firstmate/data/harness-steering-boundary/autonomous-boundary-once')
env={k:v for k,v in os.environ.items() if not k.startswith('FM_')}
def call(args, **kw):
    return subprocess.check_output(args, cwd=root, env=env, text=True, **kw)
def lib(file, fn, *args):
    return call(['bash','-c','. "$1"; shift; "$@"','_',str(root/'bin'/file),fn,*map(str,args)])
def section(text):
    return re.search(r'(?ms)^# Firstmate instruction inbox\n.*?(?=^# |\Z)',text)[0].rstrip()
checks=[]
with tempfile.TemporaryDirectory(dir=root,prefix='.issue-h-test-') as tmp:
    home=pathlib.Path(tmp)
    env['FM_HOME']=str(home)
    for kind in ['ship','scout','secondmate']:
        args=['bash','bin/fm-brief.sh',kind]
        if kind=='secondmate':
            args+=['--secondmate','--no-projects']
            env['FM_SECONDMATE_CHARTER']='Supervise assigned work.'
        else:
            args+=['synthetic-project']+(['--scout'] if kind=='scout' else ['--mode','no-mistakes'])
        result=call(args)
        text=(home/'data'/kind/'brief.md').read_text()
        (out/(kind+'-brief.md')).write_text(text)
        guidance=section(text)
        for expected in ['after a command returns and before starting the next expensive suite/campaign or a fresh blocking reattachment',
            'Move each read and accepted message to handled/ before starting that next command',
            "retain the action and its deferred condition in the task's existing status/report before acknowledging it",
            'never completion or additional authority', 'separate matching resolution',
            'Do not interrupt an in-flight owned command', 'or add inbox polling during a blocked wait']:
            assert expected in guidance, (kind,expected)
        listing=re.search(r'list them with `([^`]+)`',guidance)[1]
        assert call(['bash','-c',listing])==''
        checks.append(kind+': generated checkpoint, accepted-receipt, deferred-action and separate-decision guidance; empty/absent inbox command exits silently.')
        if kind=='ship':
            old=section((prior/'workspace/emitted-inbox.md').read_text())
            oldpath=str(prior/'workspace/home/state/synthetic-worker.inbox')
            assert guidance.replace(str(home/'state/ship.inbox'),oldpath)==old
            checks.append('Current emitted inbox section equals the trial section byte for byte after substituting the task-owned inbox path.')
    rec=lib('fm-task-inbox-lib.sh','fm_task_inbox_write',home/'state','ship','A synthetic accepted instruction.').strip()
    bell=lib('fm-task-inbox-lib.sh','fm_task_inbox_doorbell_line',rec)
    assert 'mv each read and accepted message' in bell and 'numeric order' in bell
    assert 'list "$FM_TASK_INBOX"/*.msg' in bell and 'handled/' in bell
    (out/'doorbell.txt').write_text(bell+'\n')
    wt=home/'facet-worktree'; wt.mkdir()
    lib('fm-polytoken-lib.sh','fm_polytoken_write_facet',wt,home/'state/ship.inbox')
    facet=(wt/'.polytoken/facets/firstmate-worker.md').read_text()
    assert 'read each message in numeric order' in facet
    assert 'acknowledge each read and accepted message' in facet
    assert "Follow the launch brief's command-boundary, deferred-action and keyed decision-resolution guidance" in facet
    (out/'polytoken-worker-facet.md').write_text(facet)
    checks.append('Real inbox writer and doorbell formatter emit accepted-receipt reminder with the original inbox glob, numeric ordering and handled destination.')
    checks.append('Real Polytoken facet writer emits accepted-receipt guidance and points to the launch brief for boundaries and keyed decisions.')
    env['TMPDIR']=str(home)
    scenario=root/'unused'
    script=pathlib.Path('/Users/vladimir/.local/share/firstmate/data/harness-steering-boundary/scenario.py')
    transcript=call(['python3',str(script)])
    (out/'scripted-protocol-transcript.txt').write_text(transcript)
    checks.append('Replayed supplied scripted protocol using current production writer, body reader, generated listing command and decision folding; both ship and scout passed. This script chooses acknowledgement order; it is not autonomous behavior evidence.')
(out/'public-output-checks.txt').write_text('\n'.join(checks)+'\n')
print('\n'.join(checks))
