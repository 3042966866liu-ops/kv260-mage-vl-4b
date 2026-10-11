"""Clone a completed HLS project to reuse unchanged synthesis for new TB only."""
import json,shutil
from pathlib import Path
from measurement import sha256,write_json
root=Path(__file__).resolve().parents[2];base=root/'deployment/mage_vl4b/optimization_v1'
prior=json.loads((base/'gates/G02-decode-one-rtl/attempt_01/result.json').read_text())
kernel=root/'hls/mage_decode_op01_one/decode_one.cpp'
assert sha256(kernel)==prior['evidence'][str(kernel.relative_to(root))]
src=root/'tmp/op01_decode_one_rtl';dest=root/'tmp/op01_decode_one_shapes'
if dest.exists():raise RuntimeError('Immutable clone exists')
shutil.copytree(src,dest)
app=dest/'hls.app';text=app.read_text()
assert text.count('name="op01_decode_one_rtl"')==1
app.write_text(text.replace('name="op01_decode_one_rtl"','name="op01_decode_one_shapes"'))
write_json(dest/'REUSED_SYNTHESIS.json',dict(status='PREPARED_ONLY',kernel_sha256=sha256(kernel),
    original_cosim_sha256=sha256(src/'hls/sim/report/op01_decode_one_kernel_cosim.rpt'),
    original_synthesis_sha256=sha256(src/'hls/syn/report/op01_decode_one_kernel_csynth.rpt'),
    purpose='New testbench only; numerical kernel and synthesis unchanged. Clone keeps old artifacts intact.'))
print('OP01_SHAPES_CLONE_READY')
