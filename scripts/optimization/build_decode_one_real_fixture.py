"""Frozen real-board Gate/Up replay fixture; expected output comes from capture."""
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import sys
import numpy as np
from measurement import sha256,write_json
root=Path(__file__).resolve().parents[2];base=root/'deployment/mage_vl4b/optimization_v1'
layout=Path(sys.argv[1]);out=base/'runs/OP01-decode-one-real-fixture'
if out.exists():raise RuntimeError('Immutable fixture exists')
capture=base/'runs/OP01-replay01-real-capture'
assert sha256(capture/'manifest.json')=='b7a479ac23db5703989fb40808ba8c46bbd055bba9830901629933d82b80d8ff'
arrays={}
for item in json.loads((capture/'manifest.json').read_text())['files']:
    path=capture/item['file'];assert sha256(path)==item['sha256']
    arrays[item['name']]=np.load(path,allow_pickle=False)
plan=json.loads((base/'runs/OP01-file-cache-probe-01/plan.json').read_text())
assert sha256(layout/'SIXPORT_LAYOUT_MANIFEST.json')==plan['layout_sha256']
windows=[]
for row in plan['windows']:
    with (layout/f"weights{row['shard']}.bin").open('rb') as f:
        f.seek(row['offset']);raw=f.read(row['bytes'])
    assert len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256']
    windows.append(raw)
path=root/'deployment/mage_vl4b/m175_m120_fixed_text_candidate/runtime/contract_runtime.py'
spec=importlib.util.spec_from_file_location('packet_contract',path)
mod=importlib.util.module_from_spec(spec);sys.modules[spec.name]=mod;spec.loader.exec_module(mod)
contract=root/'deployment/mage_vl4b/m175_m120_fixed_text_candidate/contracts/M126_LANGUAGE_RUNTIME_CONTRACT_RESULT.json'
chain=json.loads(contract.read_text())['chains'][3]
packet=mod.pack_chain_input(chain,arrays['input'],descriptor_offset_base_words=chain['staged_base_words'],activation_scale_shift=6)
expected=[]
for d in chain['descriptors']:
    rows=d['rows_per_shard'];blocks=rows//8
    data=np.zeros((32,4*rows),'<f2')
    observed=arrays[d['module']][0,d['row_start']:d['row_start']+d['valid_rows']]
    data[0,:d['valid_rows']]=np.ldexp(observed,6).astype('<f2')
    assert np.array_equal(np.ldexp(data[0,:d['valid_rows']].astype(np.float32),-6),observed)
    values=data.reshape(32,4,blocks,4,2).transpose(2,0,1,3,4).view('<u2')
    wire=np.zeros((blocks,32,4,4,4),'<u2');wire[...,0]=values[...,0];wire[...,2]=values[...,1]
    expected.append(wire.tobytes())
expected=b''.join(expected)
assert len(expected)==chain['output_bytes']
config=int(chain['config_u32'],16)|(1<<24)
out.mkdir()
fixture=out/'real_gate_up.bin'
with fixture.open('xb') as f:
    f.write(b'OP1REAL1');f.write(struct.pack('<IIII',len(windows[0]),len(packet),len(expected),config))
    for raw in windows:f.write(raw)
    f.write(packet);f.write(expected)
write_json(out/'manifest.json',dict(status='FIXTURE_PREPARED_NOT_TESTED',fixture_sha256=sha256(fixture),
    bytes=fixture.stat().st_size,weight_window_hashes=[r['sha256'] for r in plan['windows']],
    input_shape=[1,2560],output_elements=19456,config=hex(config),scale_shift=6,
    expected_source='real REPLAY01 Gate/Up capture; token0 rescaled exactly; all inactive lanes zero',
    builder_sha256=sha256(__file__),contract_sha256=sha256(contract)))
print('REAL_GATE_UP_FIXTURE_READY '+sha256(fixture))
