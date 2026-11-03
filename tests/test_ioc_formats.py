import json
import sys
from pathlib import Path
import unittest
from datetime import datetime, timezone
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from ioc_formats import records, summary, validate_indicator
from maintain import parse_date, assess, render, now


class IndicatorTests(unittest.TestCase):
    def test_first_row_provenance_and_defang(self):
        body = b'2026-11-03 01:00:00,a,ip,192.0.2.1,#test,https://x.com/a/status/1\n'
        rows, latest, info = summary(body, 'tweetfeed-csv', parse_date)
        self.assertEqual(len(rows), 1)
        self.assertEqual(info['reference_count'], 1)
        self.assertEqual(info['samples'][0]['value'], '192[.]0[.]2[.]1')
        self.assertIsNone(rows[0]['observed_at'])

    def test_idn_domain(self):
        validate_indicator('domain', '例子.test')

    def test_bad_indicator_quarantined(self):
        body = b'2026-11-03 01:00:00,a,ip,not-an-ip,#test,https://x.com/a/status/1\n'
        rows, latest, info = summary(body, 'tweetfeed-csv', parse_date)
        self.assertEqual(rows, [])
        self.assertEqual(info['rejected_record_count'], 1)
        r = assess(dict(format='tweetfeed-csv', stale_after_hours=48), {}, body, datetime(2026,11,3,tzinfo=timezone.utc))
        self.assertIn('high-invalid-record-rate', r['alerts'])

    def test_wrong_schema(self):
        with self.assertRaises(ValueError): records(b'<html>Access denied</html>', 'tweetfeed-csv')

    def test_c2_header_and_unknown_time(self):
        with self.assertRaises(ValueError): records(b'ip,label\n192.0.2.1,C2\n', 'c2-csv')
        rows, latest, info = summary(b'#ip,ioc\n192.0.2.1,Possible C2\n', 'c2-csv', parse_date)
        self.assertIsNone(latest)
        self.assertEqual(info['time_basis'], 'not-provided')

    def test_old_online_is_stale(self):
        body = json.dumps([dict(ip_address='192.0.2.1',port=443,status='online',first_seen='2024-01-01',last_online='2026-03-12',malware='test')]).encode()
        r = assess(dict(format='feodo-json', stale_after_hours=720), {}, body, datetime(2026,11,3,tzinfo=timezone.utc))
        self.assertIn('review-freshness', r['alerts'])
        self.assertEqual(r['samples'][0]['current_validity'], 'unknown')

    def test_ip_list_rejects_html(self):
        with self.assertRaises(ValueError): records(b'<html>Login</html>', 'ip-list')

    def test_render_does_not_remove_defanging(self):
        source = dict(id='c2',name='test',url='https://example.test',endpoint='https://example.test/feed',
                      format='c2-csv',categories=['test'],purpose='p',limits='l',interval_hours=24)
        row = dict(checked_at=now().isoformat(),access='reachable',content='valid',count=1,alerts=[],samples=[{'value':'192[.]0[.]2[.]1'}])
        text = render([source], {'c2':row})
        self.assertIn('`192[.]0[.]2[.]1`',text)
