"""Static generated RTL ABI/FIFO audit, not a dynamic CoSim result."""
import re
from pathlib import Path
from measurement import sha256,write_json
root=Path(__file__).resolve().parents[2];v=root/'tmp/op01_decode_one_rtl/hls/syn/verilog'
ctrl=v/'op01_decode_one_kernel_control_s_axi.v'
fifo=v/'op01_decode_one_kernel_fifo_w32_d8192_A.v'
four=v/'op01_decode_one_kernel_m89x_four.v'
expected={'ADDR_AP_CTRL':0,'ADDR_AP_RETURN_0':16,'ADDR_S0_DATA_0':24,'ADDR_S1_DATA_0':36,'ADDR_S2_DATA_0':48,'ADDR_S3_DATA_0':60,'ADDR_CONFIG_R_DATA_0':128}
text=ctrl.read_text();assert re.search(r'C_S_AXI_ADDR_WIDTH\s*=\s*8\b',text)
actual={}
for name,value in expected.items():
    match=re.search(r'\b'+name+r'\s*=\s*8\x27h([0-9a-fA-F]+)',text)
    assert match and int(match[1],16)==value,name
    actual[name]=value
assert re.search(r'DEPTH\s*=\s*8192\b',fifo.read_text())
assert len(re.findall(r'\bop01_decode_one_kernel_fifo_w32_d8192_A\s+result(?:_[123])?_U\(',four.read_text()))==4
out=root/'deployment/mage_vl4b/optimization_v1/runs/OP01-decode-one-rtl-abi/result.json'
if out.exists():raise RuntimeError('Immutable audit exists')
write_json(out,dict(status='PASS_STATIC_GENERATED_RTL_ABI_ONLY',build_id='0x4F503131',addresses=actual,
    address_width=8,result_fifo_instances=4,result_fifo_depth_each=8192,
    limitations=['Not measured occupancy or AXI forward progress','Does not establish routed timing or board correctness'],
    sources={str(p.relative_to(root)):sha256(p) for p in [ctrl,fifo,four]}))
print('OP01_GENERATED_RTL_ABI_STATIC_PASS')
