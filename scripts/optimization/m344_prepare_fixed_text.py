"""Freeze the complete fixed-text candidate after synchronized layer evidence."""
import ast
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
sys.dont_write_bytecode = True
import numpy as np
ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
BASE = ROOT / 'deployment/mage_vl4b/optimization_v1'


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    package = BASE / 'candidates/M344-fixed-text-01'; run = BASE / 'runs/M344-fixed-text-preparation-01'
    if package.exists() or run.exists(): raise RuntimeError('Immutable preparation exists')
    recovery = {}
    for name in ('CURRENT_STATE.md', 'docsMILESTONES.md', 'DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md', 'deployment/mage_vl4b/BOARD_GATE_RESULT.json'):
        raw = (ROOT / name).read_bytes(); raw.decode('utf-8-sig')
        recovery[name] = dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
    prior = BASE / 'runs/M343-single-layer-board-01/BOARD_RESULT.json'
    prior_sha = 'a7fadf42f0afb65dddbffb862163a1c99684a04664318463894e598f314cf67e'
    proof = json.loads(prior.read_text(encoding='utf-8'))
    board = json.loads((ROOT / 'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_text(encoding='utf-8'))
    if sha(prior) != prior_sha or proof['status'] != 'PASS' or proof['unsafe_buffers_retained'] or board['latest_m343_single_layer']['sha256'] != prior_sha:
        raise RuntimeError('Single-layer identity/PASS mismatch')
    if not all(prior_sha in (ROOT / n).read_text(encoding='utf-8') for n in ('CURRENT_STATE.md', 'docsMILESTONES.md')):
        raise RuntimeError('Three-record synchronization incomplete')
    previous = BASE / 'candidates/M343-single-layer-01'
    closure = json.loads((previous / 'SOURCE_CLOSURE.json').read_text(encoding='utf-8'))
    relative = 'deployment/mage_vl4b/m175_m120_fixed_text_candidate/auxiliary/official_cpu_text_1token.json'
    reference_path = ROOT / relative
    if sha(reference_path) != 'bb7f5a34db949976eca159ab8a125508e178699dbe1cb90cfac675bc582243bb': raise RuntimeError('CPU fixed reference drift')
    closure['files'].append(dict(path=relative, bytes=reference_path.stat().st_size, sha256=sha(reference_path)))
    for row in closure['files']:
        path = ROOT / row['path']
        if sha(path) != row['sha256'] or path.stat().st_size != row['bytes']: raise RuntimeError('Source closure drift')
    selected = json.loads((previous / 'INPUT_CONTRACT.json').read_text(encoding='utf-8'))['selected_embedding_ids']
    ref = json.loads(reference_path.read_text(encoding='utf-8'))
    with np.load(ROOT / 'deployment/mage_vl4b/m175_m120_fixed_text_candidate/auxiliary/m77_text_aux_fp16.npz', allow_pickle=False) as archive:
        rows = np.asarray(archive['model.language_model.embed_tokens.weight'], np.float32)
    hidden = np.stack([rows[selected.index(token)] for token in ref['prompt_token_ids']])
    contract = dict(scope='Original 30-token fixed text, one generated token, all 36 layers and full LM head',
        selected_embedding_ids=selected, prompt_token_ids=ref['prompt_token_ids'], expected_token=17,
        input_tensor=dict(shape=list(hidden.shape), dtype=str(hidden.dtype), bytes=hidden.nbytes, sha256=hashlib.sha256(hidden.tobytes()).hexdigest()),
        exact_outputs=['Full 151936 logits', '36 K and 36 V tensors', 'All family input/output bytes', 'Adaptive retry contract'], performance_pass=False)
    # Exercise the exact board verifier functions locally without importing PYNQ
    # or executing any simulated language inference as board evidence.
    source = (HERE / 'm344_fixed_text_gate.py').read_text(encoding='utf-8')
    tree = ast.parse(source); namespace = {'np': np, 'hashlib': hashlib}
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in ('tensor', 'exact_array', 'check_call_contract'):
            exec(ast.get_source_segment(source, node), namespace)
    check, exact = namespace['check_call_contract'], namespace['exact_array']
    attempts = [dict(layer=0 if i < 154 else None, attempted_shifts=[6], selected_shift=6) for i in range(162)]
    row = dict(scale_attempts=attempts, logical_calls=162, host_calls=162, retry_count=0, retry_launches=0,
               nonfinite_detections=0, logical_expected_macros=123)
    check(row, 123)
    with_head_retry = copy.deepcopy(row)
    with_head_retry['scale_attempts'][-1].update(attempted_shifts=[6, 5], selected_shift=5)
    with_head_retry.update(host_calls=163, retry_count=1)
    check(with_head_retry, 123)
    with_language_retry = copy.deepcopy(with_head_retry)
    with_language_retry['scale_attempts'][0].update(attempted_shifts=[6, 5, 4], selected_shift=4)
    with_language_retry.update(host_calls=165, retry_count=3, retry_launches=2, nonfinite_detections=2)
    check(with_language_retry, 123)
    rejected = []
    for name, edits in [('missing_physical', dict(host_calls=164)), ('pipeline_count', dict(retry_launches=3)),
                        ('macro_count', dict(logical_expected_macros=124))]:
        bad = copy.deepcopy(with_language_retry); bad.update(edits)
        try: check(bad, 123)
        except RuntimeError: rejected.append(name)
        else: raise AssertionError('Invalid retry/macro contract accepted')
    positive, negative = np.array([0.0], np.float32), np.array([-0.0], np.float32)
    assert not exact(positive, negative) and exact(hidden, hidden.copy())
    flipped = hidden.copy(); flipped.view(np.uint32).flat[0] ^= np.uint32(1)
    assert not exact(hidden, flipped)
    language = json.loads((ROOT / 'deployment/mage_vl4b/m175_m120_fixed_text_candidate/contracts/M126_LANGUAGE_RUNTIME_CONTRACT_RESULT.json').read_text(encoding='utf-8'))
    head = json.loads((ROOT / 'deployment/mage_vl4b/m175_m120_fixed_text_candidate/contracts/M126_LMHEAD_RUNTIME_CONTRACT_RESULT.json').read_text(encoding='utf-8'))
    sequence = [(layer, family) for layer in range(36) for family in
                (('q', 'kv', 'attention_out', 'gate_up', 'mlp_down') if layer < 10 else ('qkv', 'attention_out', 'gate_up', 'mlp_down'))]
    assert sequence == [(c['layer'], c['family']) for c in language['chains']]
    assert len(sequence) + len(head['chains']) == 162
    expected_macros = sum(c['expected_macros'] for c in language['chains'] + head['chains'])
    assert expected_macros == language['contract']['total_expected_macros'] + head['contract']['total_expected_macros']
    # Final entry imports with the same module search order, before transfer.
    sys.path[:0] = [str(ROOT / p) for p in closure['module_dirs'] if p != 'runtime_site']
    import importlib
    for name, relative_module in closure['modules'].items():
        if name == 'reserved_ddr_pool':
            # Linux-only fcntl is unavailable on Windows. Do not mock/import it
            # as board evidence: exact source/AST here; real import before overlay.
            ast.parse((ROOT / relative_module).read_text(encoding='utf-8'))
            continue
        module = importlib.import_module(name)
        if Path(module.__file__).resolve() != (ROOT / relative_module).resolve(): raise RuntimeError('Local exact import path differs')
    checks = dict(retry_none_and_language_and_head_accepted=True, invalid_retry_macro_rejected=rejected,
                  signed_zero_and_one_bit_difference_rejected=True, frozen_input_exact=True,
                  complete_162_chain_sequence=True, macros=expected_macros, exact_windows_compatible_imports=True,
                  linux_reserved_pool_import='Exact source/AST local; actual board import before any overlay')
    package.mkdir(parents=True); run.mkdir(parents=True)
    for name in recovery: shutil.copyfile(ROOT / name, run / (Path(name).name + '.before'))
    for name in ('m341_build_id_gate.py', 'measurement.py', 'board_safety.py', 'm120_board_common.py',
                 'm120_board_env_preflight.py', 'HARDWARE_CLOSURE.json', 'weight_prefetch.py'):
        shutil.copyfile(previous / name, package / name)
    shutil.copyfile(prior, package / 'SINGLE_LAYER_PREREQUISITE.json')
    shutil.copyfile(HERE / 'm344_fixed_text_gate.py', package / 'm344_fixed_text_gate.py')
    for name, payload in (('SOURCE_CLOSURE.json', closure), ('INPUT_CONTRACT.json', contract)):
        (package / name).write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8', newline='\n')
    runner = '''#!/usr/bin/env bash
set -euo pipefail
package_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$package_dir"
manifest_sha=${1:?exact manifest SHA required}
printf '%s  PACKAGE_MANIFEST.json\\n' "$manifest_sha" | sha256sum -c -
sha256sum -c SHA256SUMS
sudo -n true
set +e
sudo -n env XILINX_XRT=/usr TMPDIR=/dev/shm PATH=/usr/local/share/pynq-venv/bin:/usr/local/bin:/usr/bin:/bin PYTHONDONTWRITEBYTECODE=1 \\
  /usr/local/share/pynq-venv/bin/python3 -B "$package_dir/m344_fixed_text_gate.py" "$manifest_sha"
gate_rc=$?
set -e
printf 'M344_TEXT_DONE gate_rc=%s\\n' "$gate_rc"
exit "$gate_rc"
'''
    (package / 'run_m344_text.sh').write_text(runner, encoding='utf-8', newline='\n')
    items = [dict(path=p.name, bytes=p.stat().st_size, sha256=sha(p)) for p in sorted(package.iterdir())]
    (package / 'SHA256SUMS').write_text(''.join(i['sha256'] + '  ' + i['path'] + '\n' for i in items), encoding='utf-8', newline='\n')
    items.append(dict(path='SHA256SUMS', bytes=(package / 'SHA256SUMS').stat().st_size, sha256=sha(package / 'SHA256SUMS')))
    manifest = dict(schema='tellme-m344-fixed-text-weight-prefetch-v1', files=items, file_count=len(items),
                    total_bytes=sum(i['bytes'] for i in items), hardware_changed=False, performance_pass=False)
    (package / 'PACKAGE_MANIFEST.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8', newline='\n')
    result = dict(status='PASS_OFFLINE_FIXED_TEXT_PREPARATION', recovery_read=recovery, checks=checks,
                  files=len(items), bytes=manifest['total_bytes'], manifest_sha256=sha(package / 'PACKAGE_MANIFEST.json'),
                  rejected_attempts=['Windows exact-all-import probe rejected Linux fcntl in reserved_ddr_pool before package/transfer; no mock, retain real board import before overlay'],
                  evidence_level='L0', hardware_gate_run=False, performance_pass=False)
    (run / 'RESULT.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps(result))


if __name__ == '__main__': main()
