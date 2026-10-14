"""Recompute strict structure and timing from unchanged GPU raw responses."""
import argparse
import csv
import hashlib
import json
import statistics
from pathlib import Path
from inspection_contract import VISION_PROMPT, parse_draft


def percentile(values, q):
    values = sorted(values)
    index = (len(values) - 1) * q
    low = int(index)
    high = min(low + 1, len(values) - 1)
    return values[low] + (values[high] - values[low]) * (index - low)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--results', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    samples = {s['id']: s for s in manifest['images']}
    summary, comparison = {}, []
    for mode in ['16x', '4x']:
        report = json.loads((args.results / f'benchmark-gpu-v2-{mode}.json').read_text())
        assert report['status'] == 'completed' and len(report['rows']) == 20
        assert report['manifest_sha256'] == hashlib.sha256(args.manifest.read_bytes()).hexdigest()
        assert report['prompt']['sha256'] == hashlib.sha256(VISION_PROMPT.encode()).hexdigest()
        assert len({row['id'] for row in report['rows']}) == 20
        for row in report['rows']:
            assert row['sha256'] == samples[row['id']]['sha256']
            draft = parse_draft(row['raw'])
            assert row['schema_valid'] is True and row['draft'] == draft
            comparison.append({'mode': mode, 'id': row['id'], **draft,
                'source_label': samples[row['id']]['source_label'],
                'mentions_crack': any(w in draft['visible_issue'] for w in ['裂纹', '裂缝']),
                'elapsed_ms': row['elapsed_ms'], 'first_token_id_ms': row['first_generated_token_ms']})
        times = [row['elapsed_ms'] for row in report['rows']]
        summary[mode] = {'n': 20, 'strict_valid': 20, 'load_ms': report['load_ms'],
            'mean_ms': statistics.mean(times), 'median_ms': statistics.median(times),
            'p95_linear_ms': percentile(times, .95), 'min_ms': min(times), 'max_ms': max(times),
            'first_token_id_mean_ms': statistics.mean(row['first_generated_token_ms'] for row in report['rows']),
            'cuda_peak_allocated_mib': report['cuda_peak_allocated_bytes'] / 1024**2,
            'cuda_peak_reserved_mib': report['cuda_peak_reserved_bytes'] / 1024**2,
            'needs_retake': sum(row['draft']['needs_retake'] for row in report['rows']),
            'generic_surface_objects': sum(row['draft']['object'] in ['表面', 'surface'] for row in report['rows']),
            'timing_scope': report['timing_scope'], 'memory_scope': report['memory_scope']}
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    with (args.out / 'comparison-40.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(comparison[0]))
        writer.writeheader()
        writer.writerows(comparison)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
