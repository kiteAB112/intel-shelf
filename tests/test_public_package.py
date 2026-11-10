"""Verify public status publishing and deployment isolation against disposable files."""
import contextlib
from datetime import datetime, timezone
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import publish_readme
from readme_status import START, END, render, replace_status


class ReadmeSummary(unittest.TestCase):
    def test_availability_limits_exclusions_and_fork_links(self):
        catalog = [dict(id='probe', name='Probe', endpoint='https://example.test/feed', url='https://example.test',
                        categories=['vulnerability'], interval_hours=24),
                   dict(id='history', name='History', endpoint='https://example.test/old', url='https://example.test/old',
                        categories=['ioc'], interval_hours=24, use_status='historical-only'),
                   dict(id='auth', name='Auth', categories=['ioc']),
                   dict(id='manual', name='Manual', categories=['ioc'], access_mode='manual')]
        stamp = '2026-11-10T00:00:00+00:00'
        state = {'probe':dict(checked_at=stamp, access='reachable', content='valid', count=1, freshness='unknown')}
        run = dict(finished_at=stamp, code_sha='a'*40, run_id='42')
        body = render(catalog, state, run, {'tasks':[]}, 'someone/fork', datetime(2026,11,10,13,tzinfo=timezone.utc))
        self.assertIn('入口可读取 **1**', body)
        self.assertIn('时效未知', body)
        self.assertIn('仅历史参考', body)
        self.assertIn('待接入', body)
        self.assertIn('人工查阅', body)
        self.assertIn('超过 12 小时', body)
        self.assertIn('https://github.com/someone/fork/blob/state/status.json', body)

    def test_replacement_preserves_all_human_text_and_rejects_ambiguous_markers(self):
        text = 'Human introduction.\n' + START + '\nold\n' + END + '\nHuman footer.\n'
        self.assertEqual(replace_status(text,'new'), text.replace('\nold\n','\nnew\n'))
        for invalid in ('No marker', text + START, END + START):
            with self.assertRaises(ValueError):
                replace_status(invalid, 'new')


class PublicPublishing(unittest.TestCase):
    def test_only_readme_is_pushed_and_local_worktree_is_untouched(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            origin, repo = root/'origin.git', root/'repo'
            def command(*args, cwd=None):
                return subprocess.check_output(args, cwd=cwd or repo, text=True, stderr=subprocess.STDOUT).strip()
            command('git','init','--bare',str(origin),cwd=root)
            command('git','init','-b','main',str(repo),cwd=root)
            command('git','config','user.name','Test')
            command('git','config','user.email','test@example.test')
            command('git','remote','add','origin',str(origin))
            (repo/'sources').mkdir()
            (repo/'sources/catalog.json').write_text('[]',encoding='utf-8')
            original = '# Project\n' + START + '\nold\n' + END + '\nHuman text.\n'
            (repo/'README.md').write_text(original,encoding='utf-8')
            command('git','add','.')
            command('git','commit','-m','base')
            base = command('git','rev-parse','HEAD')
            command('git','push','-u','origin','main')
            command('git','checkout','-b','state')
            run = dict(run_id='42',code_sha=base,run_kind='scheduled',status='completed',
                       check_origin='github-actions',finished_at='2026-11-10T00:00:00+00:00')
            for name,value in (('run.json',run),('status.json',{}),('maintenance-tasks.json',{'tasks':[]})):
                (repo/name).write_text(json.dumps(value),encoding='utf-8')
            command('git','add','run.json','status.json','maintenance-tasks.json')
            command('git','commit','-m','production state')
            command('git','push','origin','state')
            command('git','checkout','main')
            out = root/'runtime'
            out.mkdir()
            (out/'run.json').write_text(json.dumps(run),encoding='utf-8')
            (repo/'README.md').write_text(original+'Local uncommitted note.\n',encoding='utf-8')
            with patch.object(publish_readme,'ROOT',repo), contextlib.redirect_stdout(io.StringIO()):
                publish_readme.publish(out,'someone/fork')
                published = command('git','ls-remote','origin','refs/heads/main').split()[0]
                publish_readme.publish(out,'someone/fork')
                self.assertEqual(command('git','ls-remote','origin','refs/heads/main').split()[0],published)
            self.assertEqual(command('git','rev-parse','HEAD'),base)
            self.assertTrue((repo/'README.md').read_text(encoding='utf-8').endswith('Local uncommitted note.\n'))
            command('git','fetch','origin','main')
            self.assertEqual(command('git','diff','--name-only',base,'FETCH_HEAD'),'README.md')
            readme=command('git','show','FETCH_HEAD:README.md')
            self.assertIn('Human text.',readme)
            self.assertNotIn('Local uncommitted note.',readme)
            self.assertIn('someone/fork',readme)
            run['run_kind']='validation'
            (out/'run.json').write_text(json.dumps(run),encoding='utf-8')
            with patch.object(publish_readme,'ROOT',repo):
                with self.assertRaisesRegex(ValueError,'production'):
                    publish_readme.publish(out,'someone/fork')


class HermesInstall(unittest.TestCase):
    def test_installer_is_local_idempotent_and_never_exports_jobs(self):
        spec=importlib.util.spec_from_file_location('hermes_install',ROOT/'ops/hermes/install.py')
        installer=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(installer)
        with tempfile.TemporaryDirectory() as folder, contextlib.redirect_stdout(io.StringIO()):
            profile=Path(folder)/'profile'
            installer.install(ROOT,profile,dry_run=True)
            self.assertFalse(profile.exists())
            installer.install(ROOT,profile)
            installer.install(ROOT,profile)
            self.assertEqual(len(list(profile.rglob('*.py'))),3)
            self.assertFalse((profile/'cron/jobs.json').exists())
            target=profile/'scripts/intel-shelf-watch.py'
            target.write_text('local customization',encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'Existing file differs'):
                installer.install(ROOT,profile)
            self.assertEqual(target.read_text(encoding='utf-8'),'local customization')


if __name__ == '__main__':
    unittest.main()
