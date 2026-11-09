"""Publish only generated results to the state branch, without changing code."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
FILES = ('status.json', 'maintenance-tasks.json', 'run.json', 'DIRECTORY.md', 'index.html')


def git(*args, cwd=None):
    return subprocess.check_output(['git', *args], cwd=cwd or ROOT, text=True).strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    run = json.loads((args.directory / 'run.json').read_text(encoding='utf-8'))
    if run['run_kind'] != 'scheduled' or run['status'] != 'completed':
        raise ValueError('Only complete production rounds may publish state')
    for name in FILES:
        if not (args.directory / name).is_file():
            raise ValueError('Incomplete output: ' + name)
    # This worktree shares checkout's Git credential configuration, not its files.
    with tempfile.TemporaryDirectory(prefix='intel-state-') as parent:
        target = Path(parent) / 'worktree'
        exists = bool(git('ls-remote', '--heads', 'origin', 'state'))
        if exists:
            git('fetch', 'origin', 'state')
            git('worktree', 'add', '--detach', str(target), 'FETCH_HEAD')
        else:
            git('worktree', 'add', '--detach', '--no-checkout', str(target), 'HEAD')
            git('symbolic-ref', 'HEAD', 'refs/heads/state-publish', cwd=target)
            git('read-tree', '--empty', cwd=target)
        try:
            previous = target / 'run.json'
            if previous.exists():
                old = json.loads(previous.read_text(encoding='utf-8'))
                if old['run_id'] == run['run_id']:
                    print('Round already published:', run['run_id'])
                    return
                if old['started_at'] > run['started_at']:
                    raise ValueError('Refusing to replace a newer round')
            for name in FILES:
                shutil.copyfile(args.directory / name, target / name)
            git('add', '--', *FILES, cwd=target)
            git('commit', '-m', 'Source check ' + run['run_id'] + ' using ' + run['code_sha'][:7], cwd=target)
            git('push', 'origin', 'HEAD:refs/heads/state', cwd=target)
            print('Published state:', git('rev-parse', 'HEAD', cwd=target))
        finally:
            git('worktree', 'remove', '--force', str(target))


if __name__ == '__main__':
    main()
