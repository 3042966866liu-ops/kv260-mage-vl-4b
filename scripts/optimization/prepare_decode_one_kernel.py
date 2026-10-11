"""Generate isolated mechanical fork; never patch the stable T32 source."""
from pathlib import Path
from measurement import sha256,write_json
root=Path(__file__).resolve().parents[2]
src=root/'hls/mage_prefill_m89x_runtime'
out=root/'hls/mage_decode_op01_one'
if out.exists():raise RuntimeError('Candidate directory already exists')
kernel=(src/'mage_prefill_m89x_runtime.cpp').read_text()
if sha256(src/'mage_prefill_m89x_runtime.cpp')!='94e85e0cdd7ccd4758ee02407b46b728a045b288befb3b29bf4615ecfee24f2d':
    raise RuntimeError('Stable source identity changed')
def replace(text,old,new,count=1):
    if text.count(old)!=count:raise RuntimeError('Unexpected source shape: '+old)
    return text.replace(old,new)
kernel=replace(kernel,'#include "mage_prefill_m89x_runtime.hpp"','#include "decode_one.hpp"')
kernel=replace(kernel,'unsigned rows, unsigned bits) {','unsigned rows, unsigned bits, bool decode_one) {')
kernel=replace(kernel,'token_pair < 16','token_pair < (decode_one ? 1U : 16U)')
for i in (0,1):
    kernel=replace(kernel,f'm89s_half_bits((half)acc{i}[token][pair])',
        f'(decode_one && token != 0) ? ap_uint<16>(0) : m89s_half_bits((half)acc{i}[token][pair])')
kernel=replace(kernel,'unsigned rows, unsigned bits, bool final_descriptor) {',
    'unsigned rows, unsigned bits, bool final_descriptor, bool decode_one) {')
kernel=replace(kernel,'groups, rows, bits);','groups, rows, bits, decode_one);',4)
kernel=replace(kernel,'i + 1 == descriptor_count);','i + 1 == descriptor_count, config[24]);')
kernel=replace(kernel,'m89x_runtime_kernel(','op01_decode_one_kernel(')
kernel=replace(kernel,'return 0x4D395832U;','return 0x4F503131U;')
header=(src/'mage_prefill_m89x_runtime.hpp').read_text().replace('m89x_runtime_kernel(','op01_decode_one_kernel(')
tb=(src/'tb_m128_m120_numerical.cpp').read_text()
tb=replace(tb,'#include "mage_prefill_m89x_runtime.hpp"','#include "decode_one.hpp"')
tb=replace(tb,'int main() {','static int run_mode(bool decode_one) {')
tb=replace(tb,'m89x_runtime_kernel(','op01_decode_one_kernel(')
tb=replace(tb,'0x4D395832U','0x4F503131U')
tb=replace(tb,'ap_uint<32> status =','config[24] = decode_one;\n    ap_uint<32> status =')
tb=replace(tb,'if (item.data.range(15, 0) != expected0 ||',
    'if (decode_one && token != 0) { expected0 = 0; expected1 = 0; }\n            if (item.data.range(15, 0) != expected0 ||')
tb+='\nint main() {\n  int rc=run_mode(false); if(rc) return rc;\n  rc=run_mode(true); if(rc) return rc;\n  std::cout << "OP01_T32_AND_DECODE_ONE_NUMERICAL_PASS\\n";\n  return 0;\n}\n'
out.mkdir()
for name,text in [('decode_one.cpp',kernel),('decode_one.hpp',header),('tb_decode_one.cpp',tb)]:
    (out/name).write_text(text,encoding='utf-8',newline='\n')
write_json(out/'SOURCE_MANIFEST.json',dict(status='CANDIDATE_UNTESTED',build_id='0x4F503131',
    config='bit24=1: only token0 valid; bit24=0: legacy T32; full T32 wire format always',
    parent_sha256=sha256(src/'mage_prefill_m89x_runtime.cpp'),
    files=[dict(path=p.name,sha256=sha256(p)) for p in sorted(out.iterdir())],
    arithmetic='One token-pair executed for decode_one; lane1 arithmetic discarded; no speedup proven'))
print('DECODE_ONE_CANDIDATE_GENERATED')
