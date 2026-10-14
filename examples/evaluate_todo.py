"""Strict JSON / field checks. Invalid responses count as failures, never repaired."""
import argparse
import json
from pathlib import Path
from task_contract import loads_strict, read_jsonl, validate

def score(gold, predictions):
    expected_ids = {x['id'] for x in gold}
    if len(expected_ids) != len(gold) or not gold:
        raise ValueError('gold IDs must be unique and nonempty')
    by_id = {}
    for p in predictions:
        if p['id'] in by_id or p['id'] not in expected_ids:
            raise ValueError('duplicate or unknown prediction ID: ' + p['id'])
        by_id[p['id']] = p
    valid, correct, fields, total_fields, null_ok, total_null, count_ok = 0, 0, 0, 0, 0, 0, 0
    failures = []
    for g in gold:
        truth = validate(g['expected'])
        output = by_id.get(g['id'], {}).get('output', '')
        try:
            parsed = validate(loads_strict(output))
            valid += 1
        except (ValueError, TypeError):
            parsed = None
        same = parsed == truth
        correct += same
        gt = truth['tasks']
        pt = parsed['tasks'] if parsed else []
        count_ok += parsed is not None and len(pt) == len(gt)
        # Missing/extra tasks also lower field accuracy. Sequence alignment follows input order.
        total_fields += 3 * max(len(gt), len(pt), 1)
        if not gt and not pt and parsed is not None:
            fields += 3
        for i, item in enumerate(gt):
            pred_item = pt[i] if i < len(pt) else {}
            for key in ('task', 'due_text', 'category'):
                fields += parsed is not None and pred_item.get(key, object()) == item[key]
                if key != 'task' and item[key] is None:
                    total_null += 1
                    null_ok += parsed is not None and pred_item.get(key, object()) is None
        if not same:
            failures.append({'id': g['id'], 'text': g['text'], 'expected': truth,
                             'output': output, 'case': g.get('case')})
    n = len(gold)
    return {'samples': n, 'present_predictions': len(by_id), 'schema_valid_rate': valid/n,
            'exact_record_rate': correct/n, 'task_count_accuracy': count_ok/n,
            'field_accuracy': fields/total_fields, 'null_preservation_rate': null_ok/total_null if total_null else None,
            'null_field_count': total_null, 'failures': failures}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--gold', default='data/test_gold.jsonl')
    parser.add_argument('--predictions', required=True)
    parser.add_argument('--report', required=True)
    args = parser.parse_args()
    report = score(read_jsonl(args.gold), read_jsonl(args.predictions))
    Path(args.report).parent.mkdir(parents=True, exist_ok=True)
    Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k != 'failures'}, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
