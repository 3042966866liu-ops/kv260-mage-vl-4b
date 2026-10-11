"""Static execution-contract audit, not PL-cycle measurement or speedup proof."""
import json
from pathlib import Path
from measurement import sha256,write_json
root=Path(__file__).resolve().parents[2];base=root/'deployment/mage_vl4b/optimization_v1'
kernel=root/'hls/mage_prefill_m89x_runtime/mage_prefill_m89x_runtime.cpp'
host=root/'deployment/mage_vl4b/m175_m120_fixed_text_candidate/runtime/contract_runtime.py'
wait=root/'deployment/mage_vl4b/m175_m120_fixed_text_candidate/runtime/board_runtime.py'
text=kernel.read_text()
for pattern in ('token_pair < 16','token < 32','token == 31','config.range(7, 0)','config.range(10, 8)','config.range(19, 16)'):
    assert pattern in text,pattern
contracts=root/'deployment/mage_vl4b/m175_m120_fixed_text_candidate/contracts'
chains=[];sources=[kernel,host,wait]
for name in ('M126_LANGUAGE_RUNTIME_CONTRACT_RESULT.json','M126_LMHEAD_RUNTIME_CONTRACT_RESULT.json'):
    path=contracts/name;sources.append(path);chains.extend(json.loads(path.read_text())['chains'])
assert len(chains)==162
result=dict(status='STATIC_CONTRACT_AUDIT',actual_decode_tokens=1,wire_tokens=32,
    arithmetic_token_pairs=16,logical_calls=len(chains),
    input_bytes=sum(c['input_bytes'] for c in chains),output_bytes=sum(c['output_bytes'] for c in chains),
    contract_expected_macros=sum(c['expected_macros'] for c in chains),
    configurable_fields=['groups','weight_bits','descriptor_count'],active_token_field=False,
    padding_token_fraction=31/32,
    caveats=['31/32 padded token positions is not 31/32 measured time or power.',
        'wait_transaction observes AP_DONE plus both DMA idle, not pure compute cycles.',
        '100us sleep repeats while busy, not a fixed 22.6s delay; poll counts not yet measured.',
        'Source/export lineage uses M132->M134; unchanged source hash alone is not proof of bitstream equivalence.',
        'New T1 packet/kernel requires independent numeric, closure, CoSim and implementation gates.'],
    sources={str(p.relative_to(root)):sha256(p) for p in sources},performance_pass=False)
out=base/'runs/OP01-t1-t32-static-audit/result.json'
if out.exists():raise RuntimeError('Immutable audit exists')
write_json(out,result);print(json.dumps(result))
