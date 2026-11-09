"""Exercise branch isolation and promotion gates against disposable Git repositories."""
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import publish_state
import verify_repair


class ReleaseFlow(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = self.root / 'repo'
        self.repo.mkdir()
        self.bare = self.root / 'origin.git'
        self.command('git', 'init', '--bare', str(self.bare), cwd=self.root)
        self.command('git', 'init', '-b', 'main')
        self.git('config', 'user.name', 'Test')
        self.git('config', 'user.email', 'test@example.test')
        self.git('remote', 'add', 'origin', str(self.bare))
        self.write('sources/catalog.json', [dict(id='target', endpoint='https://example.test/feed')])
        self.write('data/feedback.json', [dict(source_id='old', decision='preserved')])
        self.git('add', '.')
        self.git('commit', '-m', 'base')
        self.git('push', '-u', 'origin', 'main')
        self.base = self.git('rev-parse', 'HEAD')

    def command(self, *args, cwd=None):
        return subprocess.check_output(args, cwd=cwd or self.repo, text=True, stderr=subprocess.STDOUT).strip()

    def git(self, *args):
        return self.command('git', *args)

    def write(self, name, data):
        path = self.repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data), encoding='utf-8')

    def candidate(self, outcome):
        self.git('checkout', '-b', 'maintenance/task')
        record = dict(source_id='target', task_id='task', incident_id='issue', reviewed_on='2026-11-09',
                      evidence=['https://example.test/docs'], decision='confirmed', why='root cause', validation='offline passed; Actions pending', outcome=outcome)
        self.write('data/feedback.json', [dict(source_id='old', decision='preserved'), record])
        self.write('data/repair.json', dict(source_id='target', task_id='task', outcome=outcome, base_sha=self.base))
        self.git('add', '.')
        self.git('commit', '-m', 'candidate')
        return self.git('rev-parse', 'HEAD')

    def test_state_is_separate_from_main_and_round_retry_is_idempotent(self):
        out = self.repo / 'runtime'
        out.mkdir()
        for name in publish_state.FILES:
            (out / name).write_text('{}', encoding='utf-8')
        self.write('runtime/run.json', dict(run_kind='scheduled', status='completed', run_id='r1', code_sha=self.base, started_at='2026-11-09T00:00:00Z'))
        with patch.object(publish_state, 'ROOT', self.repo), patch.object(sys, 'argv', ['publish_state', str(out)]), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(publish_state.git('remote', 'get-url', 'origin'), str(self.bare))
            publish_state.main()
            first = self.git('ls-remote', 'origin', 'refs/heads/state').split()[0]
            publish_state.main()
            second = self.git('ls-remote', 'origin', 'refs/heads/state').split()[0]
        self.assertEqual(first, second)
        self.assertEqual(self.git('rev-parse', 'main'), self.base)
        names = self.git('ls-tree', '-r', '--name-only', first).splitlines()
        self.assertEqual(set(names), set(publish_state.FILES))

    def test_validation_cannot_publish_production_state(self):
        out = self.repo / 'validation'
        out.mkdir()
        self.write('validation/run.json', dict(run_kind='validation', status='completed'))
        with patch.object(publish_state, 'ROOT', self.repo), patch.object(sys, 'argv', ['publish_state', str(out)]):
            with self.assertRaisesRegex(ValueError, 'production'):
                publish_state.main()

    def test_fixed_claim_requires_live_success_and_preserves_main_on_failure(self):
        candidate = self.candidate('fixed')
        self.write('validation/run.json', dict(code_sha=candidate, run_kind='validation', checked_sources=['target'], live_check_passed=False))
        with patch.object(verify_repair, 'ROOT', self.repo):
            with self.assertRaisesRegex(ValueError, 'fixed claim'):
                verify_repair.promote()
        self.assertEqual(self.git('ls-remote', 'origin', 'refs/heads/main').split()[0], self.base)

    def test_improvement_can_publish_without_claiming_recovery(self):
        candidate = self.candidate('improved')
        self.write('validation/run.json', dict(code_sha=candidate, run_kind='validation', checked_sources=['target'], live_check_passed=False, workflow_url='https://example.test/run', finished_at='2026-11-09T00:00:00Z'))
        with patch.object(verify_repair, 'ROOT', self.repo), contextlib.redirect_stdout(io.StringIO()):
            verify_repair.promote()
        feedback = json.loads((self.repo / 'data/feedback.json').read_text())
        self.assertFalse(feedback[-1]['actions_validation']['live_check_passed'])
        self.assertEqual(self.git('ls-remote', 'origin', 'refs/heads/main').split()[0], self.git('rev-parse', 'HEAD'))

    def test_history_cannot_be_silently_rewritten(self):
        self.candidate('reviewed')
        data = json.loads((self.repo / 'data/feedback.json').read_text())
        data[0]['decision'] = 'overwritten'
        self.write('data/feedback.json', data)
        self.git('add', '.')
        self.git('commit', '-m', 'rewrite history')
        with patch.object(verify_repair, 'ROOT', self.repo):
            with self.assertRaisesRegex(ValueError, 'rewrite history'):
                verify_repair.prepare()

    def test_gate_and_workflow_changes_are_outside_auto_maintenance_scope(self):
        self.assertFalse(verify_repair.allowed('scripts/verify_repair.py'))
        self.assertFalse(verify_repair.allowed('.github/workflows/check-sources.yml'))
        self.assertTrue(verify_repair.allowed('scripts/source_checks.py'))

    def test_gate_library_does_not_change_the_surrounding_actions_environment(self):
        self.candidate('reviewed')
        envfile = self.root / 'github-env'
        envfile.write_text('ORIGINAL=kept\n')
        with patch.object(verify_repair, 'ROOT', self.repo), patch.dict(os.environ, {'GITHUB_ENV': str(envfile)}):
            verify_repair.prepare()
        self.assertEqual(envfile.read_text(), 'ORIGINAL=kept\n')


if __name__ == '__main__':
    unittest.main()
