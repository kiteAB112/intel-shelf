"""Prepare a pinned full-code review for Hermes; never runs a production round."""
import hashlib
import importlib.util
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('intel_weekly_watch', Path(__file__).with_name('intel-shelf-watch.py'))
watch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(watch)


def build_plan(catalog, production, code_sha, stamp, handled_tasks=()):
    year, week, _ = stamp.astimezone(timezone(timedelta(hours=8))).isocalendar()
    audit_id = 'weekly-%d-W%02d' % (year, week)
    existing = {t['source_id']: t for t in production['maintenance-tasks.json']['tasks'] if t['task_id'] not in handled_tasks}
    sources = []
    excluded = []
    for source in catalog:
        sid = source['id']
        if not source.get('endpoint'):
            excluded.append(dict(source_id=sid, name=source['name'], reason='manual-reference' if source.get('access_mode') == 'manual' else 'not-integrated'))
            continue
        row = production['status.json'].get(sid, {})
        incident = audit_id + ':' + sid
        task = dict(source_id=sid, task_id=hashlib.sha256(incident.encode()).hexdigest()[:20],
                    incident_id=incident, run_id=row.get('run_id'), reasons=['weekly-script-review'],
                    problem_key=[['weekly-script-review'], None, None], action='review')
        if sid in existing:
            task = dict(existing[sid])  # Reuse a real pending issue rather than opening a duplicate.
        sources.append(dict(source_id=sid, name=source['name'], profile=source.get('check_profile'),
                            observation_code_run=row.get('run_id'), checked_at=row.get('checked_at'),
                            access=row.get('access'), content=row.get('content'), alerts=row.get('alerts', []),
                            task=task))
    return dict(mode='weekly-audit', audit_id=audit_id, prepared_at=stamp.isoformat(), code_sha=code_sha,
                production_run=production['run.json'], sources=sources, excluded_sources=excluded)


def main():
    production = watch.sync()
    catalog = json.loads((ROOT / 'sources/catalog.json').read_text(encoding='utf-8'))
    code_sha = watch.git('rev-parse', 'HEAD')
    feedback = json.loads((ROOT / 'data/feedback.json').read_text(encoding='utf-8'))
    handled = {r.get('task_id') for r in feedback if r.get('task_id')}
    plan = build_plan(catalog, production, code_sha, datetime.now(timezone.utc), handled)
    directory = ROOT / 'runtime' / 'weekly' / (plan['audit_id'] + '-' + code_sha[:7])
    directory.mkdir(parents=True, exist_ok=True)
    checkout = directory / 'code'
    if not checkout.exists():
        watch.git('worktree', 'add', '--detach', str(checkout), code_sha)
    actual = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=checkout, text=True).strip()
    if actual != code_sha:
        raise RuntimeError('Weekly checkout does not match the reviewed code SHA')
    test = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-q'],
                          cwd=checkout, text=True, capture_output=True)
    log = directory / 'tests.log'
    log.write_text(test.stdout + '\n' + test.stderr, encoding='utf-8')
    files = subprocess.check_output(['git', 'ls-files', '--', 'scripts', 'ops/hermes', '.github/workflows', 'tests', 'sources/catalog.json'],
                                    cwd=checkout, text=True).splitlines()
    for name, value in production.items():
        (directory / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    plan.update(checkout_path=str(checkout), code_files=files,
                offline_tests=dict(passed=test.returncode == 0, exit_code=test.returncode, log_path=str(log)),
                report_path=str(directory / 'report.md'))
    path = directory / 'plan.json'
    path.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    # Failed tests remain visible to the AI; a preflight alone never completes the review.
    print(json.dumps(dict(mode=plan['mode'], audit_id=plan['audit_id'], plan_path=str(path),
                          code_sha=code_sha, integrated_sources=[s['source_id'] for s in plan['sources']],
                          code_file_count=len(files), offline_tests_passed=test.returncode == 0,
                          instructions='Read the weekly-audit section of the repository maintenance Skill. Review every listed source even with an empty ordinary queue, then save and deliver the report.'), ensure_ascii=False))


if __name__ == '__main__':
    main()
