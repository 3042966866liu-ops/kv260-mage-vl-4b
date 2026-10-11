"""Bind local M319 evidence without repeating the GPU gate."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
sys.dont_write_bytecode = True
root = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256((root / path).read_bytes()).hexdigest()


def main():
    subprocess.run([sys.executable, '-B', str(root/'scripts/m319_test_token_layout.py')], check=True)
    name = 'deployment/mage_vl4b/M319_TOKEN_ADAPTER_GPU_RESULT.json'
    r = json.loads((root/name).read_text(encoding='utf-8'))
    assert r['status'] == 'PASS_INTERFACE_AND_EXPLORATORY_FORWARDS_NOT_QUALITY'
    assert r['source_sha256'] == sha('scripts/m319_token_adapter_gpu_gate.py')
    assert r['identity']['status'] == 'PASS_EXACT'
    assert r['identity']['kv_lengths'] == list(range(849, 861))
    assert r['board_modified'] is False and r['semantic_accuracy_passed'] is False
    assert len(r['records']) == 6
    for fraction, n in ((.75,653),(.5,457),(.25,261)):
        rows = [x for x in r['records'] if x['fraction'] == fraction]
        assert {x['method'] for x in rows} == {'uniform','content'}
        for x in rows:
            assert x['total_tokens'] == n
            assert len(x['visual_indices']) == n-65
            assert sorted(set(x['visual_indices'])) == x['visual_indices']
            assert len(x['token_ids']) == len(x['kv_lengths'])
            assert x['kv_lengths'] == list(range(n,n+len(x['token_ids'])))
    board = json.loads((root/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_text(encoding='utf-8'))
    assert board['latest_m319_offline_token_adapter']['board_execution_run'] is False
    paths = ['bact/token_layout.py','bact/feature_budget.py', 'scripts/m319_test_token_layout.py',
             'scripts/m319_token_adapter_gpu_gate.py','scripts/m319_run_token_adapter_wsl.sh',
             'scripts/m319_verify_evidence.py',name,'M319_TOKEN_ADAPTER_REPORT.md']
    for p in paths:
        if p.endswith('.py'):
            compile((root/p).read_text(encoding='utf-8'),p,'exec')
    out = root/'deployment/mage_vl4b/M319_LOCAL_EVIDENCE_VERIFICATION.json'
    tmp = out.with_suffix('.partial.json')
    tmp.write_text(json.dumps(dict(status='PASS_LOCAL_EVIDENCE_ONLY', unit_tests=5,
        board_execution_run=False, files=[dict(path=p,sha256=sha(p)) for p in paths]),indent=2),encoding='utf-8')
    os.replace(tmp,out)
    print('M319_LOCAL_EVIDENCE_VERIFIED')


if __name__ == '__main__':
    main()
