"""Offline comparison to frozen M128 fixture reference, not a new CSim/board gate."""
import importlib.util
import json
from pathlib import Path
import sys
import numpy as np
from measurement import sha256,write_json
from m120_group_reference import group_reference

root=Path(__file__).resolve().parents[2]
source=root/'deployment/mage_vl4b/m120_text4b_runtime/m120_fixture.py'
fixture=root/'deployment/mage_vl4b/m120_text4b_board_candidate/reference/m128_m120_real_record_csim_fixture.bin'
spec=importlib.util.spec_from_file_location('frozen_m120_fixture',source)
reference=importlib.util.module_from_spec(spec);sys.modules[spec.name]=reference;spec.loader.exec_module(reference)
out=root/'deployment/mage_vl4b/optimization_v1/runs/OP01-group-reference-v1/result.json'
if out.exists():raise RuntimeError('Immutable result exists')
cases=[]
for case in reference.load_fixture(fixture):
    expected=reference.build_case(case,len(case.descriptors))['expected']
    raw=np.frombuffer(case.activation,np.uint8).reshape(case.groups,32,80)
    codes=raw[:,:,:64].copy().view(np.int8).transpose(1,0,2)
    scales=raw[:,:,64:66].copy().view('<f2').reshape(case.groups,32).T
    parts=[]
    for descriptor in case.descriptors:
        shards=[]
        for payload in descriptor.shard_records:
            packed=np.frombuffer(payload,np.uint8).reshape(case.groups,17,16)
            decoded=[reference._decode_weights(packed[g,:descriptor.words],case.bits) for g in range(case.groups)]
            weights=np.stack([d[0] for d in decoded]);ws=np.stack([d[1] for d in decoded]).astype('<f2')
            integer=group_reference(codes,scales,weights,ws)
            floating=group_reference(codes,scales,weights,ws,dot_mode='fp32_exact')
            if not np.array_equal(integer.view('u2'),floating.view('u2')):raise RuntimeError('Dot implementation mismatch')
            shards.append(floating)
        # Frozen wire order descriptor/token/shard/pair/low-half/padding/high-half/padding.
        values=np.stack(shards,axis=1).reshape(32,4,4,2).view('<u2')
        wire=np.zeros((32,4,4,4),'<u2');wire[:,:,:,0]=values[:,:,:,0];wire[:,:,:,2]=values[:,:,:,1]
        parts.append(wire.tobytes())
    observed=b''.join(parts)
    if observed!=expected:raise RuntimeError('Frozen output byte mismatch: '+str(case.ordinal))
    cases.append(dict(ordinal=case.ordinal,layer=case.layer,family=case.family,bits=case.bits,
        groups=case.groups,descriptors=len(case.descriptors),output_bytes=len(observed),byte_exact=True))
result=dict(status='PASS',scope='CPU group arithmetic vs frozen M128 software fixture only',
    board_gate_pass=False,full_model_numerical_pass=False,csim_executed=False,
    fixture_sha256=sha256(fixture),frozen_reference_sha256=sha256(source),
    implementation_sha256=sha256(Path(__file__).with_name('m120_group_reference.py')),cases=cases)
write_json(out,result);print(json.dumps(result))
