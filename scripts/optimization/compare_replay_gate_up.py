"""Compare captured real Gate/Up to exact packed M120+A8 group reference.

Offline only. No board action, no inferred tolerance, no full-model acceptance.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import numpy as np
from measurement import sha256, write_json
from m120_group_reference import group_reference

root = Path(__file__).resolve().parents[2]
base = root / 'deployment/mage_vl4b/optimization_v1'
layout_root = Path(sys.argv[1])
out = base / 'runs/OP01-replay01-gate-up-reference/result.json'
if out.exists():
    raise RuntimeError('Immutable result exists')

def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod

runtime_path = root / 'deployment/mage_vl4b/m175_m120_fixed_text_candidate/runtime/contract_runtime.py'
fixture_path = root / 'deployment/mage_vl4b/m120_text4b_runtime/m120_fixture.py'
runtime = load_module('exact_packet_reference', runtime_path)
fixture = load_module('exact_weight_decoder', fixture_path)
capture = base / 'runs/OP01-replay01-real-capture'
assert sha256(capture/'manifest.json') == 'b7a479ac23db5703989fb40808ba8c46bbd055bba9830901629933d82b80d8ff'
manifest = json.loads((capture/'manifest.json').read_text())
arrays = {}
for entry in manifest['files']:
    path = capture/entry['file']
    assert sha256(path) == entry['sha256']
    arrays[entry['name']] = np.load(path, allow_pickle=False)
plan = json.loads((base/'runs/OP01-file-cache-probe-01/plan.json').read_text())
assert sha256(layout_root/'SIXPORT_LAYOUT_MANIFEST.json') == plan['layout_sha256']
windows = []
for window in plan['windows']:
    with (layout_root/f"weights{window['shard']}.bin").open('rb') as f:
        f.seek(window['offset'])
        raw = f.read(window['bytes'])
    assert len(raw) == window['bytes']
    assert hashlib.sha256(raw).hexdigest() == window['sha256']
    windows.append(raw)
contract_path = root/'deployment/mage_vl4b/m175_m120_fixed_text_candidate/contracts/M126_LANGUAGE_RUNTIME_CONTRACT_RESULT.json'
chain = json.loads(contract_path.read_text())['chains'][3]
assert chain['family'] == 'gate_up' and chain['layer'] == 0
board_path = base/'gates/G01-decode-replay/attempt_01/board_result.json'
assert sha256(board_path) == '02dd529c05b890b11bcf1ce444054dcefee1181667723a96fcea724b430611db'
board = json.loads(board_path.read_text())
attempt = [a for a in board['board_evidence']['scale_attempts'] if a['layer']==0 and a['family']=='gate_up']
assert len(attempt)==1 and len(attempt[0]['attempted_shifts'])==1
shift = attempt[0]['selected_shift']
_, codes, scales = runtime.quantize_t32(arrays['input'], chain['groups'], shift)
expected = {n: np.full_like(a, np.nan) for n,a in arrays.items() if n.endswith(('gate_proj','up_proj'))}
for d in chain['descriptors']:
    parts = []
    blocks = d['rows_per_shard']//8
    words = 1+4*d['bits']
    start = d['offset_words']*16-plan['windows'][0]['offset']
    for raw in windows:
        packed = np.frombuffer(raw[start:start+d['record_bytes_per_shard']], np.uint8).reshape(chain['groups'],blocks,words,16).transpose(1,0,2,3)
        values = []
        for block in packed:
            decoded = [fixture._decode_weights(record,d['bits']) for record in block]
            weights = np.stack([v[0] for v in decoded])
            ws = np.stack([v[1] for v in decoded]).astype('<f2')
            value = group_reference(codes[:1],scales[:1],weights,ws)
            values.append(np.ldexp(value.astype(np.float32),-shift))
        parts.append(np.concatenate(values,axis=1))
    assembled = np.concatenate(parts,axis=1)[:,:d['valid_rows']]
    expected[d['module']][:,d['row_start']:d['row_start']+d['valid_rows']] = assembled
    print('REFERENCE_DESCRIPTOR_DONE', d['descriptor_index'], flush=True)
metrics = {}
for name, ref in expected.items():
    obs = arrays[name]
    assert np.isfinite(ref).all() and np.isfinite(obs).all()
    delta = obs.astype(np.float64)-ref.astype(np.float64)
    a,b = obs.astype(np.float64).ravel(),ref.astype(np.float64).ravel()
    metrics[name] = dict(elements=obs.size,exact_count=int(np.count_nonzero(obs.view('u4')==ref.view('u4'))),
        max_abs=float(np.max(np.abs(delta))),rmse=float(np.sqrt(np.mean(delta**2))),
        relative_l2=float(np.linalg.norm(delta)/np.linalg.norm(b)),cosine=float(a@b/(np.linalg.norm(a)*np.linalg.norm(b))))
result = dict(status='MEASURED',scope='Actual layer0 Gate/Up only; packed M120 plus transmitted A8',
    full_model_pass=False,threshold_inferred=False,scale_shift=shift,metrics=metrics,
    board_result_sha256=sha256(board_path),capture_manifest_sha256=sha256(capture/'manifest.json'),
    layout_sha256=plan['layout_sha256'],windows=plan['windows'],contract_sha256=sha256(contract_path),
    sources={p.name:sha256(p) for p in [Path(__file__),runtime_path,fixture_path,Path(__file__).with_name('m120_group_reference.py')]})
write_json(out,result)
print(json.dumps(result,ensure_ascii=False))
