"""Wrap the verified release Notebook with anonymous download and hash validation."""
import ast
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent


def main():
    notebook=json.loads((ROOT/'dist/part5-release/notebooks/part5_reproduce.ipynb').read_text())
    setup='''from pathlib import Path
from urllib.request import urlopen
import hashlib, io, os, zipfile
PACKAGE_URL='https://modelscope.cn/datasets/pzc163/minicpm-v-inspection-part5/resolve/master/part5-reproduction-v2.zip?view=false'
PACKAGE_SHA256='55fee5d70e416e310573c08a3a2739ad4482a4f590b298b7ca307d91d15670b5'
with urlopen(PACKAGE_URL,timeout=120) as response:
    package=response.read()
assert hashlib.sha256(package).hexdigest()==PACKAGE_SHA256, 'Published package hash mismatch'
HOME=Path.cwd()/'part5-public-reproduction-v2'
HOME.mkdir(exist_ok=True)
with zipfile.ZipFile(io.BytesIO(package)) as archive:
    assert sum(x.file_size for x in archive.infolist())<5_000_000
    for item in archive.infolist():
        path=(HOME/item.filename).resolve()
        assert path.is_relative_to(HOME.resolve()) and not path.is_symlink()
        assert (item.external_attr >> 16) & 0o170000 != 0o120000
    if not (HOME/'part5-release/release-manifest.json').exists():
        archive.extractall(HOME)
os.chdir(HOME/'part5-release')
print('Anonymous download and package SHA256 verified:',len(package),PACKAGE_SHA256)
'''
    notebook['cells']=[{'cell_type':'markdown','metadata':{},'id':'share-intro',
        'source':['# 第五章 MiniCPM-V 公开复现入口\n',
        '\n此快照先从[公开数据集仓库](https://modelscope.cn/datasets/pzc163/minicpm-v-inspection-part5)匿名下载固定SHA256的复现包，再执行经验证的单图与20图两模式流程。选择GPU实例与普通Python3内核，按顺序执行所有单元。数据CC BY 4.0、原创代码MIT。\n',
        '\n原始结构结果为两模式各20/20；三图曾参与提示诊断，属于开发回归，不代表语义准确率或完整现场验收。语义问题和旧失败输出保留。\n']},
        {'cell_type':'code','metadata':{},'execution_count':None,'outputs':[],
         'id':'share-download','source':setup.splitlines(True)},*notebook['cells']]
    for cell in notebook['cells']:
        if cell['cell_type']=='code':ast.parse(''.join(cell['source']))
    out=ROOT/'notebooks/Part5-MiniCPM-V-Reproduce.ipynb'
    out.write_text(json.dumps(notebook,ensure_ascii=False,indent=2)+'\n')
    print(out)


if __name__=='__main__':main()
