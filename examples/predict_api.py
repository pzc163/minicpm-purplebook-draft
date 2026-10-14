"""Evaluate a local OpenAI-compatible GGUF server with the SAME test prompts."""
import argparse
import json
import os
import urllib.request
from pathlib import Path
from task_contract import PROMPT, read_jsonl

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--url', default='http://127.0.0.1:8080/v1/chat/completions')
    p.add_argument('--model', default='todo')
    p.add_argument('--gold', default='data/test_gold.jsonl')
    p.add_argument('--out', required=True)
    a = p.parse_args()
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    with open(a.out, 'w', encoding='utf-8') as f:
        for row in read_jsonl(a.gold):
            payload = {'model': a.model, 'messages':[{'role':'system','content':PROMPT},
                       {'role':'user','content':row['text']}], 'temperature':0, 'max_tokens':512,
                       'chat_template_kwargs':{'enable_thinking':False}}
            headers = {'Content-Type':'application/json'}
            if os.environ.get('MODEL_API_KEY'):
                headers['Authorization'] = 'Bearer ' + os.environ['MODEL_API_KEY']
            request = urllib.request.Request(a.url, data=json.dumps(payload).encode(), headers=headers)
            try:
                with urllib.request.urlopen(request, timeout=180) as response:
                    answer = json.load(response)['choices'][0]['message']['content'] or ''
                prediction = {'id':row['id'], 'output':answer}
            except Exception as exc:
                prediction = {'id':row['id'], 'output':'', 'error':type(exc).__name__}
            f.write(json.dumps(prediction, ensure_ascii=False) + '\n')
            f.flush()

if __name__ == '__main__':
    main()
