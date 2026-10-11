#!/usr/bin/env python3
"""Verify source identities and public timing summaries without hardware or tools."""

from pathlib import Path
import hashlib
import json
import math
import os
import statistics

ROOT = Path(__file__).resolve().parents[1]
if os.name == 'nt':
    ROOT = Path('\\\\?\\' + str(ROOT))
RUNS = ROOT / 'deployment/mage_vl4b/optimization_v1/runs'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    problems = []
    index = json.loads((ROOT / 'manifests/optimization_sync_20261011.json').read_text(encoding='utf-8'))
    for row in index['copied_source_and_evidence']:
        path = ROOT / row['path']
        if not path.is_file() or sha(path) != row['sha256']:
            problems.append('source identity: ' + row['path'])
    summary = json.loads((ROOT / 'experiments/optimization_20261011/SUMMARY.json').read_text(encoding='utf-8'))
    if index.get('raw_evidence_published') is not False:
        problems.append('publication scope')
    source = ROOT / 'tmp/m443_pair_pipeline_03/hls/mage_prefill_m89x_runtime/mage_prefill_m89x_runtime.cpp'
    if not source.is_file() or sha(source) != '4da9eadbe97d8b8b072e109ab44c155e5f45d715fff87b4f972a1ff538421040':
        problems.append('M443 original design identity')
    names = ['M441-complete-request-closure-17', 'M442-complete-request-parser-closure-01', 'M443-complete-request-closure-01']
    if [x['name'] for x in summary['experiments']] != names:
        problems.append('independent experiment identities')
    for result in summary['experiments']:
        name = result['name']
        for key, value in {'status':'PASS_NATURAL_IO_FULL_REQUEST_BENEFIT', 'completed_requests':12,
                           'formal_requests':8, 'production_promoted':False, 'IO_adjusted':False}.items():
            if result.get(key) != value:
                problems.append(f'summary contract: {name}/{key}')
        for key in ['raw_sha256', 'closure_sha256']:
            digest = result.get(key, '')
            if len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
                problems.append(f'original result identity format: {name}/{key}')
        blocks = result['blocks']
        a = [x for block in blocks for x in block['A_ms']]
        b = [x for block in blocks for x in block['B_ms']]
        deltas = result['paired_deltas_ms']
        gain = statistics.mean(a) - statistics.mean(b)
        margin = 3.182446305284263 * statistics.stdev(deltas) / math.sqrt(len(deltas))
        expected_values = {'A_mean_ms':statistics.mean(a), 'B_mean_ms':statistics.mean(b),
                           'paired_mean_gain_ms':statistics.mean(deltas),
                           'gain_percent':gain/statistics.mean(a)*100}
        for key, value in expected_values.items():
            if not math.isclose(result[key], value, rel_tol=1e-10, abs_tol=1e-7):
                problems.append(f'statistics: {name}/{key}')
        ci = [statistics.mean(deltas)-margin, statistics.mean(deltas)+margin]
        if any(not math.isclose(x,y,rel_tol=1e-8,abs_tol=1e-5) for x,y in zip(ci,result['paired_95percent_CI_ms'])):
            problems.append('paired interval: '+name)
        if len(a)!=4 or len(b)!=4 or len(deltas)!=4 or ci[0]<=0 or any(block['gain_ms']<=0 for block in blocks):
            problems.append('paired design: '+name)
    print(json.dumps({'status':'PASS' if not problems else 'FAIL',
                      'source_files_checked':len(index['copied_source_and_evidence']),
                      'raw_evidence_checked':False, 'independent_summaries_recomputed':len(summary['experiments']),
                      'board_execution_run':False, 'problems':problems},ensure_ascii=False,indent=2))
    return int(bool(problems))


if __name__ == '__main__':
    raise SystemExit(main())
