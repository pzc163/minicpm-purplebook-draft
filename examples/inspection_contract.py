"""Contract for model drafts and confirmed business records."""
import hashlib
import json
import uuid
from task_contract import loads_strict

LEGACY_VISION_PROMPT = "你是现场照片观察助手。请用中文描述这张照片中的一个主要可见对象及其状态，只输出一个JSON对象。禁止输出数组、对象列表、多个JSON对象、Markdown或解释。必须完整包含且只包含四个字段：object、visible_issue、needs_retake、missing_fields。object为对象名称字符串或null；visible_issue为仅由照片支持的状态描述字符串或null，正常场景也填写可见状态，不猜测动作意图、故障原因或维修方法。needs_retake必须是true或false，照片暗、模糊、遮挡或无法判断时为true。missing_fields必须是JSON数组，不能是null：object为null时包含\"object\"，visible_issue为null时包含\"visible_issue\"，两者都有描述时为[]。两个描述均无法确认时输出{\"object\":null,\"visible_issue\":null,\"needs_retake\":true,\"missing_fields\":[\"object\",\"visible_issue\"]}；可以确认时请依据照片填写，不能直接照抄空值示例。不要生成位置、时间或处理状态。"

VISION_PROMPT_VERSION = 'inspection-v2-concise'
VISION_PROMPT = '观察这张照片，用中文描述主要可见对象或表面以及可见状态。只输出一个JSON对象，恰好包含object、visible_issue、needs_retake、missing_fields。object填写对象或表面名称，不要求画面中有独立物体；visible_issue填写可见现象，正常时也描述可见状态。不猜测原因、意图或维修方案。看不清的字段才填null；needs_retake为布尔值；missing_fields为值为null的字段名称数组，没有缺失则为[]。不要Markdown或解释。'

def parse_draft(text):
    v = loads_strict(text)
    if not isinstance(v,dict) or set(v) != {'object','visible_issue','needs_retake','missing_fields'}:
        raise ValueError('invalid draft fields')
    for key in ('object','visible_issue'):
        if v[key] is not None and (not isinstance(v[key],str) or not v[key].strip() or len(v[key])>300):
            raise ValueError('invalid observation')
    if type(v['needs_retake']) is not bool or not isinstance(v['missing_fields'],list):
        raise ValueError('invalid retake / missing fields')
    if set(v['missing_fields']) != {key for key in ('object','visible_issue') if v[key] is None}:
        raise ValueError('missing fields must match null fields')
    if len(set(v['missing_fields'])) != len(v['missing_fields']):
        raise ValueError('duplicate missing field')
    return v

def validate_record(v):
    fields = {'record_id','captured_at','location','object','visible_issue','image_sha256',
              'model_id','model_revision','confirmed_by','confirmed_at','human_confirmed'}
    if not isinstance(v,dict) or set(v)!=fields:
        raise ValueError('invalid record fields')
    uuid.UUID(v['record_id'])
    for key in fields - {'record_id','human_confirmed'}:
        if not isinstance(v[key],str) or not v[key].strip() or len(v[key])>500:
            raise ValueError('missing or invalid '+key)
    if v['human_confirmed'] is not True:
        raise ValueError('human confirmation required')
    from datetime import datetime
    for key in ('captured_at','confirmed_at'):
        stamp=datetime.fromisoformat(v[key].replace('Z','+00:00'))
        if stamp.tzinfo is None:
            raise ValueError('timezone required')
    if len(v['image_sha256'])!=64 or any(c not in '0123456789abcdef' for c in v['image_sha256']):
        raise ValueError('invalid image SHA256')
    return v

def digest(v):
    return hashlib.sha256(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
