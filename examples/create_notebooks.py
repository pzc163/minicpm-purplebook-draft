"""Create clean, unexecuted notebooks; run from any directory."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def md(text): return {'cell_type':'markdown','metadata':{},'source':text.splitlines(keepends=True)}
def code(text): return {'cell_type':'code','metadata':{},'execution_count':None,'outputs':[],'source':text.splitlines(keepends=True)}
def write(name,cells):
    nb={'cells':cells,'metadata':{'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'},
        'language_info':{'name':'python','version':'3.11'}},'nbformat':4,'nbformat_minor':5}
    # Stable cell identifiers, supported by nbformat 4.5.
    for i,c in enumerate(nb['cells']): c['id']=f'cell-{i:03d}'
    (ROOT/'notebooks'/name).write_text(json.dumps(nb,ensure_ascii=False,indent=2),encoding='utf-8')

LOCATE='''from pathlib import Path
import sys, subprocess, json
candidates=[Path.cwd(), Path.cwd().parent, Path.cwd()/"minicpm-purplebook-draft"]
ROOT=next((p.resolve() for p in candidates if (p/"examples/task_contract.py").is_file()), None)
if ROOT is None:
    raise RuntimeError("请先上传并解压完整实践包，再在项目目录打开Notebook")
sys.path.insert(0,str(ROOT/"examples"))
def run(args):
    subprocess.run([str(x) for x in args],cwd=ROOT,check=True)
print("Project:",ROOT)
'''

def main():
    write('01_minicpm5_todo_lora.ipynb',[
md('''# 微调 MiniCPM5-2B 待办助手

此 Notebook 是 GPU 复现实验初稿，尚未在本次环境执行训练。请先阅读 Part 3 章节，使用支持 BF16 的 GPU 与 Python 3.11，上传完整项目。基座、模板、提示与测试集应固定。不会自动发布任何模型。'''),
code(LOCATE),
md('## 1 安装官方指定模板版本\n保留镜像的 CUDA / PyTorch 组合。安装后重启内核，并重新执行路径定位单元格。'),
code('''run([sys.executable,"-m","pip","install",
     "git+https://github.com/modelscope/ms-swift.git@654e24f17b5d9f40ed4b9ee4c56a723320244db5",
     "transformers==5.7.0","modelscope==1.33.0","accelerate","peft"])
'''),
code('''import torch
from importlib.metadata import version
assert torch.cuda.is_available(), "需要GPU Notebook"
assert torch.cuda.is_bf16_supported(), "本配置要求支持BF16的GPU，请更换镜像/资源或另行验证FP16路线"
(ROOT/"results").mkdir(exist_ok=True)
environment={name:version(name) for name in ["torch","transformers","ms-swift","modelscope","peft","accelerate"]}
environment["gpu"]=torch.cuda.get_device_name(0)
(ROOT/"results/environment.json").write_text(json.dumps(environment,indent=2),encoding="utf-8")
with (ROOT/"results/pip-freeze.txt").open("w") as f:
    subprocess.run([sys.executable,"-m","pip","freeze"],stdout=f,check=True)
print(environment)
'''),
md('## 2 下载魔搭基座并记录版本\n第一次探索可以用 master。正式复现请从模型页复制实际固定版本/提交；完整文件哈希会写入清单。'),
code('''from modelscope import snapshot_download
import hashlib
revision=input("基座固定revision（首次探索可输入master）：").strip()
assert revision, "请填写实际revision"
base=Path(snapshot_download("OpenBMB/MiniCPM5-2B",revision=revision,
                          local_dir=str(ROOT/"models/minicpm5-2b")))
files=[]
for path in sorted(base.rglob("*")):
    if path.is_file() and not any(part.startswith(".") for part in path.relative_to(base).parts):
        with path.open("rb") as f: checksum=hashlib.file_digest(f,"sha256").hexdigest()
        files.append({"path":str(path.relative_to(base)),"bytes":path.stat().st_size,"sha256":checksum})
(ROOT/"results/base-manifest.json").write_text(json.dumps(
    {"model_id":"OpenBMB/MiniCPM5-2B","requested_revision":revision,"files":files},indent=2),encoding="utf-8")
print(base)
'''),
md('## 3 生成教学数据\n训练 320、验证 64、测试 96 条，外围模板分离。这是合成教学集，不能代表真实用户分布。'),
code('''run([sys.executable,"examples/build_data.py"])
from task_contract import read_jsonl
print(read_jsonl(ROOT/"data/train.jsonl")[0])
'''),
md('## 4 测试基座\n不使用测试结果调参；调参应使用 dev_gold.jsonl。这里保存第一次冻结协议下的测试结果。'),
code('''run([sys.executable,"examples/predict_todo.py","--model",base,"--out","results/base.jsonl"])
run([sys.executable,"examples/evaluate_todo.py","--predictions","results/base.jsonl",
     "--report","results/base-report.json"])
'''),
md('## 5 启动 LoRA 训练\n下面是初稿资源配置。日志正常结束仍需通过任务评测。'),
code('''import os
os.environ["CUDA_VISIBLE_DEVICES"]="0"
run(["swift","sft","--model",base,"--model_type","llama","--template","minicpm5_2b",
     "--tuner_type","lora","--dataset","data/train.jsonl","--val_dataset","data/dev.jsonl",
     "--target_modules","q_proj","k_proj","v_proj","o_proj","gate_proj","up_proj","down_proj",
     "--lora_rank","16","--lora_alpha","32","--lora_dropout","0.05",
     "--num_train_epochs","2","--learning_rate","1e-4","--warmup_ratio","0.05",
     "--per_device_train_batch_size","1","--per_device_eval_batch_size","1",
     "--gradient_accumulation_steps","8","--max_length","512","--gradient_checkpointing","true",
     "--bf16","true","--eval_strategy","steps","--eval_steps","20",
     "--save_strategy","steps","--save_steps","20","--save_total_limit","2",
     "--logging_steps","5","--seed","47","--output_dir","runs/todo"])
'''),
md('## 6 选择实际检查点并合并\n选择最后检查点可以复现流程；若要比较多个检查点，使用验证集选定后再冻结最终测试。'),
code('''checkpoints=sorted((ROOT/"runs/todo").rglob("checkpoint-*"))
checkpoints=[p for p in checkpoints if (p/"adapter_config.json").is_file()]
for i,p in enumerate(checkpoints): print(i,p)
if not checkpoints: raise RuntimeError("未找到适配器检查点，检查训练日志")
index=int(input("要导出的检查点编号："))
adapter=checkpoints[index]
merged=ROOT/"artifacts/todo-merged"
run(["swift","export","--model",base,"--model_type","llama","--template","minicpm5_2b",
     "--adapters",adapter,"--merge_lora","true","--output_dir",merged])
(ROOT/"results/training-artifacts.json").write_text(json.dumps(
    {"adapter":str(adapter),"merged":str(merged),"base_revision":revision},indent=2),encoding="utf-8")
'''),
md('## 7 测试合并模型\n非法原始输出、超时和缺失预测均计失败，不修复 JSON 后重算。'),
code('''run([sys.executable,"examples/predict_todo.py","--model",merged,"--out","results/merged.jsonl"])
run([sys.executable,"examples/evaluate_todo.py","--predictions","results/merged.jsonl",
     "--report","results/merged-report.json"])
base_report=json.loads((ROOT/"results/base-report.json").read_text())
merged_report=json.loads((ROOT/"results/merged-report.json").read_text())
for key in ["schema_valid_rate","exact_record_rate","field_accuracy","null_preservation_rate"]:
    print(key,"base=",base_report[key],"merged=",merged_report[key])
'''),
md('''## 8 转换 发布与手机验证

按 Part 3 第 6 至 9 节继续操作：用固定 llama.cpp 转换合并权重并量化；用同测试集评测 Q4 / Q8；为发布目录填写模型卡；创建自己的魔搭仓库后显式运行 upload_model.py；注册自定义模型并构建 Android App。

本 Notebook 不上传模型、不生成 APK，也不把 GPU 评测当成手机报告。模板见 `model-card-template.md`，手机实测表在章节中。''')])

    write('02_minicpmv_inspection_baseline.ipynb',[
md('''# MiniCPM-V 手机巡检单图基线

先用授权图片验证单图理解和结构输出，再在手机验收。此 Notebook 使用公开的 4.6 路线，尚未执行真实图片推理。完整业务流见 Part 5。'''),
code(LOCATE),
md('## 1 准备推理依赖\n保留镜像中匹配的 PyTorch 与 torchvision。安装后重启内核。'),
code('''run([sys.executable,"-m","pip","install","transformers==5.7.0","modelscope==1.33.0",
     "accelerate","Pillow","torchvision","av"])
'''),
md('## 2 从魔搭下载固定模型\n使用完整40位Git提交。ModelScope 1.33.0的snapshot_download不接受该仓库的提交哈希；配套下载器使用固定文件接口并逐文件校验SHA256。'),
code('''from download_vision_model import download_fixed
revision=input("MiniCPM-V 4.6完整Git提交（回车使用已验证提交）：").strip() or "fd02313ad21ac485c595cb01231a3bded449cff5"
model_dir=download_fixed(revision, ROOT/"models/minicpm-v-4.6")
(ROOT/"results").mkdir(exist_ok=True)
(ROOT/"results/vision-config.json").write_text(json.dumps(
    {"model":"OpenBMB/MiniCPM-V-4.6","requested_revision":revision,
     "downsample_mode":"16x","max_slice_nums":1,"enable_thinking":False},indent=2),encoding="utf-8")
'''),
md('## 3 上传自有或授权照片\n使用真实存在的本地路径。图片未包含在教学包中。'),
code('''image_path=Path(input("授权图片的本地路径：").strip()).expanduser().resolve()
assert image_path.is_file()
import hashlib
with image_path.open("rb") as f: image_hash=hashlib.file_digest(f,"sha256").hexdigest()
print("Image SHA256:",image_hash)
run([sys.executable,"examples/vision_baseline.py","--model",model_dir,
     "--image",image_path,"--downsample","16x","--out","results/inspection-one.json"])
'''),
md('## 4 审阅原始输出\n结构合法不代表视觉识别正确。人工对照照片判断对象、现象与无依据补充。'),
code('''result=json.loads((ROOT/"results/inspection-one.json").read_text(encoding="utf-8"))
print(json.dumps(result,ensure_ascii=False,indent=2))
'''),
md('## 5 用同一图片比较 4x\n这一调用必须同时改变预处理与模型生成的 downsample_mode。'),
code('''run([sys.executable,"examples/vision_baseline.py","--model",model_dir,
     "--image",image_path,"--downsample","4x","--out","results/inspection-one-4x.json"])
'''),
md('''## 6 继续手机与业务验收

使用官方 Apps 固定版本和相匹配的 LLM / mmproj，接入 `android/InspectionRunner.kt` 与本地记录组件。按 Part 5 的验收矩阵测试飞行模式、新照片、人工确认、离线保存和显式同步。

电脑模拟台账可先运行 `examples/ledger.py`；它不承担图像推理。JSON 教学夹具只用于验证接口，不是视觉测试结果。''')])
    print('Created 2 unexecuted notebooks')

if __name__=='__main__': main()
