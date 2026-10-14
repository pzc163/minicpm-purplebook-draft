"""Transformers baseline / merged-checkpoint inference; never writes fabricated model results."""
import argparse
import json
from pathlib import Path
from task_contract import PROMPT, read_jsonl

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', required=True)
    parser.add_argument('--gold', default='data/test_gold.jsonl')
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(args.model, local_files_only=True)
    model = AutoModelForCausalLM.from_pretrained(args.model, torch_dtype='auto', device_map='auto', local_files_only=True).eval()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open('w', encoding='utf-8') as f:
        for row in read_jsonl(args.gold):
            messages = [{'role':'system', 'content':PROMPT}, {'role':'user', 'content':row['text']}]
            inputs = tok.apply_chat_template(messages, tokenize=True, add_generation_prompt=True,
                       enable_thinking=False, return_tensors='pt', return_dict=True).to(model.device)
            with torch.inference_mode():
                output = model.generate(**inputs, do_sample=False, max_new_tokens=512)
            text = tok.decode(output[0][inputs['input_ids'].shape[-1]:], skip_special_tokens=True)
            f.write(json.dumps({'id':row['id'], 'output':text}, ensure_ascii=False) + '\n')
            f.flush()

if __name__ == '__main__':
    main()
