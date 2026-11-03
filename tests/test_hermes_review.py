import sys
import json
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'optional/hermes'))
from review_with_hermes import validate_review, audit_web_events


class ReviewContractTests(unittest.TestCase):
    def setUp(self):
        self.review = dict(scope='frozen-public-source-review',summary='summary',next_actions=[],limitations=[],
                           findings=[dict(source_id='feodo',kind='freshness',observation='old records',
                                          evidence=['data/status.json:feodo.latest_item_at'],impact='historical only',
                                          recommendation='review',uncertainty='current activity unknown',requires_approval=True)])

    def test_valid_proposal(self):
        validate_review(self.review, {'feodo'})

    def test_invented_source_rejected(self):
        with self.assertRaises(ValueError): validate_review(self.review, {'another'})

    def test_no_evidence_rejected(self):
        self.review['findings'][0]['evidence']=[]
        with self.assertRaises(ValueError): validate_review(self.review, {'feodo'})

    def test_changes_cannot_auto_apply(self):
        self.review['findings'][0]['requires_approval']=False
        with self.assertRaises(ValueError): validate_review(self.review, {'feodo'})

    def live_review(self):
        self.review.update(scope='source-investigation',verification=[dict(url='https://example.test',outcome='retrieved',observation='data')],
                           data_comparison=dict(record_count=1,last_online_dates=['2026-03-12'],status_counts={'online':1,'offline':0},transport_http_status=None))
        return self.review

    def test_live_comparison_consistent(self):
        validate_review(self.live_review(), {'feodo'}, 'source-investigation')

    def test_extra_date_rejected(self):
        review = self.live_review()
        review['data_comparison']['last_online_dates'].append('2026-02-23')
        with self.assertRaises(ValueError): validate_review(review, {'feodo'}, 'source-investigation')

    def test_invented_http_status_rejected(self):
        review = self.live_review()
        review['data_comparison']['transport_http_status']=200
        with self.assertRaises(ValueError): validate_review(review, {'feodo'}, 'source-investigation')

    def test_out_of_scope_tool_rejected(self):
        with self.assertRaises(ValueError): audit_web_events([dict(type='tool_use',name='terminal')], [])

    def test_truncated_evidence_not_claimed_complete(self):
        events=[dict(type='tool_use',name='web_extract',tool_call_id='x',input={'urls':['https://example.test']}),
                dict(type='tool_result',name='web_extract',tool_call_id='x',output='{"results":[')]
        audit=audit_web_events(events, ['https://example.test'])
        self.assertFalse(audit['evidence_complete'])
        self.assertEqual(audit['extracted_urls'], [])

    def test_actual_extraction_evidence(self):
        events=[dict(type='tool_use',name='web_extract',tool_call_id='x',input={'urls':['https://example.test']}),
                dict(type='tool_result',name='web_extract',tool_call_id='x',output=json.dumps({'results':[{'url':'https://example.test','content':'body'}]}))]
        self.assertTrue(audit_web_events(events,['https://example.test'])['evidence_complete'])

    def test_unapproved_url_rejected(self):
        events=[dict(type='tool_use',name='web_extract',tool_call_id='x',input={'urls':['https://another.test']})]
        with self.assertRaises(ValueError):audit_web_events(events,['https://example.test'])
