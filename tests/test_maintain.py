import importlib.util
from pathlib import Path
import unittest
from datetime import datetime, timezone, timedelta

spec = importlib.util.spec_from_file_location('maintain', Path(__file__).resolve().parents[1] / 'scripts/maintain.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class HealthTests(unittest.TestCase):
    def setUp(self):
        self.time = datetime(2026, 11, 2, tzinfo=timezone.utc)
        self.source = dict(id='test', format='rss', stale_after_hours=48, endpoint='https://example.test/feed', interval_hours=1)

    def test_html_200_is_not_feed(self):
        with self.assertRaises(ValueError):
            m.parse(b'<html><body>Login</body></html>', 'rss')

    def test_empty_feed_detected(self):
        r = m.assess(self.source, {}, b'<rss><channel/></rss>', self.time)
        self.assertIn('empty-data', r['alerts'])

    def test_regressed_old_timestamp(self):
        body = b'<rss><channel><item><pubDate>Mon, 01 Jan 2024 00:00:00 GMT</pubDate></item></channel></rss>'
        r = m.assess(self.source, {'latest_item_at':'2026-11-01T00:00:00Z','count':10}, body, self.time)
        self.assertTrue({'timestamp-regressed','review-freshness','large-count-change'} <= set(r['alerts']))

    def test_no_date_is_unknown(self):
        r = m.assess(dict(self.source, format='url-list'), {}, b'https://example.test/a\n', self.time)
        self.assertEqual(r['freshness'], 'unknown')

    def test_network_failure_retains_last_success(self):
        class Broken:
            def open(self, *args, **kwargs): raise OSError('offline')
        previous = dict(count=8, sha256='old', last_success_at='2026-10-01T00:00:00Z', consecutive_failures=2)
        r = m.check(self.source, previous, Broken(), self.time)
        self.assertEqual(r['count'], 8)
        self.assertEqual(r['last_success_at'], previous['last_success_at'])
        self.assertIn('repeated-failure', r['alerts'])
        self.assertEqual(r['access'], 'fetch-failed')

    def test_auth_pending_does_not_make_request(self):
        r = m.check(dict(self.source, endpoint=None), {}, None, self.time)
        self.assertEqual(r['access'], 'needs-auth-or-access-review')

    def test_three_failures_require_repair_including_parse_errors(self):
        for access in ('reachable', 'fetch-failed'):
            state = {'test': dict(access=access, consecutive_failures=2, alerts=['fetch-or-parse-error'])}
            source = dict(self.source, documentation_reviewed_on='2026-11-02')
            self.assertEqual(m.review_tasks([source], state, [], self.time)['tasks'], [])
            state['test']['consecutive_failures'] = 3
            task = m.review_tasks([self.source], state, [], self.time)['tasks'][0]
            self.assertEqual(task['action'], 'repair-required')
            self.assertEqual(task['consecutive_problem_checks'], 3)

    def test_content_alert_streak_increments_only_on_real_checks(self):
        class Response:
            status = 200
            url = 'https://example.test/feed'
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self, limit): return b'<rss><channel/></rss>'
        class Working:
            def open(self, *args, **kwargs): return Response()
        row = {}
        for i in range(3):
            row = m.check(self.source, row, Working(), self.time + timedelta(hours=i))
        self.assertEqual(row['alert_streaks']['empty-data'], 3)
        skipped = m.check(self.source, row, None, self.time + timedelta(hours=2, minutes=1))
        self.assertEqual(skipped['alert_streaks']['empty-data'], 3)
        task = m.review_tasks([self.source], {'test': row}, [], self.time)['tasks'][0]
        self.assertEqual(task['action'], 'repair-required')

    def test_interval_does_not_fake_new_check(self):
        previous = dict(checked_at=self.time.isoformat(), access='reachable')
        self.assertEqual(m.check(self.source, previous, None, self.time + timedelta(minutes=5)), previous)

    def test_recovery_clears_failure(self):
        class Response:
            status=200
            url='https://example.test/feed'
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self, limit): return b'<rss><channel><item><title>x</title><link>https://example.test/post</link></item></channel></rss>'
        class Working:
            def open(self, *args, **kwargs): return Response()
        r = m.check(self.source, dict(error='offline', consecutive_failures=4), Working(), self.time)
        self.assertNotIn('error', r)
        self.assertEqual(r['consecutive_failures'], 0)
        self.assertEqual(r['alerts'], [])

    def test_kev_fractional_timestamp(self):
        self.assertIsNotNone(m.parse_date('2026-10-30T17:02:45.3665Z'))

    def test_kev_parse_current_schema(self):
        body = (b'{"title":"CISA Catalog of Known Exploited Vulnerabilities",'
                b'"catalogVersion":"2026.10.04","dateReleased":"2026-10-04T18:52:56.0635Z","count":2,'
                b'"vulnerabilities":[{"cveID":"CVE-2026-11111","dateAdded":"2026-10-04"},'
                b'{"cveID":"CVE-2026-22222","dateAdded":"2026-10-03"}]}')
        count, latest = m.parse(body, 'kev')
        self.assertEqual(count, 2)
        self.assertEqual(latest, m.parse_date('2026-10-04T18:52:56.0635Z'))

    def test_kev_parse_rejects_record_without_cveid(self):
        body = b'{"dateReleased":"2026-10-04T00:00:00Z","vulnerabilities":[{"vendorProject":"x"}]}'
        with self.assertRaises(ValueError):
            m.parse(body, 'kev')

    def test_missing_article_link_is_not_ready(self):
        body = b'<rss><channel><item><title>x</title></item></channel></rss>'
        r = m.assess(self.source, {}, body, self.time)
        self.assertIn('missing-readable-items', r['alerts'])

    def test_auth_pending_has_no_fake_fetch_date(self):
        r = m.check(dict(self.source, endpoint=None), {}, None, self.time)
        self.assertNotIn('checked_at', r)
        self.assertIn('evaluated_at', r)

    def test_directory_separates_unavailable(self):
        source = dict(self.source, name='restricted', url='https://example.test', endpoint=None,
                      categories=['test'], purpose='p', limits='l')
        directory = m.render([source], {'test':{'access':'needs-auth-or-access-review'}})
        self.assertIn('已验证可读取 0 个', directory)
        before, after = directory.split('## 待接入或异常的来源')
        self.assertNotIn('[restricted]', before)
        self.assertIn('[restricted]', after)

    def test_expired_check_is_not_available(self):
        source = dict(self.source, name='expired', url='https://example.test', categories=['test'], purpose='p', limits='l')
        directory = m.render([source], {'test':dict(checked_at='2000-01-01T00:00:00Z',access='reachable',content='valid',count=1,alerts=[])})
        self.assertIn('已验证可读取 0 个', directory)

    def test_historical_source_stays_out_even_after_fetch_success(self):
        source = dict(self.source, name='historical',url='https://example.test',categories=['test'],purpose='p',limits='l',use_status='historical-only')
        row = dict(checked_at=m.now().isoformat(),access='reachable',content='valid',count=1,alerts=[])
        directory=m.render([source],{'test':row})
        self.assertIn('已验证可读取 0 个',directory)
        self.assertIn('仅历史参考',directory)


if __name__ == '__main__': unittest.main()
