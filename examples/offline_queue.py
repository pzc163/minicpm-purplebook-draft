"""Durable outbox simulator. Payloads freeze after confirmation; retry keeps ID."""
import argparse
import json
import os
import sqlite3
import urllib.error
import urllib.request
from pathlib import Path
from inspection_contract import digest, validate_record

class Outbox:
    def __init__(self,path):
        self.path=str(path)
        with sqlite3.connect(self.path) as c:
            c.execute('CREATE TABLE IF NOT EXISTS outbox(record_id TEXT PRIMARY KEY, payload TEXT NOT NULL, digest TEXT NOT NULL, synced INTEGER NOT NULL DEFAULT 0)')
    def add(self,record):
        validate_record(record)
        with sqlite3.connect(self.path) as c:
            row=c.execute('SELECT digest FROM outbox WHERE record_id=?',(record['record_id'],)).fetchone()
            if row and row[0]!=digest(record):
                raise ValueError('confirmed record is immutable; create a correction record')
            c.execute('INSERT OR IGNORE INTO outbox(record_id,payload,digest) VALUES(?,?,?)',
                      (record['record_id'],json.dumps(record,ensure_ascii=False),digest(record)))
    def pending(self):
        with sqlite3.connect(self.path) as c:
            return [json.loads(x[0]) for x in c.execute('SELECT payload FROM outbox WHERE synced=0 ORDER BY record_id')]
    def ack(self,rid):
        with sqlite3.connect(self.path) as c:
            c.execute('UPDATE outbox SET synced=1 WHERE record_id=?',(rid,))
    def sync(self,url):
        results=[]
        for record in self.pending():
            headers={'Content-Type':'application/json'}
            if os.environ.get('DEMO_LEDGER_TOKEN'):
                headers['Authorization']='Bearer '+os.environ['DEMO_LEDGER_TOKEN']
            req=urllib.request.Request(url.rstrip('/')+'/records', data=json.dumps(record).encode(),headers=headers)
            try:
                with urllib.request.urlopen(req,timeout=10) as response:
                    ack=json.load(response)
                    if response.status not in (200,201) or ack.get('record')!=record:
                        raise ValueError('acknowledged payload differs')
                self.ack(record['record_id'])
                results.append({'id':record['record_id'],'synced':True})
            except Exception as exc:
                results.append({'id':record['record_id'],'synced':False,'error':type(exc).__name__})
        return results

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--db',default='phone-outbox.sqlite3')
    sub=p.add_subparsers(dest='command',required=True)
    add=sub.add_parser('add'); add.add_argument('record')
    sub.add_parser('pending')
    sync=sub.add_parser('sync'); sync.add_argument('--url',default='http://127.0.0.1:8787')
    a=p.parse_args(); box=Outbox(a.db)
    if a.command=='add':
        box.add(json.loads(Path(a.record).read_text(encoding='utf-8'))); print('Saved locally')
    elif a.command=='pending': print(json.dumps(box.pending(),ensure_ascii=False,indent=2))
    else: print(json.dumps(box.sync(a.url),ensure_ascii=False,indent=2))
