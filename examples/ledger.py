"""Local teaching ledger: idempotent create + optimistic status update. Standard library only."""
import argparse
import json
import os
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit
from inspection_contract import digest, validate_record

class Ledger:
    def __init__(self, path):
        self.path = str(path)
        with self.connect() as c:
            c.execute('CREATE TABLE IF NOT EXISTS records (record_id TEXT PRIMARY KEY, payload TEXT NOT NULL, digest TEXT NOT NULL, status TEXT NOT NULL, version INTEGER NOT NULL)')

    def connect(self):
        c = sqlite3.connect(self.path, timeout=10)
        c.row_factory = sqlite3.Row
        return c

    @staticmethod
    def shape(row):
        return {'record':json.loads(row['payload']), 'status':row['status'], 'version':row['version']}

    def create(self, payload):
        validate_record(payload)
        checksum = digest(payload)
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            row = c.execute('SELECT * FROM records WHERE record_id=?',(payload['record_id'],)).fetchone()
            if row:
                if row['digest'] != checksum:
                    return 409, {'error':'same record_id with different content'}
                return 200, self.shape(row)
            c.execute('INSERT INTO records VALUES(?,?,?,?,?)',(payload['record_id'],json.dumps(payload,ensure_ascii=False),checksum,'pending',1))
            return 201, self.shape(c.execute('SELECT * FROM records WHERE record_id=?',(payload['record_id'],)).fetchone())

    def list(self):
        with self.connect() as c:
            return [self.shape(x) for x in c.execute('SELECT * FROM records ORDER BY record_id')]

    def get(self, rid):
        with self.connect() as c:
            row=c.execute('SELECT * FROM records WHERE record_id=?',(rid,)).fetchone()
            return (200,self.shape(row)) if row else (404,{'error':'not found'})

    def update(self, rid, status, version):
        if status not in {'pending','in_progress','closed'} or type(version) is not int:
            return 400, {'error':'invalid status or version'}
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            row=c.execute('SELECT * FROM records WHERE record_id=?',(rid,)).fetchone()
            if not row:
                return 404, {'error':'not found'}
            if row['version'] != version:
                return 409, {'error':'version conflict','version':row['version']}
            c.execute('UPDATE records SET status=?, version=version+1 WHERE record_id=?',(status,rid))
            return 200,self.shape(c.execute('SELECT * FROM records WHERE record_id=?',(rid,)).fetchone())

def make_server(bind, port, path):
    ledger=Ledger(path)
    token=os.environ.get('DEMO_LEDGER_TOKEN')
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass
        def reply(self, status, value):
            body=json.dumps(value,ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header('Content-Type','application/json; charset=utf-8')
            self.send_header('Content-Length',str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        def handle_method(self, method):
            if token and self.headers.get('Authorization')!='Bearer '+token:
                return self.reply(401,{'error':'unauthorized'})
            parts=urlsplit(self.path).path.strip('/').split('/')
            try:
                if method=='GET' and parts==['records']:
                    return self.reply(200,{'items':ledger.list()})
                if method=='GET' and len(parts)==2 and parts[0]=='records':
                    return self.reply(*ledger.get(parts[1]))
                if method in {'POST','PATCH'}:
                    size=int(self.headers.get('Content-Length','0'))
                    if not 0<size<=65536:
                        return self.reply(400,{'error':'invalid body length'})
                    body=json.loads(self.rfile.read(size))
                    if method=='POST' and parts==['records']:
                        return self.reply(*ledger.create(body))
                    if method=='PATCH' and len(parts)==3 and parts[0]=='records' and parts[2]=='status':
                        if not isinstance(body,dict) or set(body)!={'status','expected_version'}:
                            raise ValueError('invalid status body')
                        return self.reply(*ledger.update(parts[1],body['status'],body['expected_version']))
                return self.reply(404,{'error':'not found'})
            except (ValueError,TypeError,KeyError,AttributeError):
                return self.reply(400,{'error':'invalid request'})
        def do_GET(self): self.handle_method('GET')
        def do_POST(self): self.handle_method('POST')
        def do_PATCH(self): self.handle_method('PATCH')
    return ThreadingHTTPServer((bind,port),Handler)

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--bind',default='127.0.0.1')
    p.add_argument('--port',type=int,default=8787)
    p.add_argument('--db',default='ledger.sqlite3')
    a=p.parse_args()
    server=make_server(a.bind,a.port,a.db)
    print(f'Teaching ledger: http://{a.bind}:{server.server_port}/records',flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()
