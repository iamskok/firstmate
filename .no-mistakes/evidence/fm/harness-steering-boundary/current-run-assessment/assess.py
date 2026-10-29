import datetime
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import tempfile
from zoneinfo import ZoneInfo

ROOT = pathlib.Path('/Users/vladimir/.no-mistakes/worktrees/a559d9ebd6f1/01M64634C9P9711DWYJR5PT2KT')
OUT = pathlib.Path('/Users/vladimir/.no-mistakes/evidence/01M64634C9P9711DWYJR5PT2KT/current-run-assessment')
TRIAL = pathlib.Path('/Users/vladimir/.local/share/firstmate/data/harness-steering-boundary/autonomous-boundary-fork-recovery')
RUN = '01M64634C9P9711DWYJR5PT2KT'
TARGET = '4a81a203bf8fbc4f3cf3f9731c4dda9debc4239b'
ENV = {k: v for k, v in os.environ.items() if not k.startswith('FM_')}
notes = []

def call(args, **kwargs):
    return subprocess.check_output(args, cwd=ROOT, env=ENV, text=True, timeout=30, **kwargs)

def lib(filename, function, *args):
    return call(['bash', '-c', '. "$1"; shift; "$@"', '_', str(ROOT / 'bin' / filename), function, *map(str, args)])

def digest(data):
    return hashlib.sha256(data).hexdigest()

def section(text):
    return re.search(r'(?ms)^# Firstmate instruction inbox\n.*?(?=^# |\Z)', text)[0].rstrip() + '\n'

def localtime(ns):
    return datetime.datetime.fromtimestamp(ns / 1e9, ZoneInfo('America/New_York')).isoformat()

assert call(['git', 'rev-parse', 'HEAD']).strip() == TARGET
assert call(['git', 'status', '--porcelain']) == ''
manifest = json.loads((TRIAL / 'manifest.json').read_text())
pre = json.loads((TRIAL / 'prelaunch-manifest.json').read_text())
assert manifest['run'] == pre['run'] == RUN
assert manifest['candidate'] == pre['candidate'] == TARGET
assert len(manifest['files']) == 20
copied = OUT / 'autonomous-trial'
copied.mkdir(exist_ok=True)
checks = []
for item in manifest['files']:
    source = pathlib.Path(item['path'])
    relative = source.relative_to(TRIAL)
    data = source.read_bytes()
    assert len(data) == item['bytes'], relative
    assert digest(data) == item['sha256'], relative
    dest = copied / relative
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    checks.append({'path': str(relative), 'bytes': len(data), 'sha256': digest(data), 'verified': True})
shutil.copyfile(TRIAL / 'manifest.json', copied / 'manifest.json')
for source in pre['sources']:
    current = (ROOT / source['path']).read_bytes()
    committed = subprocess.check_output(['git', 'show', TARGET + ':' + source['path']], cwd=ROOT)
    assert current == committed
    assert digest(current) == source['sha256']
for ancestor in ['fd1a5b3668ad31c84eefe68140a76ac90e978f9b', 'eecd9060f3984e39d1ef0832837af3e5b45af351']:
    subprocess.run(['git', 'merge-base', '--is-ancestor', ancestor, TARGET], cwd=ROOT, check=True)
notes.append('The current-run and candidate identities match. All 20 named artifact sizes and SHA-256 hashes match. All three production source files match their prelaunch hashes and exact committed bytes; both retained repair commits remain ancestors.')

prompt = (TRIAL / 'workspace/prompt.txt').read_text()
emitted = (TRIAL / 'workspace/emitted-inbox.md').read_text()
assert digest(prompt.encode()) == pre['prompt_sha256']
assert digest(emitted.encode()) == pre['emitted_instruction_sha256']
assert digest((TRIAL / 'workspace/workload.py').read_bytes()) == pre['workload_sha256']
assert prompt.count(emitted.rstrip()) == 1

with tempfile.TemporaryDirectory(dir=ROOT, prefix='.issue-h-test-assessment-') as tmp:
    home = pathlib.Path(tmp)
    ENV['FM_HOME'] = str(home)
    ENV['TMPDIR'] = str(home)
    outputs = []
    for kind in ['ship', 'scout', 'secondmate']:
        args = ['bash', 'bin/fm-brief.sh', kind]
        if kind == 'secondmate':
            args += ['--secondmate', '--no-projects']
            ENV['FM_SECONDMATE_CHARTER'] = 'Supervise assigned synthetic work.'
        else:
            args += ['synthetic-project'] + (['--scout'] if kind == 'scout' else ['--mode', 'no-mistakes'])
        call(args)
        generated = (home / 'data' / kind / 'brief.md').read_text()
        (OUT / (kind + '-brief.md')).write_text(generated)
        guidance = section(generated)
        for expected in [
            'after a command returns and before starting the next expensive suite/campaign or a fresh blocking reattachment',
            'Move each read and accepted message to handled/ before starting that next command',
            "retain the action and its deferred condition in the task's existing status/report before acknowledging it",
            'never completion or additional authority',
            'separate matching resolution',
            'Do not interrupt an in-flight owned command',
            'or add inbox polling during a blocked wait',
        ]:
            assert expected in guidance, (kind, expected)
        task_inbox = home / 'state' / (kind + '.inbox')
        listing = re.search(r'list them with `([^`]+)`', guidance)[1]
        assert call(['bash', '-c', listing]) == ''
        (task_inbox / 'handled').mkdir(parents=True, exist_ok=True)
        assert call(['bash', '-c', listing]) == ''
        trial_inbox = str(TRIAL / 'workspace/home/state/synthetic-worker.inbox')
        assert guidance.replace(str(task_inbox), trial_inbox) == section(emitted), kind
        outputs.append(kind + ': production brief emits the same checkpoint/receipt/deferred-action/decision contract as the trial; absent and empty checkpoints exit silently.')
    record = lib('fm-task-inbox-lib.sh', 'fm_task_inbox_write', home / 'state', 'ship', 'Accepted synthetic instruction.').strip()
    assert lib('fm-task-inbox-lib.sh', 'fm_task_inbox_body', record) == 'Accepted synthetic instruction.'
    doorbell = lib('fm-task-inbox-lib.sh', 'fm_task_inbox_doorbell_line', record)
    for expected in ['list "$FM_TASK_INBOX"/*.msg', 'numeric order', 'mv each read and accepted message', 'handled/']:
        assert expected in doorbell
    (OUT / 'doorbell.txt').write_text(doorbell + '\n')
    outputs.append('The production inbox writer/body reader preserves the message; the doorbell uses ordered accepted-receipt wording and the existing glob and handled destination.')
    facet_root = home / 'facet-worktree'
    facet_root.mkdir()
    lib('fm-polytoken-lib.sh', 'fm_polytoken_write_facet', facet_root, home / 'state/ship.inbox')
    facet = (facet_root / '.polytoken/facets/firstmate-worker.md').read_text()
    for expected in ['read each message in numeric order', 'acknowledge each read and accepted message', "Follow the launch brief's command-boundary, deferred-action and keyed decision-resolution guidance"]:
        assert expected in facet
    (OUT / 'polytoken-worker-facet.md').write_text(facet)
    outputs.append('The production Polytoken facet emits accepted-receipt wording and delegates boundaries and keyed decisions to the launch brief.')
    script = pathlib.Path('/Users/vladimir/.local/share/firstmate/data/harness-steering-boundary/scenario.py')
    replay = call(['python3', str(script)])
    (OUT / 'scripted-protocol-transcript.txt').write_text(replay)
    outputs.append('The supplied offline enactment executed the current production writer, body reader, generated listing and decision folding in disposable ship/scout fixtures. It preserved command completion and deferred conditions with the keyed decision still open. The script controls receipt order and is not autonomous evidence.')
    (OUT / 'public-output-checks.txt').write_text('\n'.join(outputs) + '\n')
notes.append('Regenerated ship, scout and secondmate inbox sections match the trial input byte for byte after replacing only the owned inbox path. The prompt contains that section once and unchanged. Manual inspection of the complete wrapper and driver found scope restrictions and a two-command task, with no extra receipt-timing coaching or follow-up prompt.')

launch = json.loads((TRIAL / 'launch.json').read_text())
result = json.loads((TRIAL / 'result.json').read_text())
args = launch['args']
for flag in ['--ignore-user-config', '--strict-config', '--ephemeral', '--json']:
    assert flag in args
assert args[args.index('--sandbox') + 1] == 'workspace-write'
assert args[args.index('--model') + 1] == 'gpt-6.1-sol'
assert args[args.index('--cd') + 1] == str(TRIAL / 'workspace')
for setting in ['model_reasoning_effort="medium"', 'service_tier="default"', 'project_doc_max_bytes=0', 'history.persistence="none"', 'sandbox_workspace_write.network_access=false', 'sandbox_workspace_write.exclude_tmpdir_env_var=true', 'sandbox_workspace_write.exclude_slash_tmp=true']:
    assert setting in args
assert result['pid'] == launch['pid']
assert result['exit'] == 0 and not result['timed_out'] and result['controller_error'] is None
assert result['end_ns'] - launch['start_ns'] < 240 * 10**9
probe = json.loads((TRIAL / 'sandbox-direct-probe.json').read_text())
assert probe['exit'] == 0
assert json.loads(probe['stdout']) == {'inside_write': True, 'outside_write_denied': True}
auth = json.loads((TRIAL / 'isolated-auth-status.json').read_text())
assert auth['exit'] == 0 and 'Logged in using ChatGPT' in auth['stderr']
notes.append('The launcher requests one real ephemeral Codex gpt-6.1-sol medium/default child, with workspace-write, network disabled and no project instructions. Existing-login status is successful. The direct sandbox probe permits its inside write and denies its outside write; no credential contents were read.')

raw_lines = (TRIAL / 'stdout.jsonl').read_text().splitlines()
timed = [json.loads(line) for line in (TRIAL / 'timed-events.jsonl').read_text().splitlines()]
assert [event['raw'] for event in timed] == raw_lines
assert [event['time_ns'] for event in timed] == sorted(event['time_ns'] for event in timed)
events = [json.loads(line) for line in raw_lines]
assert sum(event['type'] == 'thread.started' for event in events) == 1
assert sum(event['type'] == 'turn.started' for event in events) == 1
assert sum(event['type'] == 'turn.completed' for event in events) == 1
completed = [event['item'] for event in events if event['type'] == 'item.completed' and event['item']['type'] == 'command_execution']
assert [item['id'] for item in completed] == ['item_' + str(i) for i in range(1, 9)]
assert all(item['exit_code'] == 0 and item['status'] == 'completed' for item in completed)
for i, needle in [(0, 'python3 workload.py first'), (1, 'find '), (2, 'read_text()'), (3, 'Deferred action accepted:'), (4, 'mv home/state/'), (5, 'python3 workload.py second'), (6, 'find '), (7, 'DEFERRED_DONE')]:
    assert needle in completed[i]['command'], (i, needle)
assert completed[2]['aggregated_output'].startswith("001.msg\n")
assert completed[2]['aggregated_output'].index('001.msg') < completed[2]['aggregated_output'].index('002.msg')
assert completed[4]['command'].index('/001.msg') < completed[4]['command'].index('/002.msg')
workload = [json.loads(line) for line in (TRIAL / 'workspace/events.jsonl').read_text().splitlines()]
assert [event['event'] for event in workload] == ['first-start', 'first-end', 'second-start', 'second-end']
first_start, first_end, second_start, second_end = workload
assert first_start['pid'] == first_end['pid']
assert first_end['pending'] == ['001.msg', '002.msg'] and first_end['handled'] == []
assert first_end['report'] == first_start['report'] == 'Fixture report.\n'
assert second_start['pending'] == [] and second_start['handled'] == ['001.msg', '002.msg']
assert 'CORRECTION_APPLIED\n' in second_start['report']
assert 'Deferred action accepted: append DEFERRED_DONE only after the second workload succeeds.\n' in second_start['report']
assert not re.search(r'^DEFERRED_DONE$', second_start['report'], re.M)
assert second_end['report'] == second_start['report']
assert re.search(r'^DEFERRED_DONE$', (TRIAL / 'workspace/report.md').read_text(), re.M)
expected_decision = 'needs-decision [key=unchanged]: separate choice unanswered\n'
assert all(event['decision'] == expected_decision for event in workload)
assert (TRIAL / 'workspace/decision.status').read_text() == expected_decision
observations = result['observations']
deliveries = [event for event in observations if event['event'] == 'delivered']
assert [pathlib.Path(event['path']).name for event in deliveries] == ['001.msg', '002.msg']
assert all(first_start['time_ns'] < event['time_ns'] < first_end['time_ns'] for event in deliveries)
before_release = next(event for event in observations if event['event'] == 'before-release')
assert before_release['first_pid_alive'] and before_release['pending'] == ['001.msg', '002.msg'] and before_release['handled'] == []
assert first_start['time_ns'] < deliveries[0]['time_ns'] < deliveries[1]['time_ns'] < before_release['time_ns'] < first_end['time_ns'] < second_start['time_ns'] < second_end['time_ns'] < result['end_ns']
notes.append('The matching raw and timestamped streams contain one thread and one completed turn. Both messages arrive while command one is running. It finishes normally with neither message receipted. The child then lists, reads 001 and 002 in order, writes the correction and deferred condition, and moves both records in numeric argument order before command two.')
notes.append('The second workload starts with both receipts handled, the correction applied, the deferred condition recorded and its completion still deferred. Only after the second workload succeeds does the child append DEFERRED_DONE. The keyed decision stays byte-identical throughout. All eight tool commands and the child exit successfully; no timeout or interruption is recorded.')
notes.append('Observed command-one interval: ' + localtime(first_start['time_ns']) + ' to ' + localtime(first_end['time_ns']) + '. Command two starts at ' + localtime(second_start['time_ns']) + '; child exits at ' + localtime(result['end_ns']) + '.')
notes.append('Confinement is supported by the explicit workspace sandbox, direct denial probe and complete visible command transcript. This is not a syscall-level audit of every runtime write. No live trial was repeated, no real worker or fleet state was accessed or controlled, and the external evidence was only read and copied.')
plan = pathlib.Path('/Users/vladimir/.no-mistakes/run-inputs/01M64634C9P9711DWYJR5PT2KT/verification-plan.txt')
assert digest(plan.read_bytes()) == '1afdee35207af5ad9d010fddd437093f1f8b6f2a2fe5608555e054757667d1bb'
notes.append('The captured offline plan still matches its supplied hash. This assessment uses the expressly authorized current-run outer-owned supplement; it does not reinterpret the plan or authorize another trial.')
prior_log = (OUT.parent / 'targeted-tests.log').read_text()
for filename in ['fm-brief.test.sh', 'fm-task-inbox.test.sh', 'fm-polytoken-harness.test.sh']:
    assert re.search(r'FM_TEST_END [^\n]*tests/' + re.escape(filename) + r' exit=0 [^\n]*gate_skip=false', prior_log)
assert 'FM_TEST_SUMMARY total=3 failed=0 skipped_gate=0' in prior_log
notes.append('The existing current-run targeted baseline completed fm-brief, fm-task-inbox and fm-polytoken-harness successfully with no gate skips. It was inspected and retained, not rerun. Fresh public-interface checks and the scripted protocol also succeeded. No lint, broad suite or other pipeline phase was executed.')
assert call(['git', 'status', '--porcelain']) == ''
assert not list(ROOT.glob('.issue-h-test-assessment-*'))
(OUT / 'hash-verification.json').write_text(json.dumps({'run': RUN, 'candidate': TARGET, 'verified_files': checks}, indent=2) + '\n')
notes.append('Assessment: the previously missing behavioral scenario is demonstrated by this single genuine autonomous trial from this run. Together with the five generated-interface scenarios it supports go for issue H. It does not prove universal model compliance, a before-fix counterfactual, or other harness behavior. No source changes were needed.')
(OUT / 'assessment.md').write_text('# Current-run autonomous evidence assessment\n\n' + '\n\n'.join(notes) + '\n')
print('\n\n'.join(notes))
