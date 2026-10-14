"""Build a small public release from an explicit allowlist, excluding private tests."""
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'dist/part5-release'


def md(text):
    return {'cell_type': 'markdown', 'metadata': {}, 'source': text.splitlines(True)}


def code(text):
    return {'cell_type': 'code', 'metadata': {}, 'execution_count': None,
            'outputs': [], 'source': text.splitlines(True)}


def notebook():
    cells = [md('''# MiniCPM-V 4.6 第五章公开复现

GPU 16x / 4x 各20图开发回归。三张图曾用于提示诊断，结构通过率不等于语义准确率。
默认 Python 3 内核即可：推理在本目录新建的虚拟环境中运行，继承魔搭基础镜像的 GPU PyTorch。
下载并解压复现包后打开本文件，从上到下执行。需要 NVIDIA GPU、可用的 CUDA PyTorch 和约4GB显存余量。
模型从官方固定版本下载（约2.5GiB），不会打包模型权重。现有缓存可通过 PART5_MODEL_DIR 指定并逐文件校验。
'''), code('''from pathlib import Path
import os, sys, json, subprocess, hashlib
ROOT=next(p for p in [Path.cwd(), *Path.cwd().parents] if (p/'release-manifest.json').is_file())
def run(args):
    subprocess.run([str(x) for x in args], cwd=ROOT, check=True)
run([sys.executable, ROOT/'examples/verify_part5_release.py'])
run([sys.executable, ROOT/'examples/bootstrap_part5.py', '--venv', ROOT/'.venv-part5',
     '--out', ROOT/'results/reproduction/environment.json'])
PY=ROOT/'.venv-part5/bin/python'
'''), md('## 固定模型文件与来源\n每次运行都重新核对官方文件清单与SHA256。'), code('''MODEL=Path(os.environ.get('PART5_MODEL_DIR',str(ROOT/'models/minicpm-v-4.6'))).resolve()
run([PY, ROOT/'examples/download_vision_model.py', '--revision',
     'fd02313ad21ac485c595cb01231a3bded449cff5', '--out', MODEL])
model_manifest=json.loads((MODEL/'download-manifest.json').read_text())
assert model_manifest['git_commit']=='fd02313ad21ac485c595cb01231a3bded449cff5'
for entry in model_manifest['files']:
    with (MODEL/entry['path']).open('rb') as f:
        assert hashlib.file_digest(f,'sha256').hexdigest()==entry['sha256']
print('Verified model files:',len(model_manifest['files']))
DATA=ROOT/'data/inspection-validation/public-cracks/manifest.json'
'''), md('## 单张图基线\n保存完整原始回答，并进行严格四字段解析。'), code('''sample=json.loads(DATA.read_text())['images'][0]
run([PY, ROOT/'examples/vision_baseline.py', '--model', MODEL,
     '--image', DATA.parent/sample['image'], '--out', ROOT/'results/reproduction/inspection-one.json'])
'''), md('## 20图两种模式\n每种模式单独加载一次模型。独立消息，无标签输入；失败原样保存。'), code('''for mode in ['16x','4x']:
    run([PY, ROOT/'examples/vision_batch.py', '--model', MODEL, '--manifest', DATA,
         '--downsample', mode, '--out', ROOT/f'results/reproduction/benchmark-gpu-v2-{mode}.json'])
'''), md('## 重新校验和统计\n统计脚本从原始JSON重新解析，不修补回答。原始发布测量保存在results/published。'), code('''run([PY, ROOT/'examples/analyze_gpu_v2.py', '--results', ROOT/'results/reproduction',
     '--manifest', DATA, '--out', ROOT/'results/reproduction'])
for mode in ['16x','4x']:
    r=json.loads((ROOT/f'results/reproduction/benchmark-gpu-v2-{mode}.json').read_text())
    print(mode, r['status'],sum(x['schema_valid'] for x in r['rows']),'/20')
print('需人工逐图核对，参阅 results/published/semantic-review.md')
''')]
    return {'cells': cells, 'metadata': {'kernelspec': {'display_name':'Python 3',
            'language':'python','name':'python3'}, 'language_info':{'name':'python'}},
            'nbformat':4, 'nbformat_minor':5}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    files = ['examples/inspection_contract.py', 'examples/task_contract.py',
             'examples/vision_baseline.py', 'examples/vision_batch.py',
             'examples/vision_prompt_diagnostic.py', 'examples/download_vision_model.py',
             'examples/bootstrap_part5.py', 'examples/verify_part5_release.py',
             'examples/analyze_gpu_v2.py', 'examples/integrate_inspection_android.py',
             'examples/ledger.py', 'examples/offline_queue.py',
             'data/inspection_confirmed_example.json']
    files += [str(p.relative_to(ROOT)) for p in (ROOT/'android').rglob('*') if p.is_file()]
    files += [str(p.relative_to(ROOT)) for p in (ROOT/'data/inspection-validation/public-cracks').rglob('*')
              if p.is_file() and p.suffix in ['.json','.md','.jpg']]
    for name in files:
        target=OUT/name; target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/name,target)
    published=OUT/'results/published';published.mkdir(parents=True,exist_ok=True)
    raw=ROOT/'results/part5-validation/notebook-public-batch-v2/results'
    for name in ['benchmark-gpu-v2-16x.json','benchmark-gpu-v2-4x.json',
                 'notebook-public-batch-v2-report.json','gpu-prompt-diagnostic.json']:
        shutil.copyfile(raw/name,published/name)
    for name in ['summary.json','comparison-40.csv','semantic-review.md']:
        shutil.copyfile(ROOT/'results/part5-validation/gpu-v2-summary'/name,published/name)
    legacy=published/'legacy-v1';legacy.mkdir(exist_ok=True)
    old=ROOT/'results/part5-validation/notebook-public-batch/results'
    for name in ['benchmark-gpu-16x.json','benchmark-gpu-4x.json']:
        shutil.copyfile(old/name,legacy/name)
    shutil.copyfile(ROOT/'results/part5-validation/benchmark-gpu-summary.json',legacy/'summary.json')
    for name in ['README.md','LICENSE-CODE-MIT','LICENSE-DATA-CC-BY-4.0.md','THIRD_PARTY_NOTICES.md','ANDROID.md']:
        shutil.copyfile(ROOT/'release-assets'/name,OUT/name)
    nb=OUT/'notebooks';nb.mkdir(exist_ok=True)
    document=notebook()
    for i,cell in enumerate(document['cells']):cell['id']=f'part5-cell-{i:02d}'
    (nb/'part5_reproduce.ipynb').write_text(json.dumps(document,ensure_ascii=False,indent=2)+'\n')
    # Derived reports and documentation contain no private phone records or images.
    manifest={'release':'2026-10-15-v2','model_revision':'fd02313ad21ac485c595cb01231a3bded449cff5',
              'code_license':'MIT','data_license':'CC-BY-4.0','files':[]}
    for path in sorted(OUT.rglob('*')):
        if path.is_file() and path.name!='release-manifest.json':
            manifest['files'].append({'path':str(path.relative_to(OUT)),'bytes':path.stat().st_size,
                                      'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    (OUT/'release-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    bundle=ROOT/'dist/part5-reproduction-v2.zip'
    with zipfile.ZipFile(bundle,'w',zipfile.ZIP_DEFLATED) as z:
        for path in sorted(OUT.rglob('*')):
            if path.is_file():z.write(path,Path('part5-release')/path.relative_to(OUT))
    print(bundle, bundle.stat().st_size, hashlib.sha256(bundle.read_bytes()).hexdigest())


if __name__=='__main__':main()
