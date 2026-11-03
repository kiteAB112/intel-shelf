import json
import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from query import identify, select_sources, cve_facts, indicator_matches, collect


class QueryTests(unittest.TestCase):
    def test_classification_and_defanging(self):
        for value, expected in [('cve-2024-3400',('cve','CVE-2024-3400')),('192[.]0[.]2[.]1',('ip','192.0.2.1')),
                                ('ExAmple.TEST.',('domain','example.test')),('A'*64,('sha256','a'*64)),
                                ('hxxps://example[.]test/A',('url','https://example.test/A'))]:
            self.assertEqual(identify(value),expected)

    def test_credentials_and_invalid_input_rejected(self):
        for value in ['https://user:secret@example.test','CVE-2024-3400; whoami','../secret','ftp://example.test']:
            with self.assertRaises(ValueError): identify(value)

    def test_company_skips_nc_and_all_contexts_skip_historical(self):
        catalog=[dict(id='a',capabilities=['ip'],query_mode='feed-exact',url='https://example.test',purpose='p',limits='l',endpoint='https://example.test/feed',usage_scope='noncommercial-research-only'),
                 dict(id='b',capabilities=['ip'],url='https://example.test',purpose='p',limits='l',use_status='historical-only')]
        self.assertEqual([r['skip_reason'] for r in select_sources(catalog,'ip','company')],['noncommercial-research-only','historical-only'])

    def test_wrong_cve_is_error_not_no_match(self):
        with self.assertRaises(ValueError):cve_facts('circl',{'cveMetadata':{'cveId':'CVE-2000-0001'}},'CVE-2024-3400')
        with self.assertRaises(ValueError):cve_facts('nvd',{'vulnerabilities':[{'cve':{'id':'CVE-2000-0001'}}]},'CVE-2024-3400')

    def test_empty_kev_is_valid_nonmatch(self):
        self.assertEqual(cve_facts('cisa-kev',{'vulnerabilities':[]},'CVE-2024-3400'),[])

    def test_indicator_match_preserves_provenance(self):
        body=b'2026-11-03 01:00:00,a,ip,192.0.2.1,#test,https://x.com/a/status/1\n'
        matches,count=indicator_matches({'format':'tweetfeed-csv'},body,'ip','192.0.2.1')
        self.assertEqual(matches[0]['value'],'192[.]0[.]2[.]1')
        self.assertEqual(matches[0]['reference'],'https://x.com/a/status/1')
        self.assertEqual(matches[0]['current_validity'],'unknown')

    def test_no_substring_domain_matching(self):
        body=b'2026-11-03 01:00:00,a,domain,sub.example.test,#test,https://x.com/a/status/1\n'
        self.assertEqual(indicator_matches({'format':'tweetfeed-csv'},body,'domain','example.test')[0],[])

    def test_only_catalog_endpoint_requested_never_ioc(self):
        visited=[]
        class Response:
            status=200
            url='https://feed.example.test/urls'
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self,*args):return b'https://indicator.example.test/a\n'
        class Opener:
            def open(self,req,**kwargs):visited.append(req.full_url);return Response()
        source=dict(id='feed',capabilities=['url'],url='https://feed.example.test',endpoint='https://feed.example.test/urls',format='url-list',query_mode='feed-exact',purpose='p',limits='l')
        result=collect([source],'url','https://indicator.example.test/a','research',Opener())
        self.assertEqual(visited,['https://feed.example.test/urls'])
        self.assertEqual(result[0]['outcome'],'matched')

    def test_network_failure_not_negative(self):
        class Opener:
            def open(self,*args,**kwargs):raise OSError('offline')
        source=dict(id='nvd',capabilities=['cve'],url='https://example.test',endpoint='https://example.test',query_mode='cve-json',purpose='p',limits='l')
        result=collect([source],'cve','CVE-2024-3400','research',Opener())
        self.assertEqual(result[0]['outcome'],'fetch-or-parse-failed')
        self.assertNotIn('matches',result[0])
