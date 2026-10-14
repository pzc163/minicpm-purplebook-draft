"""Single-photo Notebook baseline using native Transformers MiniCPM-V 4.6 API."""
import argparse
import json
from pathlib import Path
from inspection_contract import VISION_PROMPT, VISION_PROMPT_VERSION, parse_draft

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--model',required=True)
    p.add_argument('--image',required=True)
    p.add_argument('--out',required=True)
    p.add_argument('--downsample',choices=['4x','16x'],default='16x')
    a=p.parse_args()
    import torch
    from transformers import AutoProcessor, AutoModelForImageTextToText
    model=AutoModelForImageTextToText.from_pretrained(a.model,torch_dtype='auto',device_map='auto',local_files_only=True).eval()
    processor=AutoProcessor.from_pretrained(a.model,local_files_only=True)
    messages=[{'role':'system','content':VISION_PROMPT},{'role':'user','content':[
        {'type':'image','url':str(Path(a.image).resolve())},
        {'type':'text','text':VISION_PROMPT}]}]
    inputs=processor.apply_chat_template(messages,tokenize=True,add_generation_prompt=True,
           enable_thinking=False,return_dict=True,return_tensors='pt',
           downsample_mode=a.downsample,max_slice_nums=1).to(model.device)
    with torch.inference_mode():
        ids=model.generate(**inputs,downsample_mode=a.downsample,do_sample=False,max_new_tokens=384)
    raw=processor.batch_decode([ids[0][len(inputs.input_ids[0]):]],skip_special_tokens=True,clean_up_tokenization_spaces=False)[0]
    try:
        draft=parse_draft(raw); result={'raw':raw,'schema_valid':True,'draft':draft}
    except (ValueError,TypeError):
        result={'raw':raw,'schema_valid':False,'draft':None}
    import hashlib
    result['prompt']={'version':VISION_PROMPT_VERSION,'text':VISION_PROMPT,'sha256':hashlib.sha256(VISION_PROMPT.encode()).hexdigest()}
    out=Path(a.out); out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__': main()
