"""Checks contracts and real localhost sync; performs no model inference."""
import json
import tempfile
import threading
import unittest
from pathlib import Path
from task_contract import read_jsonl, loads_strict
from evaluate_todo import score
from inspection_contract import parse_draft
from ledger import Ledger, make_server
from offline_queue import Outbox

ROOT=Path(__file__).resolve().parents[1]

class ContractTests(unittest.TestCase):
    def test_splits_and_null_evidence(self):
        seen=set()
        for split,count in [('train',320),('dev',64),('test',96)]:
            rows=read_jsonl(ROOT/'data'/f'{split}_gold.jsonl')
            self.assertEqual(len(rows),count)
            for row in rows:
                self.assertNotIn(row['text'],seen); seen.add(row['text'])
                for item in row['expected']['tasks']:
                    self.assertIn(item['task'],row['text'])
                    if item['due_text']: self.assertIn(item['due_text'],row['text'])
                    if item['category']: self.assertIn(item['category'],row['text'])
    def test_scoring_invalid_missing_extra(self):
        gold=[{'id':'a','text':'需要取快递','expected':{'tasks':[{'task':'取快递','due_text':None,'category':None}]}},
              {'id':'b','text':'没有待办','expected':{'tasks':[]}}]
        good={'id':'a','output':json.dumps(gold[0]['expected'],ensure_ascii=False)}
        report=score(gold,[good,{'id':'b','output':'```json\n{"tasks":[]}\n```'}])
        self.assertEqual(report['schema_valid_rate'],0.5)
        self.assertEqual(report['exact_record_rate'],0.5)
        self.assertEqual(score(gold,[])['field_accuracy'],0)
        extra={'tasks':[{'task':'取快递','due_text':None,'category':None},{'task':'买纸','due_text':None,'category':None}]}
        self.assertLess(score([gold[0]],[{'id':'a','output':json.dumps(extra)}])['field_accuracy'],1)
        with self.assertRaises(ValueError): score(gold,[good,good])
    def test_json_and_draft_contract(self):
        with self.assertRaises(ValueError): loads_strict('{"tasks":[],"tasks":[]}')
        with self.assertRaises(ValueError): loads_strict('{"x":NaN}')
        good={'object':None,'visible_issue':None,'needs_retake':True,'missing_fields':['object','visible_issue']}
        self.assertEqual(parse_draft(json.dumps(good)),good)
        good['needs_retake']='false'
        with self.assertRaises(ValueError): parse_draft(json.dumps(good))

class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.record=json.loads((ROOT/'data/inspection_confirmed_example.json').read_text(encoding='utf-8'))
    def tearDown(self): self.tmp.cleanup()
    def test_lost_ack_replay_and_conflict(self):
        ledger=Ledger(Path(self.tmp.name)/'ledger.db')
        self.assertEqual(ledger.create(self.record)[0],201)
        # Server committed but the phone never received ACK; retry same frozen payload.
        self.assertEqual(ledger.create(self.record)[0],200)
        self.assertEqual(len(ledger.list()),1)
        changed=dict(self.record,location='三层')
        self.assertEqual(ledger.create(changed)[0],409)
        self.assertEqual(ledger.update(self.record['record_id'],'closed',1)[0],200)
        self.assertEqual(ledger.update(self.record['record_id'],'pending',1)[0],409)
        self.assertEqual(ledger.get(self.record['record_id'])[1]['status'],'closed')
    def test_confirmation_gate(self):
        ledger=Ledger(Path(self.tmp.name)/'ledger.db')
        with self.assertRaises(ValueError): ledger.create(dict(self.record,human_confirmed=False))
        with self.assertRaises(ValueError): ledger.create(dict(self.record,location=''))
        self.assertEqual(ledger.list(),[])
    def test_offline_restart_and_http_sync(self):
        path=Path(self.tmp.name)/'outbox.db'
        box=Outbox(path); box.add(self.record)
        self.assertEqual(len(Outbox(path).pending()),1)
        # Network unavailable: item stays pending.
        self.assertFalse(box.sync('http://127.0.0.1:1')[0]['synced'])
        self.assertEqual(len(box.pending()),1)
        server=make_server('127.0.0.1',0,Path(self.tmp.name)/'ledger.db')
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            base=f'http://127.0.0.1:{server.server_port}'
            self.assertTrue(box.sync(base)[0]['synced'])
            self.assertEqual(Outbox(path).pending(),[])
            self.assertEqual(box.sync(base),[])
        finally:
            server.shutdown();server.server_close();thread.join()
        with self.assertRaises(ValueError): box.add(dict(self.record,location='四层'))

if __name__=='__main__': unittest.main(verbosity=2)
