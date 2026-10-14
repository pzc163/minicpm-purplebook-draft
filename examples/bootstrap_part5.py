"""Create an isolated inference environment while retaining the base CUDA stack."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import venv

PINNED = ['transformers==5.7.0', 'modelscope==1.33.0', 'accelerate==1.14.0',
          'Pillow==11.3.0', 'av==18.1.0', 'tokenizers==0.22.2', 'requests==2.32.5']


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--venv', type=Path, default=Path('.venv-part5'))
    parser.add_argument('--out', type=Path, default=Path('results/reproduction/environment.json'))
    args = parser.parse_args()
    target = args.venv.resolve()
    if not (target / 'bin/python').exists():
        venv.EnvBuilder(with_pip=True, system_site_packages=True).create(target)
    python = str(target / 'bin/python')
    subprocess.run([python, '-m', 'pip', 'install', *PINNED], check=True)
    probe = '''import json,platform,importlib.metadata as m,torch,torchvision,transformers
assert torch.cuda.is_available(), 'Select a GPU Notebook with a working PyTorch/CUDA base'
assert transformers.__version__ == '5.7.0'
assert torch.ones(1,device='cuda').item()==1
print(json.dumps({'python':platform.python_version(),'torch':torch.__version__,
 'torch_cuda':torch.version.cuda,'torchvision':torchvision.__version__,
 'gpu':torch.cuda.get_device_name(0),'packages':{x:m.version(x) for x in
 ['transformers','modelscope','accelerate','Pillow','av','tokenizers','requests']},
 'scope':'isolated venv; GPU torch/torchvision inherited from the Notebook base, not installed by this script'},indent=2))'''
    report = subprocess.check_output([python, '-c', probe], text=True)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(report, encoding='utf-8')
    freeze = subprocess.check_output([python, '-m', 'pip', 'freeze'], text=True)
    args.out.with_name('pip-freeze.txt').write_text(freeze, encoding='utf-8')
    print(report)
    print('Inference interpreter:', python)


if __name__ == '__main__':
    main()
