"""Create the public 20-image experiment notebook; validate with nbformat on GPU."""
import json
from create_notebooks import ROOT, LOCATE, code, md, write


def main():
    write('02_minicpmv_public_batch.ipynb', [
        md('# 公开混凝土图片的20图对照验证\n\n'
           '第五章GPU提示v2开发回归：20张227×227裁剪图，来源正/负类各10张，不能代表20个独立现场。三张用于提示诊断，本组不作为独立盲测。'
           '手机和GPU使用相同图像哈希，解码与视觉预处理配置不同，时间不作直接等效比较。'
           '来源、许可及边界歧义见数据子集README。'),
        md('## 1 固定环境和数据\n使用此前已准备的Part5内核，不重新升级PyTorch。'),
        code(LOCATE + '''
import hashlib, torch, transformers
assert transformers.__version__ == "5.7.0"
assert torch.cuda.is_available()
MODEL=ROOT/"models/minicpm-v-4.6"
manifest=json.loads((MODEL/"download-manifest.json").read_text())
for item in manifest["files"]:
    path=MODEL/item["path"]
    with path.open("rb") as f: actual=hashlib.file_digest(f,"sha256").hexdigest()
    assert actual==item["sha256"], item["path"]
print("Model files verified:",len(manifest["files"]))
DATA=ROOT/"data/inspection-validation/public-cracks/manifest.json"
assert len(json.loads(DATA.read_text())["images"])==20
'''),
        md('## 2 16x 连续运行\n单次模型加载，保存原始输出、结构校验、逐图时间与PyTorch显存峰值。'),
        code('''run([sys.executable,ROOT/"examples/vision_batch.py","--model",MODEL,"--manifest",DATA,
     "--downsample","16x","--out",ROOT/"results/benchmark-gpu-v2-16x.json"])
'''),
        md('## 3 同图4x对照\n预处理和生成两处参数一致；每种模式单独加载一次模型。'),
        code('''run([sys.executable,ROOT/"examples/vision_batch.py","--model",MODEL,"--manifest",DATA,
     "--downsample","4x","--out",ROOT/"results/benchmark-gpu-v2-4x.json"])
'''),
        md('## 4 检查结果\n结构合格率单独统计。对象、裂纹描述和无依据断言需按保存的标注逐图复核。'),
        code('''for mode in ["16x","4x"]:
    report=json.loads((ROOT/f"results/benchmark-gpu-v2-{mode}.json").read_text())
    assert report["status"]=="completed" and len(report["rows"])==20
    print(mode,"schema",sum(r["schema_valid"] for r in report["rows"]),"/20",
          "allocated MiB",report["cuda_peak_allocated_bytes"]/1024**2)
'''),
    ])
    path = ROOT / 'notebooks/02_minicpmv_public_batch.ipynb'
    notebook = json.loads(path.read_text())
    notebook['metadata']['kernelspec'] = {
        'display_name': 'Python (Part5 fixed)', 'language': 'python', 'name': 'minicpm-part5'}
    path.write_text(json.dumps(notebook, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
