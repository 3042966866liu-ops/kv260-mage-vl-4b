"""Preserve candidate01; forbid automatic MAC nest flattening in isolated02."""
import json,difflib
from m351_workflow import ROOT,BASE,atomic,encoded,sha,sync
from m439_prepare import ENTRY,TB,BUILD

def main():
    old=ROOT/'tmp/m439_record_load_01';out=ROOT/'tmp/m439_record_load_02';proj=ROOT/'tmp/m439_hls_project_02'
    assert not out.exists() and not proj.exists()
    hls=BASE/'runs/M439-record-load-hls-01/RESULT.json';hr=json.loads(hls.read_bytes())
    assert hr['status']=='PASS_M439_HLS_RESOURCE_REPORT' and hr['resources']['DSP']==604
    report=ROOT/'tmp/m439_hls_project_01/hls/syn/report/m89x_shard_Pipeline_VITIS_LOOP_79_6_VITIS_LOOP_89_7_csynth.rpt'
    s=report.read_text(encoding='utf-8-sig');assert 'VITIS_LOOP_79_6_VITIS_LOOP_89_7' in s and '|          2|          1|    64|' in s
    ev=BASE/'runs/M439-record-load-schedule-rejection-01/RESULT.json'
    r=dict(status='REJECTED_M439_AUTOMATIC_MAC_NEST_FLATTENING',source_hls_sha256=sha(hls),report_sha256=sha(report),source02_pending=True,
      original_MAC='Four pair calls per record, each16token-pairs and II1; DSP1184',candidate01_MAC='Merged pair/token-pair64-iteration pipeline II2; DSP604',
      numerical_CSim_pass=True,resource_report_pass=True,burst_inference=True,isolated_read_change=False,board=False,rtl_simulated=False,
      next_step='Independent02 adds only LOOP_FLATTEN off in innermost MAC loop to retain original schedule; original01 evidence immutable',
      official_directive_documentation='https://docs.amd.com/r/en-US/ug1399-vitis-hls/Loop_flatten')
    atomic(ev,encoded(r),immutable=True)
    sync('latest_m439_record_load_schedule_rejection',dict(status=r['status'],result=ev.relative_to(ROOT).as_posix(),sha256=sha(ev),build_id=BUILD,board=False),
      f'## M439 首版自动合并计算循环，隔离裁决拒绝（2026-10-07）\n\nSHA {sha(ev)}；首版CSim/资源报告成立，但HLS自动把4pair×16token-pair合并为64次II2过程，DSP604不同于原1184。不能把其周期收益只归因burst。0RTL模拟/板端；原01保持，02仅禁止最内层MAC自动flatten，原算术/累加顺序保持。下一步独立02同数值/综合检查。')
    prep=BASE/'runs/M439-record-load-preparation-01/RESULT.json';pr=json.loads(prep.read_bytes())
    for f in pr['files']:
        p=ROOT/f['path'];assert sha(p)==f['sha256']
        atomic(out/p.relative_to(old),p.read_bytes(),immutable=True)
    before=(old/ENTRY).read_text(encoding='utf-8')
    anchor='for (unsigned token_pair = 0; token_pair < 16; ++token_pair) {\n#pragma HLS PIPELINE II=1'
    replacement='for (unsigned token_pair = 0; token_pair < 16; ++token_pair) {\n#pragma HLS LOOP_FLATTEN off\n#pragma HLS PIPELINE II=1'
    assert before.count(anchor)==1
    after=before.replace(anchor,replacement);assert after.replace(replacement,anchor)==before
    atomic(out/ENTRY,after.encode('utf-8'))
    t=(old/'run_m439_hls.tcl').read_text(encoding='utf-8').replace(old.as_posix(),out.as_posix()).replace('tmp/m439_hls_project_01','tmp/m439_hls_project_02')
    atomic(out/'run_m439_hls.tcl',t.encode('utf-8'))
    atomic(out/'SCHEDULE_GUARD.diff',''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='candidate01.cpp',tofile='candidate02.cpp')).encode('utf-8'),immutable=True)
    r=dict(pr,status='PREPARED_M439_RECORD_LOAD_WITH_ORIGINAL_MAC_NEST',revision='02',prior_preparation_sha256=sha(prep),schedule_rejection_sha256=sha(ev),
      added_guard='LOOP_FLATTEN off in innermost token-pair loop; no arithmetic operations changed',
      files=[dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p)) for p in sorted(out.rglob('*')) if p.is_file()])
    ev=BASE/'runs/M439-record-load-preparation-02/RESULT.json';atomic(ev,encoded(r),immutable=True)
    sync('latest_m439_record_load_preparation02',dict(status=r['status'],result=ev.relative_to(ROOT).as_posix(),sha256=sha(ev),build_id=BUILD,board=False),
      f'## M439 独立02保留原MAC循环（2026-10-07）\n\nSHA {sha(ev)}；Build {BUILD}，相比01仅最内层LOOP_FLATTEN off及新输出路径，不添加预取/算术变体。旧01保留；下一步02数值CSim及同约束综合，必须核对四个16次II1过程和资源，再进入窄RTL。')
    print('M439_PREPARED02',sha(ev))

if __name__=='__main__':main()
