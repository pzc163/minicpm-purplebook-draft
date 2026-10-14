"""Small prompt diagnostic; does not repair or score edited model outputs."""
import json
from pathlib import Path
import sys
import time
import hashlib

from inspection_contract import LEGACY_VISION_PROMPT, parse_draft

PROMPTS = {
    "legacy": LEGACY_VISION_PROMPT,
    "concise": "观察这张照片，用中文描述主要可见对象或表面以及可见状态。只输出一个JSON对象，恰好包含object、visible_issue、needs_retake、missing_fields。object填写对象或表面名称，不要求画面中有独立物体；visible_issue填写可见现象，正常时也描述可见状态。不猜测原因、意图或维修方案。看不清的字段才填null；needs_retake为布尔值；missing_fields为值为null的字段名称数组，没有缺失则为[]。不要Markdown或解释。",
    "positive_template": "请观察照片，只输出一个JSON对象，按下面的四字段格式填写真实观察，不照抄占位文字：{\"object\":\"主要对象或表面名称\",\"visible_issue\":\"照片支持的状态描述\",\"needs_retake\":false,\"missing_fields\":[]}。用中文。特写中的墙面、地面或其他表面也是对象，不要求出现独立物体。正常照片也填写可见状态。不能从照片确认原因、动作意图或维修方法。只有确实看不清的观察字段才填null，并在missing_fields数组列出对应字段名；此时needs_retake为true。不要输出代码围栏、数组或额外字段。",
}

def main():
    import torch
    from transformers import AutoProcessor, AutoModelForImageTextToText
    root = Path(sys.argv[1]).resolve()
    model_dir = root / "models/minicpm-v-4.6"
    data = root / "data/inspection-validation/public-cracks"
    manifest = json.loads((data / "manifest.json").read_text())
    model = AutoModelForImageTextToText.from_pretrained(model_dir, torch_dtype="auto", device_map="auto", local_files_only=True).eval()
    processor = AutoProcessor.from_pretrained(model_dir, local_files_only=True)
    rows = []
    for name, prompt in PROMPTS.items():
        for index in [0, 1, 10]:
            item = manifest["images"][index]
            image = data / item["image"]
            assert hashlib.sha256(image.read_bytes()).hexdigest() == item["sha256"]
            messages = [{"role": "system", "content": prompt}, {"role": "user", "content": [
                {"type": "image", "url": str(image)}, {"type": "text", "text": prompt}]}]
            began = time.perf_counter()
            inputs = processor.apply_chat_template(messages, tokenize=True, add_generation_prompt=True,
                enable_thinking=False, return_dict=True, return_tensors="pt", downsample_mode="16x", max_slice_nums=1).to(model.device)
            with torch.inference_mode():
                ids = model.generate(**inputs, downsample_mode="16x", do_sample=False, max_new_tokens=384)
            raw = processor.batch_decode([ids[0][inputs.input_ids.shape[1]:]], skip_special_tokens=True, clean_up_tokenization_spaces=False)[0]
            row = {"prompt_name": name, "image_id": item["id"], "raw": raw, "elapsed_ms": (time.perf_counter()-began)*1000}
            try:
                row["draft"] = parse_draft(raw)
                row["schema_valid"] = True
            except (ValueError, TypeError) as error:
                row.update(schema_valid=False, error=str(error))
            rows.append(row)
            output = root / "results/gpu-prompt-diagnostic.json"
            output.write_text(json.dumps({"scope": "three development images; not held-out evaluation", "prompts": PROMPTS, "rows": rows}, ensure_ascii=False, indent=2))
            print(json.dumps(row, ensure_ascii=False), flush=True)
    print("DIAGNOSTIC_COMPLETE", flush=True)

if __name__ == "__main__":
    main()
