"""One isolated supply-organization candidate, strict recursive source closure."""
import json
import re
import sys
from pathlib import Path
import m351_workflow as w
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'deployment/mage_vl4b/optimization_v1'
OUT=ROOT/'tmp/m357_activation_banks'
BUILD='0x4D333537'
INCLUDES=re.compile(r'^\s*#\s*include\s*"([^"]+)"',re.M)

def main():
    if OUT.exists():raise RuntimeError('Existing candidate; do not regenerate')
    entry='hls/mage_prefill_m89x_runtime/mage_prefill_m89x_runtime.cpp'
    tb='hls/mage_prefill_m89x_runtime/tb_m128_m120_numerical.cpp'
    queue=[ROOT/entry,ROOT/tb];seen={}
    while queue:
        p=queue.pop(0).resolve()
        if p in seen:continue
        rel=p.relative_to(ROOT);raw=p.read_bytes();text=raw.decode('utf-8-sig')
        seen[p]=dict(path=rel.as_posix(),sha256=w.sha(p))
        dest=OUT/rel;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
        for inc in INCLUDES.findall(text):queue.append((p.parent/inc).resolve())
    p=OUT/entry;original=p.read_text(encoding='utf-8-sig')
    start=original.index('static void m89x_four(');end=original.index('\nap_uint<32> m89x_runtime_kernel',start)
    replacement='''static void m89x_four(const ap_uint<128> *s0, const ap_uint<128> *s1,
                      const ap_uint<128> *s2, const ap_uint<128> *s3,
                      const ap_uint<128> x[4][M89_MAX_GROUPS][32][4],
                      const ap_uint<16> as[4][M89_MAX_GROUPS][32],
                      hls::stream<m89_axis64_t> &rx, unsigned groups,
                      unsigned rows, unsigned bits, bool final_descriptor) {
#pragma HLS INLINE off
#pragma HLS DATAFLOW
#pragma HLS ARRAY_PARTITION variable=x complete dim=1
#pragma HLS ARRAY_PARTITION variable=as complete dim=1
  hls::stream<m89s_pair_t> result[4];
#pragma HLS ARRAY_PARTITION variable=result complete
  // Preserve the original maximum legal FIFO depth and merge contract.
#pragma HLS STREAM variable=result depth=8192
  m89x_shard(s0, x[0], as[0], result[0], groups, rows, bits);
  m89x_shard(s1, x[1], as[1], result[1], groups, rows, bits);
  m89x_shard(s2, x[2], as[2], result[2], groups, rows, bits);
  m89x_shard(s3, x[3], as[3], result[3], groups, rows, bits);
  m89x_merge(result, rx, rows, final_descriptor);
}
'''
    text=original[:start]+replacement+original[end:]
    text=text.replace('ap_uint<128> activation[M89_MAX_GROUPS][M89_TOKEN_LANES][4];','ap_uint<128> activation[4][M89_MAX_GROUPS][M89_TOKEN_LANES][4];')
    text=text.replace('ap_uint<16> activation_scale[M89_MAX_GROUPS][M89_TOKEN_LANES];','ap_uint<16> activation_scale[4][M89_MAX_GROUPS][M89_TOKEN_LANES];')
    text=text.replace('#pragma HLS BIND_STORAGE variable=activation type=', '#pragma HLS ARRAY_PARTITION variable=activation complete dim=1\n#pragma HLS BIND_STORAGE variable=activation type=')
    text=text.replace('#pragma HLS BIND_STORAGE variable=activation_scale type=', '#pragma HLS ARRAY_PARTITION variable=activation_scale complete dim=1\n#pragma HLS BIND_STORAGE variable=activation_scale type=')
    text=text.replace('m89s_load(tx, activation, activation_scale, groups, status);','m89s_load(tx, activation[0], activation_scale[0], groups, status);')
    anchor='  for (unsigned i = 0; i < descriptor_count; ++i) {\n#pragma HLS LOOP_TRIPCOUNT'
    assert text.count(anchor)==1
    copy='''  // Only supply organization changes: broadcast the already validated input
  // into independent read-only banks before descriptor execution.
  for (unsigned g = 0; g < groups; ++g) {
    for (unsigned t = 0; t < M89_TOKEN_LANES; ++t) {
      for (unsigned k = 0; k < 4; ++k) {
#pragma HLS PIPELINE II=1
        ap_uint<128> value = activation[0][g][t][k];
        for (unsigned s = 1; s < 4; ++s) {
#pragma HLS UNROLL
          activation[s][g][t][k] = value;
          if (k == 0) activation_scale[s][g][t] = activation_scale[0][g][t];
        }
      }
    }
  }

'''
    text=text.replace(anchor,copy+anchor).replace('return 0x4D395832U;','return '+BUILD+'U;')
    # Prove every arithmetic/helper function preceding m89x_four is unchanged.
    assert original[:start]==text[:start]
    p.write_text(text,encoding='utf-8')
    test=OUT/tb;test.write_text(test.read_text(encoding='utf-8-sig').replace('0x4D395832U',BUILD+'U'),encoding='utf-8')
    fixture=ROOT/'deployment/mage_vl4b/artifacts/m128_m120_real_record_csim_fixture.bin'
    assert w.sha(fixture)=='f384f45eea4bc14110a7add49dd0944f0a025403aecc3360369ec999e28257d9'
    run=OUT/'run_m357_csim_synth.tcl'
    run.write_text('''set root {'''+OUT.as_posix()+'''}
set project {'''+(ROOT/'tmp/m357_hls_project').as_posix()+'''}
if {[file exists $project]} {error "Existing project: inspect only"}
set ::env(M128_FIXTURE_PATH) {'''+fixture.as_posix()+'''}
cd $root
open_project $project
set_top m89x_runtime_kernel
add_files [file join $root '''+entry+''']
add_files -tb [file join $root '''+tb+'''] -cflags "-I[file join $root hls mage_prefill_m89x_runtime]"
open_solution hls -flow_target vivado
set_part {xck26-sfvc784-2LV-c}
create_clock -period 4.8 -name default
set_clock_uncertainty 1.3
config_compile -pipeline_loops 0
csim_design -clean
csynth_design
exit
''',encoding='utf-8')
    missing=[]
    for dest in OUT.rglob('*'):
        if dest.suffix not in ('.cpp','.hpp','.h'):continue
        for inc in INCLUDES.findall(dest.read_text(encoding='utf-8-sig')):
            if not (dest.parent/inc).resolve().is_file():missing.append(str(dest)+':'+inc)
    assert not missing
    result=dict(status='PREPARED_ISOLATED_ACTIVATION_BANK_CANDIDATE',build_id=BUILD,stable_build_id='0x4D395832',
        change='One supply organization: four private read-only activation/scale banks, broadcast after original loader',
        preserved=['All arithmetic/helper functions byte-for-byte','weight AXI ports','descriptor format/order','T32','FIFO depth 8192','output merge order'],
        candidate_sha256=w.sha(p),source_closure=list(seen.values()),missing=missing,fixture_sha256=w.sha(fixture),
        csim=False,rtl=False,resources=False,timing=False,board=False,promoted=False,
        constraints='Actual independent shard start must be shown in RTL; 64 URAM estimate is a risk, not a verified fit')
    ev=BASE/'runs/M357-activation-bank-preparation-01/RESULT.json';w.atomic(ev,w.encoded(result),immutable=True);sha=w.sha(ev)
    w.sync('M357_activation_bank_preparation',dict(status=result['status'],sha256=sha,evidence_path=ev.relative_to(ROOT).as_posix(),build_id=BUILD),
        'M357 隔离候选 '+BUILD+' 仅复制原始激活/scale 为四 shard 独立只读 bank。算术函数完全不变，FIFO8192/输出顺序不变；递归 header missing=0。未 CSim/RTL/资源/时序/上板，估计 URAM64 为待验证风险。下一步新数值 CSim 与 HLS 调度/资源。证据 '+sha)
    print(json.dumps(dict(status=result['status'],sha256=sha,closure_count=len(seen),build_id=BUILD),ensure_ascii=True))

if __name__=='__main__':main()
