"""Fetch completed Actions data using the existing repository SSH key. No model."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / 'runtime' / 'production'


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()


def sync():
    if git('branch', '--show-current') != 'main' or git('status', '--porcelain'):
        raise RuntimeError('Keep the cloud main checkout clean; repair in a separate worktree')
    git('pull', '--ff-only', '--quiet', 'origin', 'main')
    git('fetch', '--quiet', 'origin', 'state')
    sha = git('rev-parse', 'FETCH_HEAD')
    RUNTIME.mkdir(parents=True, exist_ok=True)
    result = {}
    for name in ('run.json', 'status.json', 'maintenance-tasks.json'):
        body = git('show', sha + ':' + name)
        result[name] = json.loads(body)
        temp = RUNTIME / (name + '.tmp-' + str(os.getpid()))
        temp.write_text(body + '\n', encoding='utf-8')
        temp.replace(RUNTIME / name)
    run = result['run.json']
    if run.get('status') != 'completed' or run.get('run_kind') != 'scheduled' or run.get('check_origin') != 'github-actions':
        raise RuntimeError('Latest state is not a complete production Actions round')
    return result


def main():
    data = sync()
    feedback = json.loads((ROOT / 'data/feedback.json').read_text(encoding='utf-8'))
    handled = {r.get('task_id') for r in feedback if r.get('task_id')}
    pending = sorted(t['task_id'] for t in data['maintenance-tasks.json']['tasks'] if t['task_id'] not in handled)
    token_path = ROOT / 'runtime' / 'monitor-token.json'
    old_token = json.loads(token_path.read_text(encoding='utf-8')) if token_path.exists() else []
    monitor_path = ROOT / 'runtime' / 'monitor-status.json'
    monitor = json.loads(monitor_path.read_text(encoding='utf-8')) if monitor_path.exists() else {}
    requested = bool(pending and pending != old_token)
    if monitor.get('run_id') == data['run.json']['run_id']:
        requested = requested or monitor.get('model_requested', False)
    monitor_path.write_text(json.dumps(dict(run_id=data['run.json']['run_id'], model_requested=requested)), encoding='utf-8')
    # Empty queue should not wake the agent merely because it used to be nonempty.
    if pending:
        token_path.write_text(json.dumps(pending), encoding='utf-8')
    else:
        pending = old_token
    print(json.dumps(pending))


if __name__ == '__main__':
    main()
