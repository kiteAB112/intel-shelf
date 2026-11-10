"""Publish only the README status region; retry concurrent main updates safely."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
import tempfile

from readme_status import render, replace_status

ROOT = Path(__file__).resolve().parents[1]


def git(*args, cwd=None):
    return subprocess.check_output(['git', *args], cwd=cwd or ROOT, text=True, encoding='utf-8').strip()


def publish(directory, repository):
    run = json.loads((directory / 'run.json').read_text(encoding='utf-8'))
    if (run.get('run_kind') != 'scheduled' or run.get('status') != 'completed'
            or run.get('check_origin') != 'github-actions'):
        raise ValueError('Only a completed production Actions round may update README')
    if not re.fullmatch(r'[0-9a-f]{40}', run['code_sha']):
        raise ValueError('Invalid observation code SHA')
    if not re.fullmatch(r'[A-Za-z0-9_-]+', run['run_id']):
        raise ValueError('Invalid production run ID')
    git('fetch', 'origin', 'state')
    state_sha = git('rev-parse', 'FETCH_HEAD')
    published = {name: json.loads(git('show', state_sha + ':' + name))
                 for name in ('run.json', 'status.json', 'maintenance-tasks.json')}
    if published['run.json'] != run:
        raise ValueError('README must summarize the latest published production round')
    catalog = json.loads(git('show', run['code_sha'] + ':sources/catalog.json'))
    body = render(catalog, published['status.json'], run, published['maintenance-tasks.json'],
                  repository, datetime.now(timezone.utc))
    for attempt in range(3):
        git('fetch', 'origin', 'main')
        main = git('rev-parse', 'FETCH_HEAD')
        with tempfile.TemporaryDirectory(prefix='intel-readme-') as parent:
            checkout = Path(parent) / 'worktree'
            git('worktree', 'add', '--detach', str(checkout), main)
            try:
                path = checkout / 'README.md'
                original = path.read_text(encoding='utf-8')
                updated = replace_status(original, body)
                if updated == original:
                    print('README already describes this observation')
                    return
                with path.open('w', encoding='utf-8', newline='\n') as stream:
                    stream.write(updated)
                git('add', '--', 'README.md', cwd=checkout)
                git('commit', '-m', 'Update source status (' + run['run_id'] + ')', cwd=checkout)
                try:
                    git('push', 'origin', 'HEAD:refs/heads/main', cwd=checkout)
                    print('Updated README from production round:', run['run_id'])
                    return
                except subprocess.CalledProcessError:
                    if attempt == 2:
                        raise
            finally:
                git('worktree', 'remove', '--force', str(checkout))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('directory', type=Path)
    parser.add_argument('--repository', required=True, help='owner/name of this repository or fork')
    args = parser.parse_args()
    publish(args.directory, args.repository)


if __name__ == '__main__':
    main()
