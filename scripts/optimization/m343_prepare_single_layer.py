"""Freeze an independent one-layer gate and verify its scope before transfer."""
import ast
import hashlib
import importlib
import json
import os
from pathlib import Path
import shutil
import sys
import time
sys.dont_write_bytecode = True
import numpy as np
from m343_layer_scope import derive
ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
BASE = ROOT / 'deployment/mage_vl4b/optimization_v1'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    package = BASE / 'candidates/M343-single-layer-01'
    run = BASE / 'runs/M343-single-layer-preparation-01'
    if package.exists() or run.exists():
        raise RuntimeError('Immutable preparation exists')
    recovery = {}
    for name in ('CURRENT_STATE.md', 'docsMILESTONES.md', 'DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md', 'deployment/mage_vl4b/BOARD_GATE_RESULT.json'):
        raw = (ROOT / name).read_bytes()
        decoded = raw.decode('utf-8-sig')
        recovery[name] = dict(bytes=len(raw), lines=len(decoded.splitlines()), sha256=hashlib.sha256(raw).hexdigest())
    prerequisite = BASE / 'runs/M342-single-chain-board-01/BOARD_RESULT.json'
    prior_sha = '6fcc267aab9fdebbc3641a921d6518c9c266f31a9b7a515972dc30d9fa948aea'
    if sha(prerequisite) != prior_sha or json.loads(prerequisite.read_text())['status'] != 'PASS':
        raise RuntimeError('Single chain prerequisite mismatch')
    board = json.loads((ROOT / 'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_text(encoding='utf-8-sig'))
    if board['latest_m342_single_chain']['sha256'] != prior_sha:
        raise RuntimeError('Authoritative board gate not synchronized')
    for name in ('CURRENT_STATE.md', 'docsMILESTONES.md'):
        if prior_sha not in (ROOT / name).read_text(encoding='utf-8-sig'):
            raise RuntimeError('Three-document gate synchronization incomplete')
    d = 'deployment/mage_vl4b/'
    dirs = [d + 'm242_m241_fixed_text_board_candidate', d + 'm181_m120_video_board_candidate',
            d + 'm175_m120_fixed_text_candidate/runtime', d + 'm175_m120_fixed_text_candidate/runtime/support']
    # Resolve recursively all local imports from the exact final search order.
    modules = {}
    pending = ['m238_prefill_runtime', 'm241_video_language_runtime', 'board_runtime', 'reserved_ddr_pool']
    while pending:
        name = pending.pop()
        if name in modules:
            continue
        found = next((ROOT / p / (name + '.py') for p in dirs if (ROOT / p / (name + '.py')).is_file()), None)
        if found is None:
            continue  # stdlib/NumPy/PYNQ are fixed environment dependencies
        modules[name] = found.relative_to(ROOT).as_posix()
        tree = ast.parse(found.read_text(encoding='utf-8-sig'))
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                pending.extend(a.name.split('.')[0] for a in n.names)
            elif isinstance(n, ast.ImportFrom) and n.module:
                pending.append(n.module.split('.')[0])
    expected_modules = {'board_runtime', 'contract_runtime', 'reserved_ddr_pool', 'm238_prefill_runtime',
                        'm236_prefill_runtime', 'm231_prefill_runtime', 'm230_prefill_runtime',
                        'm230_video_language_runtime', 'video_language_runtime', 'm241_video_language_runtime'}
    if set(modules) != expected_modules:
        raise RuntimeError('Unexpected recursive runtime closure: ' + str(sorted(modules)))
    release = ROOT / 'release_staging/kv260-mage-vl-4b-prebuilt-install-20260926-v7'
    files = []
    extra = [d + 'm175_m120_fixed_text_candidate/contracts/M126_LANGUAGE_RUNTIME_CONTRACT_RESULT.json',
             d + 'm175_m120_fixed_text_candidate/contracts/M126_LMHEAD_RUNTIME_CONTRACT_RESULT.json',
             d + 'm175_m120_fixed_text_candidate/auxiliary/M77_TEXT_AUX_MANIFEST.json',
             d + 'm175_m120_fixed_text_candidate/auxiliary/m77_text_aux_fp16.npz']
    for relative in sorted(set(modules.values()) | set(extra)):
        path = ROOT / relative
        if sha(path) != sha(release / relative):
            raise RuntimeError('Workspace/release source mismatch: ' + relative)
        files.append(dict(path=relative, bytes=path.stat().st_size, sha256=sha(path)))
    closure = dict(module_dirs=['runtime_site'] + dirs, modules=modules, files=files)
    source = (ROOT / modules['m241_video_language_runtime']).read_bytes()
    generated = derive(source)
    for name in ('m343_layer_scope.py', 'm343_single_layer_gate.py'):
        ast.parse((HERE / name).read_text())
    aux_path = ROOT / extra[-1]
    aux_manifest = json.loads((ROOT / extra[-2]).read_text())
    with np.load(aux_path, allow_pickle=False) as archive:
        norms = {name: archive[name] for name in archive.files}
    selected = aux_manifest['selected_embedding_ids']
    prompt = aux_manifest['prompt_token_ids']
    rows = np.asarray(norms['model.language_model.embed_tokens.weight'], np.float32)
    hidden = np.tile(np.stack([rows[selected.index(token)] for token in prompt]), (6, 1))[:159].copy()
    input_contract = dict(scope='layer0 only; repeated original fixed-text W3 embeddings; not video',
        selected_embedding_ids=selected, prompt_token_ids=prompt,
        input_tensor=dict(shape=list(hidden.shape), dtype=str(hidden.dtype), bytes=hidden.nbytes,
                          sha256=hashlib.sha256(hidden.tobytes()).hexdigest()),
        expected_families=['q', 'kv', 'attention_out', 'gate_up', 'mlp_down'], expected_logical_calls=25,
        exact_outputs=['all family FP32 arrays', 'hidden', 'K', 'V', 'adaptive retry identities'])
    sys.path[:0] = [str(ROOT / p) for p in dirs]
    actual = importlib.import_module('m241_video_language_runtime')
    if Path(actual.__file__).resolve() != (ROOT / modules['m241_video_language_runtime']).resolve():
        raise RuntimeError('Wrong offline M241 module')
    namespace = dict(vars(actual))
    namespace['LAYERS'] = 1
    exec(compile(generated, '<m343-generated>', 'exec'), namespace)
    one_layer = namespace['one_layer']
    original = actual.M241VideoLanguageModel.prefill
    oracle_ns = dict(vars(actual)); oracle_ns['LAYERS'] = 1
    cls_node = next(n for n in ast.parse(source.decode()).body if isinstance(n, ast.ClassDef))
    fn_node = next(n for n in cls_node.body if isinstance(n, ast.FunctionDef) and n.name == 'prefill')
    fn_text = ast.get_source_segment(source.decode(), fn_node)
    import textwrap
    fn_text = textwrap.dedent(fn_text)
    # get_source_segment leaves the first def unindented; dedent only its body.
    first, body = fn_text.split('\n', 1)
    fn_text = first + '\n' + textwrap.dedent(body)
    # Retrieve through inspect to preserve the original class indentation.
    import inspect
    fn_text = textwrap.dedent(inspect.getsource(original))
    final_inputs = []
    original_norm = actual.rms_norm
    def observed_norm(value, weight):
        if np.asarray(weight).shape == (2560,) and getattr(observed_norm, 'last', False):
            pass
        if weight is final_weight:
            final_inputs.append(value.copy())
        return original_norm(value, weight)
    final_weight = np.ones(2560, np.float32)
    oracle_ns['rms_norm'] = observed_norm
    exec(compile(fn_text, '<m343-original-one-layer-oracle>', 'exec'), oracle_ns)
    class FakeModel:
        def __init__(self):
            self.grouped_attention_calls = 0; self.grouped_attention_wall_ms = 0.0
            self.calls = []
            self.runtime = type('HeadObserver', (), {'lm_head': lambda _, value: np.zeros((1, 8), np.float32)})()
        def weight(self, name):
            if name == 'model.language_model.norm.weight': return final_weight
            return np.asarray(norms[name], np.float32)
        def _family(self, layer, family, values):
            if layer != 0: raise RuntimeError('Scope escaped layer0')
            self.calls.append(family)
            widths = {'q': [('self_attn.q_proj', 4096)], 'kv': [('self_attn.k_proj', 1024), ('self_attn.v_proj', 1024)],
                      'attention_out': [('self_attn.o_proj', 2560)], 'gate_up': [('mlp.gate_proj', 9728), ('mlp.up_proj', 9728)],
                      'mlp_down': [('mlp.down_proj', 2560)]}
            return {'model.language_model.layers.0.' + name: np.resize(values, (len(values), width)).astype(np.float32) * np.float32(0.03125)
                    for name, width in widths[family]}
        _attention_inputs = actual.M241VideoLanguageModel._attention_inputs
    candidate_model, original_model = FakeModel(), FakeModel()
    output, kv = one_layer(candidate_model, hidden.copy())
    _, _, original_kv = oracle_ns['prefill'](original_model, hidden.copy())
    checks = dict(original_loop_AST_identical=True, frozen_source_identity=True, recursive_modules=sorted(modules),
                  source_release_identity=True, original_scope_hidden_last_row_exact=output[-1:].tobytes() == final_inputs[0].tobytes(),
                  original_scope_kv_exact=all(a.tobytes() == b.tobytes() for a, b in zip(kv.keys + kv.values, original_kv.keys + original_kv.values)),
                  family_sequence_exact=candidate_model.calls == original_model.calls == input_contract['expected_families'],
                  original_module_layers_unchanged=actual.LAYERS == 36)
    if not all(v for v in checks.values()): raise RuntimeError('Offline scope checks failed')
    try:
        derive(source + b'\n')
        raise AssertionError('Changed source accepted')
    except RuntimeError:
        checks['source_drift_rejected'] = True
    try:
        one_layer(FakeModel(), np.zeros((159, 2559), np.float32))
        raise AssertionError('Invalid shape accepted')
    except ValueError:
        checks['invalid_input_rejected_before_family'] = True
    package.mkdir(parents=True); run.mkdir(parents=True)
    for name in ('CURRENT_STATE.md', 'docsMILESTONES.md', 'DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md', 'deployment/mage_vl4b/BOARD_GATE_RESULT.json'):
        shutil.copyfile(ROOT / name, run / (Path(name).name + '.before'))
    previous = BASE / 'candidates/M341-build-id-01'
    sources = {name: previous / name for name in ('m341_build_id_gate.py', 'measurement.py', 'board_safety.py',
               'm120_board_common.py', 'm120_board_env_preflight.py', 'HARDWARE_CLOSURE.json')}
    sources.update({name: HERE / name for name in ('m343_layer_scope.py', 'm343_single_layer_gate.py')})
    sources['weight_prefetch.py'] = BASE / 'candidates/M340-weight-prefetch-component-01/weight_prefetch.py'
    sources['SINGLE_CHAIN_PREREQUISITE.json'] = prerequisite
    for name, path in sources.items(): shutil.copyfile(path, package / name)
    (package / 'frozen_one_layer.py').write_text(generated, encoding='utf-8', newline='\n')
    for name, data in (('SOURCE_CLOSURE.json', closure), ('INPUT_CONTRACT.json', input_contract)):
        (package / name).write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8', newline='\n')
    runner = '''#!/usr/bin/env bash
set -euo pipefail
package_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$package_dir"
manifest_sha=${1:?exact package manifest SHA required}
printf '%s  PACKAGE_MANIFEST.json\\n' "$manifest_sha" | sha256sum -c -
sha256sum -c SHA256SUMS
sudo -n true
set +e
sudo -n env XILINX_XRT=/usr TMPDIR=/dev/shm PATH=/usr/local/share/pynq-venv/bin:/usr/local/bin:/usr/bin:/bin PYTHONDONTWRITEBYTECODE=1 \\
  /usr/local/share/pynq-venv/bin/python3 -B "$package_dir/m343_single_layer_gate.py" "$manifest_sha"
gate_rc=$?
set -e
printf 'M343_LAYER_DONE gate_rc=%s\\n' "$gate_rc"
exit "$gate_rc"
'''
    (package / 'run_m343_layer.sh').write_text(runner, encoding='utf-8', newline='\n')
    rows_out = [dict(path=p.name, bytes=p.stat().st_size, sha256=sha(p)) for p in sorted(package.iterdir())]
    (package / 'SHA256SUMS').write_text(''.join(r['sha256'] + '  ' + r['path'] + '\n' for r in rows_out), encoding='utf-8', newline='\n')
    rows_out.append(dict(path='SHA256SUMS', bytes=(package / 'SHA256SUMS').stat().st_size, sha256=sha(package / 'SHA256SUMS')))
    manifest = dict(schema='tellme-m343-independent-single-layer-v1', files=rows_out, file_count=len(rows_out),
                    total_bytes=sum(r['bytes'] for r in rows_out), performance_pass=False, hardware_changed=False)
    (package / 'PACKAGE_MANIFEST.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8', newline='\n')
    result = dict(status='PASS_OFFLINE_SINGLE_LAYER_GATE_PREPARATION', checks=checks, recovery_read=recovery,
                  input_contract=input_contract, manifest_sha256=sha(package / 'PACKAGE_MANIFEST.json'),
                  files=manifest['file_count'], bytes=manifest['total_bytes'], evidence_level='L0',
                  hardware_gate_run=False, performance_pass=False, next_step='COM3 same-terminal preflight then one layer only')
    (run / 'RESULT.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps(result))


if __name__ == '__main__': main()
