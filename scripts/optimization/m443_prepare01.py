"""Independent intra-record pair pipeline; preserve every M441 artifact."""
import ast
import difflib
import json
import re
from pathlib import Path
from m441_host_io08 import atomic
from m351_workflow import ROOT, BASE, encoded, sha, sync

OUT = ROOT / 'tmp/m443_pair_pipeline_01'
PROJECT = ROOT / 'tmp/m443_hls_project_01'
ENTRY = Path('hls/mage_prefill_m89x_runtime/mage_prefill_m89x_runtime.cpp')
TB = Path('hls/mage_prefill_m89x_runtime/tb_m128_m120_numerical.cpp')


def main():
    if OUT.exists() or PROJECT.exists():
        raise RuntimeError('Existing independent attempt: collect saved bytes only')
    recovery = {}
    texts = {}
    for name in ('CURRENT_STATE.md', 'docsMILESTONES.md', 'DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md', 'deployment/mage_vl4b/BOARD_GATE_RESULT.json', 'AGENTS.md'):
        p = ROOT / name
        texts[name] = p.read_text(encoding='utf-8-sig')
        recovery[name] = dict(sha256=sha(p), bytes=p.stat().st_size, lines=len(texts[name].splitlines()))
    board = json.loads(texts['deployment/mage_vl4b/BOARD_GATE_RESULT.json'])
    prior = board['latest_m441_W2_W4_simulation_closure23']
    assert sha(ROOT / prior['result']) == prior['sha256']
    assert all(prior['sha256'] in texts[n] for n in ('CURRENT_STATE.md', 'docsMILESTONES.md'))
    source_root = ROOT / 'tmp/m441_record_pipeline_02'
    original = (source_root / ENTRY).read_text(encoding='utf-8')
    assert sha(source_root / ENTRY) == 'de023abc5b849a56048d5e71bcefc67be1564fe150174607fdc89792905dbe6a'
    begin = original.index('      ap_uint<128> tagged = record[0];')
    end = original.index('\n    }\n    for (unsigned token', begin)
    old = original[begin:end]
    decode_begin = old.index('        ap_uint<16> tagged0')
    decode_end = old.index('        for (unsigned token_pair')
    decode = old[decode_begin:decode_end]
    decode = decode.replace('        ap_int<5> weight0[64], weight1[64];\n#pragma HLS ARRAY_PARTITION variable=weight0 complete\n#pragma HLS ARRAY_PARTITION variable=weight1 complete\n', '')
    decode = decode.replace('weight0, weight1);', 'weight0[pair], weight1[pair]);')
    decode = decode.replace('float scale0 =', 'scale0[pair] =').replace('float scale1 =', 'scale1[pair] =')
    body_begin = old.index('          ap_int<24> dot00')
    body_end = old.index('\n        }', body_begin)
    body = old[body_begin:body_end]
    body = body.replace('m89o_dot(weight0, weight1,', 'm89o_dot(weight0[pair], weight1[pair],')
    body = body.replace('* scale0;', '* scale0[pair];').replace('* scale1;', '* scale1[pair];')
    assert body.replace('weight0[pair]', 'weight0').replace('weight1[pair]', 'weight1').replace('scale0[pair]', 'scale0').replace('scale1[pair]', 'scale1') == old[body_begin:body_end]
    new = '''      ap_uint<128> tagged = record[0];
      // Decode all four independent output pairs before one shared MAC loop.
      // No extra MAC lane, no cross-group reassociation, no early final output.
      ap_int<5> weight0[4][64], weight1[4][64];
      float scale0[4], scale1[4];
#pragma HLS ARRAY_PARTITION variable=weight0 complete dim=0
#pragma HLS ARRAY_PARTITION variable=weight1 complete dim=0
#pragma HLS ARRAY_PARTITION variable=scale0 complete
#pragma HLS ARRAY_PARTITION variable=scale1 complete
      for (unsigned pair = 0; pair < 4; ++pair) {
''' + decode + '''      }
      for (unsigned work = 0; work < 64; ++work) {
#pragma HLS LOOP_FLATTEN off
#pragma HLS PIPELINE II=1
        const unsigned pair = work >> 4;
        const unsigned token_pair = work & 15;
        unsigned token0 = 2 * token_pair, token1 = token0 + 1;
''' + body + '\n      }'
    candidate = original[:begin] + new + original[end:]
    candidate = candidate.replace('static void m441_compute(', 'static void m443_compute(').replace('  m441_compute(records,', '  m443_compute(records,')
    candidate = candidate.replace('  // M441 consumer: identical MAC order, a record owned until all four pairs finish.', '  // M443: one 64-work pipeline per record; original per-output group order.')
    assert candidate.count('return 0x4D343431U;') == 1
    candidate = candidate.replace('return 0x4D343431U;', 'return 0x4D343433U;')
    pending = [source_root / ENTRY, source_root / TB]
    inputs = {}
    while pending:
        p = pending.pop().resolve()
        p.relative_to(source_root.resolve())
        if p in inputs:
            continue
        inputs[p] = p.read_bytes()
        for inc in re.findall(r'^\s*#\s*include\s*"([^"]+)"', inputs[p].decode('utf-8-sig'), re.M):
            pending.append((p.parent / inc).resolve())
    for p, raw in inputs.items():
        if p == (source_root / ENTRY).resolve():
            raw = candidate.encode('utf-8')
        elif p == (source_root / TB).resolve():
            assert raw.count(b'0x4D343431U') == 1
            raw = raw.replace(b'0x4D343431U', b'0x4D343433U')
        atomic(OUT / p.relative_to(source_root.resolve()), raw, immutable=True)
    missing = []
    for p in OUT.rglob('*'):
        if p.suffix in ('.h', '.hpp', '.cpp'):
            for inc in re.findall(r'^\s*#\s*include\s*"([^"]+)"', p.read_text(encoding='utf-8-sig'), re.M):
                if not (p.parent / inc).is_file():
                    missing.append(str(p) + ':' + inc)
    assert not missing
    fixture = ROOT / 'deployment/mage_vl4b/artifacts/m128_m120_real_record_csim_fixture.bin'
    assert sha(fixture) == 'f384f45eea4bc14110a7add49dd0944f0a025403aecc3360369ec999e28257d9'
    tcl = f'''set root {{{OUT.as_posix()}}}
set project {{{PROJECT.as_posix()}}}
if {{[file exists $project]}} {{error "Existing project: collect only"}}
set ::env(M128_FIXTURE_PATH) {{{fixture.as_posix()}}}
cd [file dirname $root]
open_project $project
set_top m89x_runtime_kernel
add_files [file join $root {ENTRY.as_posix()}]
add_files -tb [file join $root {TB.as_posix()}] -cflags "-I[file join $root hls mage_prefill_m89x_runtime]"
open_solution hls -flow_target vivado
set_part {{xck26-sfvc784-2LV-c}}
create_clock -period 4.8 -name default
set_clock_uncertainty 1.3
config_compile -pipeline_loops 0
csim_design -clean
csynth_design
exit
'''
    atomic(OUT / 'run_m443_hls.tcl', tcl.encode(), immutable=True)
    atomic(OUT / 'SOURCE.diff', ''.join(difflib.unified_diff(original.splitlines(True), candidate.splitlines(True), fromfile='frozen-M441.cpp', tofile='independent-M443.cpp')).encode(), immutable=True)
    result = dict(status='PREPARED_M443_INTRA_RECORD_PAIR_PIPELINE01', build_id='0x4D343433', baseline_build_id='0x4D343431', recovery_read=recovery, prerequisite=prior,
                  source_sha256=sha(OUT / ENTRY), original_source_sha256=sha(source_root / ENTRY), missing_headers=missing,
                  shared_MAC_work_per_record=64, original_MAC_work_per_record=64, original_per_output_FP32_group_order=True,
                  original_dot_and_scale_expression_preserved=True, original_record_loader_FIFO34=True,
                  extra_DMA_banks=0, extra_PS_slots=0, same_target_clock_ns=4.8, same_uncertainty_ns=1.3,
                  csim=False, rtl=False, HLS_II_and_DSP_proven=False, shell=False, board=False, performance=False,
                  limits=dict(HLS_wall_budget_s=7200, full_RTL_wall_budget_s=22*3600),
                  gates=['Original seven numerical CSim cases', 'Actual shared MAC II1 and DSP count, actual 64-work loop and resources', 'Complete real Q/gate_up/down numerical CSim', 'Bounded complete real RTL, maximum occupancy/backpressure/TLAST/done/return and timeout', 'Same-constraint routed core/full shell', 'Build-ID/descriptor/chain/layer/text/video', 'Fixed complete-request A/B against M441 with baseline parser'],
                  next_step='Run finite new HLS once. Stop at failed level; no board package before all numerical/RTL/shell gates.',
                  files=[dict(path=p.relative_to(ROOT).as_posix(), sha256=sha(p), bytes=p.stat().st_size) for p in sorted(OUT.rglob('*')) if p.is_file()])
    path = BASE / 'runs/M443-pair-pipeline-preparation-01/RESULT.json'
    atomic(path, encoded(result), immutable=True)
    sync('latest_m443_pair_pipeline_preparation', dict(status=result['status'], result=path.relative_to(ROOT).as_posix(), sha256=sha(path), build_id=result['build_id'], board=False),
         f'## M443独立pair流水线候选准备（2026-10-10）\n\nSHA {sha(path)}；Build0x4D343433。用户已授权两问题实板收益测试。原M441每record四段16-work改为先解码四对再同一64-work流水线，原每输出group顺序/点积/倍率表达式、FIFO34/ABI/输出合并不改。header missing=0，0额外DMA/PS槽；仍须真实II/DSP/完整数值/有界RTL/同约束整壳后才上板。原M441/解析M442证据不改，不组合收益。')
    print(result['status'], sha(path), result['source_sha256'], len(inputs))


if __name__ == '__main__':
    main()
