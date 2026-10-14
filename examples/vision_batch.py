"""Run an authorized image manifest with one native Transformers model load."""
import argparse
import hashlib
import json
import platform
import time
from datetime import datetime, timezone
from pathlib import Path

from inspection_contract import VISION_PROMPT, VISION_PROMPT_VERSION, parse_draft


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--downsample', choices=['16x', '4x'], default='16x')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    import torch
    import transformers
    from transformers import AutoProcessor, AutoModelForImageTextToText

    manifest = json.loads(args.manifest.read_text())
    samples = manifest['images']
    if len(samples) != 20 or len({item['sha256'] for item in samples}) != 20:
        raise ValueError('This benchmark requires 20 distinct image hashes')
    images = []
    for item in samples:
        image = (args.manifest.parent / item['image']).resolve()
        if not image.is_relative_to(args.manifest.parent.resolve()):
            raise ValueError('Image path must stay inside the manifest directory')
        if hashlib.file_digest(image.open('rb'), 'sha256').hexdigest() != item['sha256']:
            raise ValueError(f'Image hash mismatch: {item["id"]}')
        images.append(image)
    model_manifest = json.loads((args.model / 'download-manifest.json').read_text())
    if model_manifest['git_commit'] != 'fd02313ad21ac485c595cb01231a3bded449cff5':
        raise ValueError('Unexpected model revision')
    args.out.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    report = {'status': 'running', 'started_at': datetime.now(timezone.utc).isoformat(),
              'source': manifest['source_url'], 'license': manifest['license'],
              'manifest_sha256': hashlib.file_digest(args.manifest.open('rb'), 'sha256').hexdigest(),
              'model_revision': model_manifest['git_commit'], 'rows': rows,
              'prompt': {'version': VISION_PROMPT_VERSION, 'text': VISION_PROMPT,
                         'sha256': hashlib.sha256(VISION_PROMPT.encode()).hexdigest()},
              'evaluation_scope': 'development regression; three of these images were used in prompt diagnostics, not a held-out accuracy benchmark',
              'environment': {'python': platform.python_version(), 'torch': torch.__version__,
                              'transformers': transformers.__version__,
                              'gpu': torch.cuda.get_device_name(0)},
              'config': {'downsample': args.downsample, 'max_slice_nums': 1,
                         'thinking': False, 'do_sample': False, 'max_new_tokens': 384},
              'timing_scope': 'processor image loading/template + image encoding + generation + output decoding; first_generated_token_ms is token ID arrival, not first displayed text',
              'memory_scope': 'PyTorch allocator peak on CUDA device 0; not whole-device driver memory'}

    def persist():
        temporary = args.out.with_suffix('.json.tmp')
        temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2))
        temporary.replace(args.out)

    class FirstTokenClock:
        def __init__(self, begin):
            self.begin = begin
            self.first_ms = None
            self.prompt = True

        def put(self, value):
            if self.prompt:
                self.prompt = False
            elif self.first_ms is None:
                self.first_ms = (time.perf_counter() - self.begin) * 1000

        def end(self):
            pass

    torch.cuda.reset_peak_memory_stats(0)
    began = time.perf_counter()
    model = AutoModelForImageTextToText.from_pretrained(
        args.model, torch_dtype='auto', device_map='auto', local_files_only=True).eval()
    processor = AutoProcessor.from_pretrained(args.model, local_files_only=True)
    torch.cuda.synchronize()
    report['load_ms'] = (time.perf_counter() - began) * 1000
    persist()
    for index, (item, image) in enumerate(zip(samples, images), 1):
        # Each input creates an independent message list; no chat history is carried.
        messages = [{'role': 'system', 'content': VISION_PROMPT}, {'role': 'user', 'content': [
            {'type': 'image', 'url': str(image)}, {'type': 'text', 'text': VISION_PROMPT}]}]
        report['active_image'] = item['id']
        persist()
        torch.cuda.synchronize()
        begin = time.perf_counter()
        clock = FirstTokenClock(begin)
        row = {'index': index, 'id': item['id'], 'sha256': item['sha256']}
        try:
            inputs = processor.apply_chat_template(
                messages, tokenize=True, add_generation_prompt=True, enable_thinking=False,
                return_dict=True, return_tensors='pt', downsample_mode=args.downsample,
                max_slice_nums=1).to(model.device)
            with torch.inference_mode():
                ids = model.generate(**inputs, downsample_mode=args.downsample, do_sample=False,
                                     max_new_tokens=384, streamer=clock)
            token_ids = ids[0][len(inputs.input_ids[0]):]
            raw = processor.batch_decode([token_ids], skip_special_tokens=True,
                                         clean_up_tokenization_spaces=False)[0]
            row['raw'] = raw
            row['generated_tokens'] = len(token_ids)
            row['reached_token_limit'] = len(token_ids) == 384
            try:
                row['draft'] = parse_draft(raw)
                row['schema_valid'] = True
            except (ValueError, TypeError) as error:
                row.update(schema_valid=False, draft=None, error=str(error))
            del inputs, ids, token_ids
        except Exception as error:
            row.update(schema_valid=False, error=f'{type(error).__name__}: {error}')
        torch.cuda.synchronize()
        row['elapsed_ms'] = (time.perf_counter() - begin) * 1000
        row['first_generated_token_ms'] = clock.first_ms
        row['cuda_peak_allocated_bytes'] = torch.cuda.max_memory_allocated(0)
        row['cuda_peak_reserved_bytes'] = torch.cuda.max_memory_reserved(0)
        rows.append(row)
        persist()
        print(f'{index:02d}/20 {item["id"]} schema={row["schema_valid"]} {row["elapsed_ms"]:.0f} ms', flush=True)
    report.pop('active_image', None)
    report['status'] = 'completed'
    report['finished_at'] = datetime.now(timezone.utc).isoformat()
    report['cuda_peak_allocated_bytes'] = torch.cuda.max_memory_allocated(0)
    report['cuda_peak_reserved_bytes'] = torch.cuda.max_memory_reserved(0)
    persist()


if __name__ == '__main__':
    main()
