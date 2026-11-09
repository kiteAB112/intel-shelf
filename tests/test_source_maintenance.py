import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from datetime import datetime, timezone, timedelta

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import maintain as m
from source_checks import validate


class SourceContracts(unittest.TestCase):
    def test_report_sources_require_dates_and_references(self):
        for sid in ('unit42', 'talos', 'checkpoint', 'dfir-report'):
            source = dict(check_profile=sid, format='rss')
            with self.subTest(source=sid):
                with self.assertRaises(ValueError):
                    validate(source, b'<rss><channel><item><title>x</title><link>https://example.test/a</link></item></channel></rss>', m.parse_date)
                validate(source, b'<rss><channel><item><title>x</title><link>https://example.test/a</link><pubDate>2026-11-09T00:00:00Z</pubDate></item></channel></rss>', m.parse_date)

    def test_kev_count_and_date_added_are_checked(self):
        obj = dict(catalogVersion='2026.11.09', dateReleased='2026-11-09T00:00:00Z', count=1,
                   vulnerabilities=[dict(cveID='CVE-2026-1234', dateAdded='2026-11-09')])
        source = dict(check_profile='cisa-kev', format='kev')
        validate(source, json.dumps(obj).encode(), m.parse_date)
        obj['count'] = 2
        with self.assertRaisesRegex(ValueError, 'count'):
            validate(source, json.dumps(obj).encode(), m.parse_date)
        obj['count'] = 1
        obj['vulnerabilities'][0].pop('dateAdded')
        with self.assertRaisesRegex(ValueError, 'dateAdded'):
            validate(source, json.dumps(obj).encode(), m.parse_date)

    def test_nvd_response_timestamp_is_not_freshness(self):
        source = dict(check_profile='nvd', format='nvd', stale_after_hours=24)
        body = json.dumps(dict(totalResults=1, vulnerabilities=[dict(cve=dict(id='CVE-2026-1234', published='2026-11-01T00:00:00Z', lastModified='2026-11-02T00:00:00Z'))])).encode()
        result = m.assess(source, {}, body, m.now())
        self.assertEqual(result['freshness'], 'unknown')
        self.assertIsNone(result['latest_item_at'])

    def test_circl_checks_the_actual_probe(self):
        body = b'{"cveMetadata":{"cveId":"CVE-2024-3400"},"containers":{"cna":{}}}'
        validate(dict(check_profile='circl', format='cve-record', probe_cve='CVE-2024-3400'), body, m.parse_date)
        with self.assertRaisesRegex(ValueError, 'different probe'):
            validate(dict(check_profile='circl', format='cve-record', probe_cve='CVE-2026-1234'), body, m.parse_date)

    def test_all_integrated_sources_have_a_profile(self):
        catalog = json.loads((m.ROOT / 'sources/catalog.json').read_text(encoding='utf-8'))
        for source in catalog:
            if source.get('endpoint'):
                self.assertEqual(source['check_profile'], source['id'])


class ProductionRounds(unittest.TestCase):
    def setUp(self):
        self.time = datetime(2026, 11, 9, tzinfo=timezone.utc)
        self.source = dict(id='test', format='rss', endpoint='https://example.test/feed', interval_hours=6, stale_after_hours=48)

    class Broken:
        def open(self, *args, **kwargs):
            raise OSError('offline')

    def test_rerunning_the_same_round_does_not_count_twice(self):
        row = m.check(self.source, {}, self.Broken(), self.time, run_id='r1')
        again = m.check(self.source, row, self.Broken(), self.time + timedelta(hours=7), run_id='r1')
        self.assertEqual(again['consecutive_failures'], 1)
        self.assertEqual(again['request_attempts'], row['request_attempts'])

    def test_validation_does_not_touch_baseline_or_production_streaks(self):
        state = {'test': dict(check_origin='github-actions', consecutive_failures=2, alerts=['fetch-or-parse-error'], incident_id='original')}
        before = json.dumps(state, sort_keys=True)
        out = m.run_checks([self.source], state, self.Broken(), self.time, 'validation', 'v1')
        self.assertEqual(json.dumps(state, sort_keys=True), before)
        self.assertNotIn('consecutive_failures', out['test'])
        self.assertNotIn('incident_id', out['test'])

    def test_switching_environment_starts_a_separate_baseline(self):
        old = {'test': dict(check_origin='hermes-cloud', consecutive_failures=7)}
        row = m.run_checks([self.source], old, self.Broken(), self.time, 'scheduled', 'r1')['test']
        self.assertEqual(row['consecutive_failures'], 1)

    def test_due_time_is_anchored_despite_a_late_start(self):
        row = m.check(self.source, {}, self.Broken(), self.time + timedelta(minutes=21), run_id='r1')
        self.assertEqual(m.parse_date(row['next_due_at']), self.time + timedelta(hours=6))
        row = m.check(self.source, row, self.Broken(), self.time + timedelta(hours=6, minutes=17), run_id='r2')
        self.assertEqual(row['consecutive_failures'], 2)

    def test_three_failures_call_for_diagnosis_not_unconditional_code_changes(self):
        row = {}
        for i in range(3):
            row = m.check(self.source, row, self.Broken(), self.time + timedelta(hours=6*i), run_id='r%d' % i)
        task = m.review_tasks([self.source], {'test': row}, [], self.time)['tasks'][0]
        self.assertEqual(task['action'], 'diagnose-required')
        self.assertEqual(task['consecutive_problem_checks'], 3)

    def test_known_external_block_waits_but_changed_evidence_reopens(self):
        row = dict(incident_id='incident', alerts=['fetch-or-parse-error', 'repeated-failure'], problem_kind='access', http_status=403, consecutive_failures=6)
        task = m.review_tasks([self.source], {'test': row}, [], self.time)['tasks'][0]
        feedback = [dict(source_id='test', incident_id='incident', task_id='older-task', reviewed_on='2026-11-09', outcome='blocked', problem_key=task['problem_key'], retry_after=(self.time + timedelta(days=1)).isoformat())]
        self.assertEqual(m.review_tasks([self.source], {'test': row}, feedback, self.time)['tasks'], [])
        row['http_status'] = 404
        self.assertEqual(len(m.review_tasks([self.source], {'test': row}, feedback, self.time)['tasks']), 1)
        row['http_status'] = 403
        self.assertEqual(len(m.review_tasks([self.source], {'test': row}, feedback, self.time + timedelta(days=2))['tasks']), 1)

    def test_normal_sources_do_not_call_ai_just_because_30_days_elapsed(self):
        source = dict(self.source, documentation_reviewed_on='2020-01-01')
        self.assertEqual(m.review_tasks([source], {'test': dict(alerts=[])}, [], self.time)['tasks'], [])

    def test_response_evidence_can_reproduce_a_parser_failure(self):
        class Response:
            status, url, headers = 200, 'https://example.test/feed', {'Content-Type': 'text/html'}
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self, size): return b'<html>Login</html>'
        class Opener:
            def open(self, *args, **kwargs): return Response()
        with tempfile.TemporaryDirectory() as directory:
            result = m.check(self.source, {}, Opener(), self.time, run_id='r1', evidence_dir=Path(directory)/'evidence')
            attempt = result['request_attempts'][0]
            self.assertEqual((Path(directory)/attempt['body_file']).read_bytes(), b'<html>Login</html>')
            self.assertEqual(result['problem_kind'], 'content')
            self.assertEqual(attempt['http_status'], 200)


if __name__ == '__main__':
    unittest.main()
