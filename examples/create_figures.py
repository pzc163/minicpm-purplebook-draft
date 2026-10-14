"""Exact workflow SVGs authored from the chapter contracts."""
from pathlib import Path
from html import escape

ROOT=Path(__file__).resolve().parents[1]
HEAD='''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="600" viewBox="0 0 1200 600"><defs><marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="5" orient="auto"><path d="M0 0 L10 5 L0 10 Z" fill="#7351b5" /></marker></defs><rect width="1200" height="600" rx="18" fill="#faf8ff" />'''
def text(x,y,s,size=24,color='#292238'):
    return f'<text x="{x}" y="{y}" text-anchor="middle" font-size="{size}" fill="{color}" font-family="PingFang SC, Microsoft YaHei, Noto Sans CJK SC, sans-serif">{escape(s)}</text>'
def box(x,y,w,title,sub):
    return f'<rect x="{x}" y="{y}" width="{w}" height="88" rx="12" fill="white" stroke="#b5a1d5" stroke-width="2" />'+text(x+w/2,y+36,title)+text(x+w/2,y+65,sub,18,'#675f73')
def arrow(x1,y1,x2,y2):
    return f'<path d="M{x1} {y1} L{x2} {y2}" stroke="#7351b5" stroke-width="3" fill="none" marker-end="url(#arrow)" />'
def main():
    out=ROOT/'figures';out.mkdir(exist_ok=True)
    s=HEAD+text(600,44,'MiniCPM 训练阶段与本章实践',30)
    s+=text(600,82,'完整训练建立基础能力，本章在已发布模型上做任务微调',19,'#675f73')
    for x,title,sub in [(60,'基础训练','稳定训练与衰减训练'),(435,'中期训练','强化目标能力与数据适配'),(810,'后训练','SFT、RL 与 OPD')]:
        s+=box(x,114,330,title,sub)
    s+=arrow(392,158,427,158)+arrow(767,158,802,158)
    s+=arrow(975,210,975,260)+text(600,270,'已发布的 MiniCPM5-2B',25)
    s+='<path d="M975 260 L975 292 L157 292 L157 337" stroke="#7351b5" stroke-width="3" fill="none" marker-end="url(#arrow)" />'
    for x,title,sub in [(30,'任务 LoRA','魔搭 Notebook'),(330,'合并权重','基座与适配器'),(630,'转换与量化','F16 / Q4 / Q8 GGUF'),(930,'手机运行','自定义模型与断网验证')]:
        s+=box(x,348,240,title,sub)
    for x in (280,580,880): s+=arrow(x,392,x+37,392)
    s+=text(600,490,'同一测试集比较基座、合并权重和量化产物',23)
    s+=text(600,530,'LoRA 适配器不是独立模型；手机运行需要合并、转换与引擎验证',19,'#675f73')+'</svg>'
    (out/'training-workflow.svg').write_text(s,encoding='utf-8')
    s=HEAD+text(600,44,'手机巡检记录的确认与同步流程',30)
    for x,title,sub in [(45,'拍照与位置','照片先保存在手机'),(430,'手机本地推理','仅提取可见信息'),(815,'人员核对修改','不自动确认草稿')]:s+=box(x,92,330,title,sub)
    s+=arrow(378,136,420,136)+arrow(764,136,804,136)
    s+=arrow(980,185,980,270)
    s+=text(1043,234,'确认',19)
    for x,title,sub in [(815,'离线保存','冻结记录与固定 UUID'),(430,'显式同步','回复匹配后标记成功'),(45,'业务台账','去重写入与状态更新')]:s+=box(x,282,330,title,sub)
    s+=arrow(807,326,769,326)+arrow(421,326,383,326)
    s+='<path d="M980 370 L980 405 L595 405 L595 377" fill="none" stroke="#a58fcb" stroke-width="2" stroke-dasharray="7 6" marker-end="url(#arrow)" />'
    s+=text(770,444,'同步失败：保留同一记录，等待再次同步',20,'#675f73')
    s+=text(600,504,'图片不清晰或字段缺失：补拍、重新生成或手工填写后再确认',21)
    s+=text(600,548,'原图留在手机；本示例只同步确认字段和图片哈希',20,'#675f73')+'</svg>'
    (out/'inspection-workflow.svg').write_text(s,encoding='utf-8')
    print('Created 2 workflow diagrams')

if __name__=='__main__':main()
