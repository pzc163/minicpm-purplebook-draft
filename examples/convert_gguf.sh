#!/usr/bin/env bash
set -euo pipefail
if [[ $# -ne 3 ]]; then
  echo 'Usage: bash examples/convert_gguf.sh MERGED_HF_DIR OUTPUT_DIR LLAMA_CPP_DIR' >&2
  exit 2
fi
checkpoint_dir=$(realpath "$1")
output_dir=$(realpath -m "$2")
llama_source_dir=$(realpath "$3")
mkdir -p "$output_dir"
python "$llama_source_dir/convert_hf_to_gguf.py" "$checkpoint_dir" --outfile "$output_dir/todo-F16.gguf" --outtype f16
"$llama_source_dir/build/bin/llama-quantize" "$output_dir/todo-F16.gguf" "$output_dir/todo-Q4_K_M.gguf" Q4_K_M
"$llama_source_dir/build/bin/llama-quantize" "$output_dir/todo-F16.gguf" "$output_dir/todo-Q8_0.gguf" Q8_0
python - "$output_dir" <<'PY'
import hashlib, json, sys
from pathlib import Path
root=Path(sys.argv[1]); rows=[]
for path in sorted(root.glob('*.gguf')):
    with path.open('rb') as f:
        checksum=hashlib.file_digest(f,'sha256').hexdigest()
    rows.append({'file':path.name,'bytes':path.stat().st_size,'sha256':checksum})
(root/'checksums.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
print(json.dumps(rows,indent=2))
PY
