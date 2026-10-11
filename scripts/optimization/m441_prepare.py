"""Independent W4 long-chain supply experiment; never reopen the M439 gate."""
import difflib
import hashlib
import json
import re
from m351_workflow import ROOT, BASE, atomic, encoded, sha, sync

OUT = ROOT/'tmp/m441_record_pipeline_01'
PROJECT = ROOT/'tmp/m441_hls_project_01'
ENTRY = 'hls/mage_prefill_m89x_runtime/mage_prefill_m89x_runtime.cpp'
TB = 'hls/mage_prefill_m89x_runtime/tb_m128_m120_numerical.cpp'
BUILD = '0x4D343431'


def main():
    assert not OUT.exists() and not PROJECT.exists(), 'Fresh independent experiment required'
    texts = {}
    recovery = {}
    for name in ('CURRENT_STATE.md', 'docsMILESTONES.md', 'DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md', 'deployment/mage_vl4b/BOARD_GATE_RESULT.json'):
        p = ROOT/name
        texts[name] = p.read_text(encoding='utf-8-sig')
        recovery[name] = dict(sha256=sha(p), bytes=p.stat().st_size, lines=len(texts[name].splitlines()))
    board = json.loads(texts['deployment/mage_vl4b/BOARD_GATE_RESULT.json'])
    prerequisites = []
    for key, required in (
        ('latest_m440_long_chain_audit', 'PASS_M440_SAVED_LONG_CHAIN_RELEVANCE_AUDIT_ONLY'),
        ('latest_m439_board_summary', 'CLOSED_M439_FIRST_VERSION_BOARD_BENEFIT_NOT_PROVEN'),
        ('latest_m439_record_load_preparation02', 'PREPARED_M439_RECORD_LOAD_WITH_ORIGINAL_MAC_NEST'),
    ):
        row = board[key]
        p = ROOT/row['result']
        assert sha(p) == row['sha256']
        r = json.loads(p.read_bytes())
        assert r['status'] == required
        assert all(row['sha256'] in texts[n] for n in ('CURRENT_STATE.md', 'docsMILESTONES.md'))
        prerequisites.append(dict(key=key, path=row['result'], sha256=row['sha256'], status=required))
    prior_preparation = json.loads((ROOT/prerequisites[-1]['path']).read_bytes())
    for row in prior_preparation['files']:
        assert sha(ROOT/row['path']) == row['sha256']
    original_path = ROOT/'tmp/m439_record_load_02'/ENTRY
    original = original_path.read_text(encoding='utf-8-sig')
    # The computation body is copied, rather than re-expressed. Only its supply
    # interface changes. The original LOOP_FLATTEN guard remains in place.
    begin = original.index('static void m89x_shard(')
    end = original.index('\nstatic void m89x_merge', begin)
    shard = original[begin:end]
    signature = 'static void m89x_shard(const ap_uint<128> *memory,'
    assert shard.count(signature) == 1
    compute = shard.replace(signature, 'static void m441_compute(hls::stream<ap_uint<128> > &records,')
    compute = compute.replace('// M439: load exactly one current record; no next-record prefetch.',
                              '// M441 consumer: identical MAC order, a record owned until all four pairs finish.')
    load = '''      const unsigned base = group * blocks * words + block * words;
      // Contiguous current-record load; actual burst is judged from RTL.
      for (unsigned i = 0; i < words; ++i) {
#pragma HLS PIPELINE II=1
#pragma HLS LOOP_TRIPCOUNT min=9 max=17
        record[i] = memory[base + i];
      }'''
    take = '''      for (unsigned i = 0; i < words; ++i) {
#pragma HLS PIPELINE II=1
#pragma HLS LOOP_TRIPCOUNT min=9 max=17
        record[i] = records.read();
      }'''
    assert compute.count(load) == 1
    compute = compute.replace(load, take)
    producer = '''static void m441_load_records(const ap_uint<128> *memory,
                                hls::stream<ap_uint<128> > &records,
                                unsigned groups, unsigned rows, unsigned bits) {
#pragma HLS INLINE off
  const unsigned blocks = rows / 8;
  const unsigned words = 1 + 4 * bits;
  for (unsigned block = 0; block < blocks; ++block) {
    for (unsigned group = 0; group < groups; ++group) {
      const unsigned base = group * blocks * words + block * words;
      for (unsigned i = 0; i < words; ++i) {
#pragma HLS LOOP_FLATTEN off
#pragma HLS PIPELINE II=1
#pragma HLS LOOP_TRIPCOUNT min=9 max=17
        records.write(memory[base + i]);
      }
    }
  }
}

'''
    wrapper = '''
static void m89x_shard(const ap_uint<128> *memory,
                       const ap_uint<128> x[M89_MAX_GROUPS][32][4],
                       const ap_uint<16> as[M89_MAX_GROUPS][32],
                       hls::stream<m89s_pair_t> &out, unsigned groups,
                       unsigned rows, unsigned bits) {
#pragma HLS INLINE off
#pragma HLS DATAFLOW
  hls::stream<ap_uint<128> > records("records");
  // 34 queued words = two W4 records. The consumer additionally owns one
  // local 17-word record; AXI inflight responses retain the existing ABI.
#pragma HLS STREAM variable=records depth=34
  m441_load_records(memory, records, groups, rows, bits);
  m441_compute(records, x, as, out, groups, rows, bits);
}
'''
    candidate = original[:begin] + producer + compute + wrapper + original[end:]
    assert candidate.count('return 0x4D343339U;') == 1
    candidate = candidate.replace('return 0x4D343339U;', f'return {BUILD}U;')
    # Everything outside the replaced supply wrapper and Build ID is exact.
    assert candidate[:begin] == original[:begin]
    assert candidate[candidate.index('\nstatic void m89x_merge'):].replace(BUILD+'U', '0x4D343339U') == original[end:]
    arith_start = '      ap_uint<128> tagged = record[0];'
    assert compute[compute.index(arith_start):] == shard[shard.index(arith_start):]
    assert '#pragma HLS LOOP_FLATTEN off' in compute
    contract_path = ROOT/'deployment/mage_vl4b/m175_m120_fixed_text_candidate/contracts/M126_LANGUAGE_RUNTIME_CONTRACT_RESULT.json'
    contract = json.loads(contract_path.read_bytes())
    audit = json.loads((ROOT/prerequisites[0]['path']).read_bytes())
    assert any(r['path'] == contract_path.relative_to(ROOT).as_posix() and r['sha256'] == sha(contract_path) for r in audit['evidence'])
    cases = []
    for family, bits, layer in (('gate_up',4,0), ('mlp_down',4,0), ('q',2,0)):
        chain = next(c for c in contract['chains'] if c['layer']==layer and c['family']==family)
        assert chain['bits'] == bits
        cases.append(dict(name=f'layer{layer}_{family}_W{bits}', role='primary' if bits==4 else 'W2_control', chain=chain,
                          real_weight_identity_required=True, full_descriptor_rows_required=True,
                          input='Deterministic nonzero T32 from frozen activation(groups); not a model-quality input'))
    plan = dict(schema='m441-independent-long-chain-v1', build_id=BUILD, baseline_build_id='0x4D333537',
        prior_M439_closed=True, prior_M439_results_mutable=False, arithmetic_changed=False,
        change='Per-shard bounded FIFO decouples contiguous record loading from unchanged MAC consumer; loading may overlap current-record compute.',
        FIFO_words_per_shard=34, FIFO_word_bits=128, consumer_local_words_per_shard=17,
        logical_added_queue_bytes_all_shards=2176, extra_PS_slots=0, extra_CMA_banks=0,
        physical_storage_and_overlap='Must be established by actual synthesis and RTL, not the source DATAFLOW directive.',
        original_chain_contract_sha256=sha(contract_path), cases=cases,
        gates=['Seven original reduced real-record numeric CSim and recursive headers',
               'Real complete-size gate_up/down/Q CSim output, sidebands, word count and return',
               'Same-constraint synthesis: original MAC II/order/DSP, FIFO mapping, burst',
               'Bounded RTL supply-overlap observation and full transaction cycles under Zero/Random delay',
               'Maximum descriptor/FIFO/output backpressure and independent timeout failure',
               'Same-constraint routed core then full-shell implementation',
               'COM3 Build-ID, descriptor, primary full chains, predetermined A/B comparison'],
        RTL_budget_cycles_per_full_chain=30000000, RTL_delay_models=['zero_extra_latency','seed356_random'],
        RTL_required=['complete output/keep/strb/TLAST/done/return', 'unchanged accepted MAC work',
                      'ARLEN and exact R/address coverage', 'read beats during MAC accepted activity',
                      'queue occupancy/backpressure/drain', 'complete transaction and shard cycles'],
        RTL_stop='Any incorrect output/protocol, missing real supply overlap, resource overflow, zero-delay full-chain regression, or no random-delay improvement stops this variant at that level.',
        board_protocol=dict(order='ABBABAAB', primers_per_shape_per_block=1, formal_per_shape_per_block=8,
                            samples_retained='all fixed formal samples, no deletion or additional samples',
                            timing='before S2MM submit through latched ap_done and both DMA idle; stage/sync/hash outside',
                            primary_pass='Both full W4 shapes improve pooled median and both balanced orders; every B block median below every A block median. No differing clock/config/input/output.',
                            W2_control='Correctness and all timings reported; no W2 gain required, no whole-model admission without assessing W2 regression.',
                            stop='Any primary failure closes the long-chain hypothesis; no full model, no additional samples. Unsafe DMA failure retains owner/process/buffers.'),
        later='Only after primary real-board benefit: original layer/text/fixed159 video numerical gates, then independent whole-request natural-I/O comparison against M437.',
        unchanged=['input','quantization/FTZ/MAC order','merge depth8192','AXI/control ABI','language runtime','visual layers13..23','parser worker1','PS prefetch disabled','stable service/rollback/boot/DTB/CMA'],
        fixed64MiB_admission=False, temperature_read=False, board_now=False, full_model_now=False)
    source_root = ROOT/'tmp/m439_record_load_02'
    inputs = {}; pending=[source_root/ENTRY, source_root/TB]
    while pending:
        p = pending.pop(0).resolve()
        if p in inputs: continue
        p.relative_to(source_root)
        inputs[p] = dict(path=p.relative_to(ROOT).as_posix(), sha256=sha(p))
        raw = p.read_bytes()
        for inc in re.findall(r'^\s*#\s*include\s*"([^"]+)"', raw.decode('utf-8-sig'), re.M): pending.append((p.parent/inc).resolve())
    for p in inputs: atomic(OUT/p.relative_to(source_root),p.read_bytes(),immutable=True)
    atomic(OUT/ENTRY,candidate.encode('utf-8'))
    tb=(source_root/TB).read_text(encoding='utf-8-sig')
    assert tb.count('0x4D343339U')==1
    atomic(OUT/TB,tb.replace('0x4D343339U',BUILD+'U').encode('utf-8'))
    missing=[]
    for p in OUT.rglob('*'):
        if p.suffix in ('.cpp','.hpp','.h'):
            for inc in re.findall(r'^\s*#\s*include\s*"([^"]+)"',p.read_text(encoding='utf-8-sig'),re.M):
                if not (p.parent/inc).resolve().is_file(): missing.append(str(p)+':'+inc)
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
    atomic(OUT/'run_m441_hls.tcl',tcl.encode('utf-8'),immutable=True)
    atomic(OUT/'SOURCE.diff',''.join(difflib.unified_diff(original.splitlines(True),candidate.splitlines(True),fromfile='closed-M439.cpp',tofile='independent-M441.cpp')).encode('utf-8'),immutable=True)
    atomic(OUT/'PLAN.json',encoded(plan),immutable=True)
    report='''# M441 独立长链供给实验协议

M439已关闭；不追加旧版样本或改变原FAIL。M440核对发现旧诊断中W4 gate_up/down占设备等待69.56%，因此新实验优先使用完整真实尺寸W4，Q仅作W2对照。

唯一新变化：每shard把连续读取与原MAC拆成两个DATAFLOW过程，用34个128位字的有界FIFO交接。W4队列最多容纳两条完整记录，consumer另持有一条17字记录；原AXI在途响应容量保持。队列逻辑容量四shard共2176B，实际资源与重叠必须由综合/RTL证明。没有PS预读槽或新增CMA bank。

原MAC顺序、FP32累加、FTZ边界、输出合并及8192深度不改。既有七组真实记录CSim只是第一数值门，完整gate_up G40/D10、down G152/D2和Q G40/D2另行核对完整行数/权重/输出，不能用每shard8行或全零最大协议替代。

Zero/seed356 Random两个RTL模型固定周期预算，统计真实读/算重叠、AR/R字数与地址、队列背压、原MAC工作、输出合并和完整事务周期。没有重叠、零附加延迟回退、随机延迟无收益、资源或时序不通过即停本级，不进入整壳或板端。

板端仅在所有前级成立后按Build→descriptor→chain推进。两项W4 primary采用固定ABBA＋BAAB，每block每shape一primer、八正式事务，保留全部样本；两项均须满足中位数及两个顺序收益、B/A block中位数完全分离，时钟和输入/输出合同相同。失败关闭新假设，不追加样本。Q对照需正确、完整报告回退，不将W2影响隐藏。

只有实板长W4收益成立，才重新过单层、固定文本、固定视频数值及相同M437完整请求性能。源码完成或CSim不等于RTL、板端或加速。精确案例、预算和判据见PLAN.json。本次不访问COM3、不改变服务、rollback、boot/DTB/CMA，也不恢复固定64MiB检查或测温。
'''
    atomic(OUT/'PLAN.md',report.encode('utf-8'),immutable=True)
    result=dict(status='PREPARED_M441_INDEPENDENT_BOUNDED_RECORD_PIPELINE',build_id=BUILD,baseline_build_id='0x4D333537',
        prerequisites=prerequisites,recovery_read=recovery,source_sha256=sha(OUT/ENTRY),prior_source_sha256=sha(original_path),
        arithmetic_body_sha256=hashlib.sha256(compute[compute.index(arith_start):].encode('utf-8')).hexdigest(),
        arithmetic_unchanged=True,outer_ABI_merge_unchanged=True,recursive_inputs=list(inputs.values()),missing_headers=missing,
        original_fixture_sha256=sha(fixture),plan=plan,
        files=[dict(path=p.relative_to(ROOT).as_posix(),bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(OUT.rglob('*')) if p.is_file()],
        csim=False,full_size_numerical=False,rtl=False,resources=False,implementation_timing=False,board=False,performance=False,promoted=False)
    ev=BASE/'runs/M441-record-pipeline-preparation-01/RESULT.json'
    atomic(ev,encoded(result),immutable=True)
    sync('latest_m441_record_pipeline_preparation',dict(status=result['status'],result=ev.relative_to(ROOT).as_posix(),sha256=sha(ev),build_id=BUILD,board=False),
         f'## M441 独立长W4供给实验准备（2026-10-07）\n\nSHA {sha(ev)}；Build {BUILD}，原M439关闭不追加样本，新34字/shard队列分离连续读与原MAC，原数学/输出/ABI不改，0PS槽/额外CMAbank。完整gate_up/down为primary、Q为对照，固定RTL与ABBA＋BAAB判据见tmp/m441_record_pipeline_01/PLAN。header missing=0；尚未CSim/RTL/综合/板端或新提速，下一步原七组数值及实际调度/资源，完整尺寸数值必须在后续RTL前闭合。')
    print(result['status'],sha(ev),len(inputs),BUILD)


if __name__=='__main__': main()
