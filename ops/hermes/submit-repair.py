"""Submit a scoped maintenance branch using the existing repository deploy key."""
import argparse
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', required=True)
    parser.add_argument('--task', required=True)
    parser.add_argument('--outcome', choices=('fixed', 'improved', 'blocked', 'reviewed'), required=True)
    args = parser.parse_args()
    if not re.fullmatch('[a-f0-9]{20}', args.task):
        parser.error('Task ID must come from the current maintenance queue')
    git('fetch', 'origin', 'main')
    base = git('rev-parse', 'origin/main')
    if git('rev-parse', 'HEAD') != base:
        raise RuntimeError('Start a fresh worktree at origin/main before editing')
    import sys
    sys.path.insert(0, str(ROOT / 'scripts'))
    from verify_repair import allowed
    changed = set(git('diff', '--name-only', 'HEAD').splitlines()) | set(git('ls-files', '--others', '--exclude-standard').splitlines())
    if not changed or not all(allowed(p) for p in changed):
        raise RuntimeError('Unexpected files changed; preserve them and submit only source maintenance')
    subprocess.run(['python3', '-m', 'unittest', 'discover', '-s', 'tests', '-q'], cwd=ROOT, check=True)
    branch = 'maintenance/' + args.task
    if git('branch', '--show-current') == 'main':
        raise RuntimeError('Repair in a separate maintenance worktree, not the monitored main checkout')
    if git('branch', '--show-current') != branch:
        git('branch', '-m', branch)
    repair = dict(source_id=args.source, task_id=args.task, outcome=args.outcome, base_sha=base)
    (ROOT / 'data/repair.json').write_text(json.dumps(repair, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    git('add', '--', *sorted(changed | {'data/repair.json'}))
    git('commit', '-m', 'Maintain ' + args.source + ' (' + args.task + ')')
    git('push', '-u', 'origin', branch)
    print('Submitted candidate:', git('rev-parse', 'HEAD'))
    print('Actions will test and recheck the target before fast-forward promotion; inspect the workflow result before claiming recovery.')
    print('https://github.com/kiteAB112/intel-shelf/actions')


if __name__ == '__main__':
    main()
