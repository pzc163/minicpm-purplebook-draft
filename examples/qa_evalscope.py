"""Optional EvalScope organization; strict task metrics remain evaluate_todo.py."""
import argparse
import os

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--model',default='todo')
    p.add_argument('--api-url',default='http://127.0.0.1:8080/v1')
    a=p.parse_args()
    from evalscope import TaskConfig,run_task
    cfg=TaskConfig(model=a.model,eval_type='openai_api',api_url=a.api_url,
                   api_key=os.environ.get('MODEL_API_KEY','EMPTY'),datasets=['general_qa'],
                   dataset_args={'general_qa':{'local_path':'data/evalscope','subset_list':['todo']}},
                   generation_config={'temperature':0,'max_tokens':512})
    run_task(task_cfg=cfg)
