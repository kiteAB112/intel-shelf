import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('weekly_review', ROOT / 'ops/hermes/intel-shelf-weekly.py')
weekly = importlib.util.module_from_spec(spec)
spec.loader.exec_module(weekly)


class WeeklyReviewTests(unittest.TestCase):
    def setUp(self):
        self.catalog = json.loads((ROOT / 'sources/catalog.json').read_text(encoding='utf-8'))
        self.production = {'run.json': {'run_id': 'production-round'}, 'status.json': {},
                           'maintenance-tasks.json': {'tasks': []}}
        self.stamp = datetime(2026, 11, 15, 2, 30, tzinfo=timezone.utc)

    def test_empty_normal_queue_still_covers_every_integrated_source(self):
        plan = weekly.build_plan(self.catalog, self.production, 'code-sha', self.stamp)
        expected = {s['id'] for s in self.catalog if s.get('endpoint')}
        self.assertEqual({s['source_id'] for s in plan['sources']}, expected)
        self.assertEqual(len(plan['sources']), 11)
        self.assertEqual(len(plan['excluded_sources']), 4)
        self.assertEqual(plan['mode'], 'weekly-audit')

    def test_weekly_task_ids_are_stable_but_advance_next_week(self):
        first = weekly.build_plan(self.catalog, self.production, 'sha1', self.stamp)
        same = weekly.build_plan(self.catalog, self.production, 'sha2', self.stamp)
        later = weekly.build_plan(self.catalog, self.production, 'sha2', self.stamp.replace(day=22))
        self.assertEqual(first['sources'][0]['task']['task_id'], same['sources'][0]['task']['task_id'])
        self.assertNotEqual(first['sources'][0]['task']['task_id'], later['sources'][0]['task']['task_id'])

    def test_pending_source_issue_is_reused_without_reopening_handled_tasks(self):
        task = dict(source_id='nvd', task_id='pending', incident_id='existing')
        self.production['maintenance-tasks.json']['tasks'] = [task]
        plan = weekly.build_plan(self.catalog, self.production, 'sha', self.stamp)
        self.assertEqual(plan['sources'][0]['task'], task)
        plan = weekly.build_plan(self.catalog, self.production, 'sha', self.stamp, {'pending'})
        self.assertNotEqual(plan['sources'][0]['task']['task_id'], 'pending')


if __name__ == '__main__':
    unittest.main()
