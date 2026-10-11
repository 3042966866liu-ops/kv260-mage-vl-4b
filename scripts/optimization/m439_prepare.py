"""One isolated record-load candidate from hash-locked M357, no prefetch."""
import json,re,difflib
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync

OUT=ROOT/'tmp/m439_record_load_01'
PROJECT=ROOT/'tmp/m439_hls_project_01'
SOURCE=ROOT/'tmp/m357_activation_banks'
BUILD='0x4D343339'
ENTRY='hls/mage_prefill_m89x_runtime/mage_prefill_m89x_runtime.cpp'
TB='hls/mage_prefill_m89x_runtime/tb_m128_m120_numerical.cpp'

def main():
    assert not OUT.exists() and not PROJECT.exists(),'Fresh isolated attempt required'
    recovery={}
    for name in ('CURRENT_STATE.md','DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'):
        p=ROOT/name;s=p.read_text(encoding='utf-8-sig')
        recovery[name]=dict(bytes=p.stat().st_size,lines=len(s.splitlines()),sha256=sha(p))
    board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    prior=board['latest_m438_weight_wait_closure']
    assert prior['sha256']=='7d410eab1d107aaa1cfe33ad7c1200e9be6a7ba5953b0241d92d78c9998c7830'
    assert sha(ROOT/prior['result'])==prior['sha256']
    assert all(prior['sha256'] in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    m357=BASE/'runs/M357-activation-bank-preparation-01/RESULT.json'
    old=json.loads(m357.read_bytes())
    assert sha(SOURCE/ENTRY)==old['candidate_sha256']
    orig=(SOURCE/ENTRY).read_text(encoding='utf-8-sig')
    assert orig.count('return 0x4D333537U;')==1
    before='  float acc0[32][4], acc1[32][4];'
    after='''  // M439: load exactly one current record; no next-record prefetch.
  ap_uint<128> record[17];
#pragma HLS BIND_STORAGE variable=record type=ram_2p impl=lutram
  float acc0[32][4], acc1[32][4];'''
    read='      ap_uint<128> tagged = memory[base];'
    load='''      // Contiguous current-record load; actual burst is judged from RTL.
      for (unsigned i = 0; i < words; ++i) {
#pragma HLS PIPELINE II=1
#pragma HLS LOOP_TRIPCOUNT min=9 max=17
        record[i] = memory[base + i];
      }
      ap_uint<128> tagged = record[0];'''
    dec='m89x_decode_pair(memory + base, pair, bits, tagged0, tagged1,'
    local='m89x_decode_pair(record, pair, bits, tagged0, tagged1,'
    replacements=[(before,after),(read,load),(dec,local),('return 0x4D333537U;',f'return {BUILD}U;')]
    text=orig
    for a,b in replacements:
        assert text.count(a)==1,a
        text=text.replace(a,b)
    reverse=text
    for a,b in reversed(replacements):reverse=reverse.replace(b,a)
    assert reverse==orig,'Unintended source change'
    # Assert the complete arithmetic body and original unpacking helper remain exact.
    def region(s,a,b):return s[s.index(a):s.index(b,s.index(a))]
    arithmetic=region(orig,'        float scale0 =','\nstatic void m89x_merge')
    assert region(text,'        float scale0 =','\nstatic void m89x_merge')==arithmetic
    assert region(text,'static void m89x_decode_pair','\nstatic void m89x_shard')==region(orig,'static void m89x_decode_pair','\nstatic void m89x_shard')
    inputs={};queue=[SOURCE/ENTRY,SOURCE/TB]
    while queue:
        p=queue.pop(0).resolve()
        if p in inputs:continue
        rel=p.relative_to(SOURCE);raw=p.read_bytes();inputs[p]=dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p))
        for inc in re.findall(r'^\s*#\s*include\s*"([^"]+)"',raw.decode('utf-8-sig'),re.M):queue.append((p.parent/inc).resolve())
    for p in inputs:
        atomic(OUT/p.relative_to(SOURCE),p.read_bytes(),immutable=True)
    atomic(OUT/ENTRY,text.encode('utf-8'))
    tb=(SOURCE/TB).read_text(encoding='utf-8-sig');assert tb.count('0x4D333537U')==1
    atomic(OUT/TB,tb.replace('0x4D333537U',BUILD+'U').encode('utf-8'))
    missing=[]
    for p in OUT.rglob('*'):
        if p.suffix in ('.cpp','.hpp','.h'):
            for inc in re.findall(r'^\s*#\s*include\s*"([^"]+)"',p.read_text(encoding='utf-8-sig'),re.M):
                if not (p.parent/inc).resolve().is_file():missing.append(str(p)+':'+inc)
    assert not missing
    fixture=ROOT/'deployment/mage_vl4b/artifacts/m128_m120_real_record_csim_fixture.bin'
    assert sha(fixture)=='f384f45eea4bc14110a7add49dd0944f0a025403aecc3360369ec999e28257d9'
    tcl=f'''set root {{{OUT.as_posix()}}}
set project {{{PROJECT.as_posix()}}}
if {{[file exists $project]}} {{error "Existing project: collect only"}}
set ::env(M128_FIXTURE_PATH) {{{fixture.as_posix()}}}
cd [file dirname $root]
open_project $project
set_top m89x_runtime_kernel
add_files [file join $root {ENTRY}]
add_files -tb [file join $root {TB}] -cflags "-I[file join $root hls mage_prefill_m89x_runtime]"
open_solution hls -flow_target vivado
set_part {{xck26-sfvc784-2LV-c}}
create_clock -period 4.8 -name default
set_clock_uncertainty 1.3
config_compile -pipeline_loops 0
csim_design -clean
csynth_design
exit
'''
    atomic(OUT/'run_m439_hls.tcl',tcl.encode('utf-8'),immutable=True)
    atomic(OUT/'SOURCE.diff',''.join(difflib.unified_diff(orig.splitlines(True),text.splitlines(True),fromfile='M357.cpp',tofile='M439.cpp')).encode('utf-8'),immutable=True)
    plan=dict(scope='Single current-record contiguous load per shard; no read/compute overlap or next-record prefetch',
      comparison_baseline='M357 0x4D333537; later whole-request baseline M437 selected visual MLP13..23',
      record_words=dict(W2=9,W4=17),record_bytes_per_shard=dict(W2=144,W4=272),physical_buffer='17x128 bits per shard dual-port LUTRAM; actual resource cost judged after synthesis',
      extra_PS_slots=0,extra_CMA_banks=0,arithmetic_changed=False,
      initial_gates=['Original seven real-record numerical CSim cases including W2/W4','Recursive local header closure','Synthesis actual burst inference and resources','M438 W2 first-block Random/Zero RTL with unchanged input/reference','One W4 representative with original-vs-candidate same input and delay model'],
      measurements=['AR requests and ARLEN histogram with R beat count/RLAST/address range','parent shard active and full transaction cycles','MAC calls and accepted iterations with exact accumulation order','full data/keep/strb/TLAST/done/Build and UVM-visible errors','same part/clock/uncertainty resource and timing reports'],
      stop_rule='No full-model expansion if requests do not decrease, zero-delay transaction regresses, delay-model transaction does not improve, resources exceed device, or implementation timing fails. HLS estimate is not implementation frequency.',
      later_only='Numerical CSim and maximum FIFO/descriptor RTL/backpressure/timeout closure required before full-shell implementation. Same-constraint implementation and real-board single-chain benefit before fixed-layer/text/video; no board performance inferred from VIP cycles.',
      post_record_pipeline=False,temperature_read=False,production_promotion=False)
    atomic(OUT/'PLAN.json',encoded(plan),immutable=True)
    result=dict(status='PREPARED_M439_SINGLE_RECORD_LOAD_CANDIDATE',build_id=BUILD,baseline_build_id='0x4D333537',source_recovery=recovery,
      baseline_source_sha256=sha(SOURCE/ENTRY),baseline_preparation_sha256=sha(m357),prior_m438_sha256=prior['sha256'],
      recursive_inputs=list(inputs.values()),missing_headers=missing,exact_arithmetic_body_sha256=__import__('hashlib').sha256(arithmetic.encode('utf-8')).hexdigest(),
      reverse_change_exact=True,fixture_sha256=sha(fixture),plan=plan,
      files=[dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p)) for p in sorted(OUT.rglob('*')) if p.is_file()],
      csim=False,rtl=False,board=False,resources=False,implementation_timing=False,performance=False,promoted=False)
    ev=BASE/'runs/M439-record-load-preparation-01/RESULT.json';atomic(ev,encoded(result),immutable=True)
    sync('latest_m439_record_load_preparation',dict(status=result['status'],result=ev.relative_to(ROOT).as_posix(),sha256=sha(ev),build_id=BUILD,board=False),
      f'## M439 单条权重连续加载候选准备（2026-10-07）\n\nBuild {BUILD} 从实际M357同SHA源隔离复制；仅当前记录9/17字连续载入17x128bit片内小缓冲、原解包与MAC/FP32累加顺序不改，无下一条预取/新PS槽/CMA。逆变换原源码精确、header missing=0；原M437完整请求基线保留。SHA {sha(ev)}。未CSim/RTL/资源/实现时序/上板/提速；下一步原七组真实权重CSim及同约束综合，实际burst后再窄W2/W4，按PLAN停止条件裁决，不直接扩全模型。')
    print('M439_PREPARED',sha(ev),len(inputs),BUILD)

if __name__=='__main__':main()
