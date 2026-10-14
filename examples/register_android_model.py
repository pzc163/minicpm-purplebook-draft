"""Register ONE custom text GGUF in the pinned official Android demo. No file-picker claim."""
import argparse
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import quote
from task_contract import PROMPT

APPS_COMMIT='d1aac05eecaac64b7fc35f1cc93a06b726ce10e3'

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--apps',required=True)
    p.add_argument('--repo',required=True,help='Your public ModelScope GGUF repository, owner/name')
    p.add_argument('--revision',required=True,help='Published immutable ModelScope revision, not master')
    p.add_argument('--gguf',required=True,help='Local GGUF used to compute checksum')
    a=p.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',a.repo):
        raise ValueError('invalid repo')
    if a.revision in {'main','master','latest'} or not re.fullmatch(r'[A-Za-z0-9_.-]+',a.revision):
        raise ValueError('use a fixed release revision')
    model=Path(a.gguf)
    if not model.is_file() or model.suffix!='.gguf':
        raise ValueError('expected existing GGUF')
    with model.open('rb') as f:
        md5=hashlib.file_digest(f,'md5').hexdigest()
    target=Path(a.apps)/'MiniCPM-V-demo-Android/app/src/main/java/com/example/minicpm_v_demo/ModelInfo.kt'
    source=target.read_text(encoding='utf-8')
    marker='val AVAILABLE_MODELS = listOf('
    if source.count(marker)!=1 or 'minicpm5-todo-custom' in source:
        raise ValueError('expected unpatched pinned ModelInfo.kt')
    # JSON string escaping is also suitable for these restricted Kotlin string values.
    url=f'https://www.modelscope.cn/models/{a.repo}/resolve/{quote(a.revision,safe="")}/{quote(model.name,safe="")}'
    entry='''
            ModelInfo(
                id = "minicpm5-todo-custom",
                displayName = "我的 MiniCPM 待办助手",
                descriptionResName = "微调后的文本模型，固定版本",
                ggufFileName = %s,
                directGgufUrl = %s,
                ggufMd5 = %s
            ),''' % tuple(json.dumps(x,ensure_ascii=False) for x in (model.name,url,md5))
    engine_path=target.parent/'LlamaEngine.kt'
    engine=engine_path.read_text(encoding='utf-8')
    load_marker='setEnableThinkingNative(getEnableThinking(context))\n                _state.value = LlamaState.ModelReady'
    clear_marker='_readyForSystemPrompt = true\n            Log.i(TAG, "Context fully reset - context recreated, ready for new conversation")'
    if engine.count(load_marker)!=1 or engine.count(clear_marker)!=1:
        raise ValueError('Expected pinned LlamaEngine; do not apply to another revision')
    call='''
                if (getSelectedModel(context).id == "minicpm5-todo-custom") {
                    setEnableThinking(false)
                    setSystemPrompt(TodoPrompts.SYSTEM)
                }'''
    engine=engine.replace(load_marker,load_marker+call)
    clear_insert='_readyForSystemPrompt = true'+call+'\n            Log.i(TAG, "Context fully reset - context recreated, ready for new conversation")'
    engine=engine.replace(clear_marker,clear_insert)
    # Prepare every edit before writing. Source files are user-reviewable and reversible.
    prompt='package com.example.minicpm_v_demo\n\nobject TodoPrompts {\n    const val SYSTEM = '+json.dumps(PROMPT,ensure_ascii=False)+'\n}\n'
    target.write_text(source.replace(marker,marker+entry),encoding='utf-8')
    engine_path.write_text(engine,encoding='utf-8')
    (target.parent/'TodoPrompts.kt').write_text(prompt,encoding='utf-8')
    print('Registered custom model and task system prompt in',target.parent)

if __name__=='__main__': main()
