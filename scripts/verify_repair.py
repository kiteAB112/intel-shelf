"""Small gate for authorized maintenance branches; never modifies production state."""
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path.cwd()


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True, encoding='utf-8').strip()


def allowed(path):
    return path.startswith('tests/') or path in (
        'scripts/maintain.py', 'scripts/ioc_formats.py', 'scripts/source_checks.py',
        'scripts/directory_page.py', 'sources/catalog.json', 'data/feedback.json', 'data/repair.json')


def prepare():
    git('fetch', 'origin', 'main')
    repair = json.loads((ROOT / 'data/repair.json').read_text(encoding='utf-8'))
    if not only_readme_status_changed(repair['base_sha'], git('rev-parse', 'origin/main')):
        raise ValueError('Main changed; rebase maintenance onto latest main and revalidate')
    changed = git('diff', '--name-only', repair['base_sha'], 'HEAD').splitlines()
    if not changed or not all(allowed(path) for path in changed):
        raise ValueError('Maintenance branch includes files outside the authorized scope')
    sources = json.loads((ROOT / 'sources/catalog.json').read_text(encoding='utf-8'))
    if repair['source_id'] not in [s['id'] for s in sources if s.get('endpoint')]:
        raise ValueError('Repair target must be an integrated source')
    feedback = json.loads((ROOT / 'data/feedback.json').read_text(encoding='utf-8'))
    old_feedback = json.loads(git('show', repair['base_sha'] + ':data/feedback.json'))
    if feedback[:len(old_feedback)] != old_feedback:
        raise ValueError('Maintenance must append evidence, not rewrite history')
    old_catalog = {s['id']: s for s in json.loads(git('show', repair['base_sha'] + ':sources/catalog.json'))}
    new_catalog = {s['id']: s for s in sources}
    if set(old_catalog) != set(new_catalog) or any(old_catalog[sid] != new_catalog[sid] for sid in old_catalog if sid != repair['source_id']):
        raise ValueError('Only the target source configuration may change')
    matches = [r for r in feedback if r.get('task_id') == repair['task_id'] and r.get('source_id') == repair['source_id']]
    if not matches or matches[-1].get('outcome') != repair['outcome']:
        raise ValueError('Missing matching maintenance record')
    if not all(matches[-1].get(field) for field in ('incident_id', 'reviewed_on', 'evidence', 'decision', 'why', 'validation')):
        raise ValueError('Maintenance record lacks evidence or verification details')
    if repair['outcome'] not in ('fixed', 'improved', 'blocked', 'reviewed'):
        raise ValueError('Unknown maintenance outcome')
    if repair['outcome'] in ('blocked', 'reviewed') and any(p.startswith(('scripts/', 'sources/')) for p in changed):
        raise ValueError('Code changes need a fixed or improved outcome')
    return repair


def promote():
    repair = prepare()
    result = json.loads((ROOT / 'validation/run.json').read_text(encoding='utf-8'))
    if result['code_sha'] != git('rev-parse', 'HEAD') or result['run_kind'] != 'validation':
        raise ValueError('Validation does not match this candidate')
    if result['checked_sources'] != [repair['source_id']]:
        raise ValueError('Target was not actually checked')
    if repair['outcome'] == 'fixed' and not result['live_check_passed']:
        raise ValueError('Cannot publish a fixed claim while target still fails')
    feedback_path = ROOT / 'data/feedback.json'
    feedback = json.loads(feedback_path.read_text(encoding='utf-8'))
    record = [r for r in feedback if r.get('task_id') == repair['task_id'] and r.get('source_id') == repair['source_id']][-1]
    record['actions_validation'] = dict(code_sha=result['code_sha'], workflow_url=result['workflow_url'],
                                        tests_passed=True, live_check_passed=result['live_check_passed'],
                                        finished_at=result['finished_at'])
    feedback_path.write_text(json.dumps(feedback, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    git('add', '--', 'data/feedback.json')
    git('commit', '-m', 'Record Actions validation for ' + repair['task_id'])
    git('fetch', 'origin', 'main')
    latest = git('rev-parse', 'origin/main')
    if not only_readme_status_changed(repair['base_sha'], latest):
        raise ValueError('Main changed outside generated source status; revalidate')
    if latest != repair['base_sha']:
        git('merge', '--no-edit', latest)
    # Push remains fast-forward only; an unexpected concurrent change fails safely.
    git('push', 'origin', 'HEAD:refs/heads/main')
    print(json.dumps(dict(code_sha=result['code_sha'], outcome=repair['outcome'],
                          tests_passed=True, live_check_passed=result['live_check_passed'],
                          workflow_url=result['workflow_url']), ensure_ascii=False))


def only_readme_status_changed(base, latest):
    """Permit generated status drift, never human README edits or code changes.

    Keep this gate self-contained: Actions loads this file from trusted main,
    not imports from the candidate checkout.
    """
    if base == latest:
        return True
    ancestor = subprocess.run(['git', 'merge-base', '--is-ancestor', base, latest], cwd=ROOT)
    if ancestor.returncode != 0 or git('diff', '--name-only', base, latest).splitlines() != ['README.md']:
        return False
    def outside(sha):
        text = subprocess.check_output(['git', 'show', sha + ':README.md'], cwd=ROOT, text=True, encoding='utf-8')
        start, end = '<!-- intel-shelf-status:start -->', '<!-- intel-shelf-status:end -->'
        if text.count(start) != 1 or text.count(end) != 1:
            raise ValueError('Missing or ambiguous README status region')
        before, rest = text.split(start)
        _, after = rest.split(end)
        return before, after
    return outside(base) == outside(latest)


if __name__ == '__main__':
    if sys.argv[1] == 'prepare':
        repair = prepare()
        if os.environ.get('GITHUB_ENV'):
            with open(os.environ['GITHUB_ENV'], 'a', encoding='utf-8') as f:
                f.write('REPAIR_SOURCE=' + repair['source_id'] + '\n')
    elif sys.argv[1] == 'promote':
        promote()
    else:
        raise ValueError('Expected prepare or promote')
