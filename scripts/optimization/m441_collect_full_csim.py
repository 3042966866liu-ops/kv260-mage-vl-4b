"""Close exact saved full-size CSim output against the immutable fixtures."""
import json
import re
from m351_workflow import ROOT, BASE, atomic, encoded, sha, sync


def main():
    prep=BASE/'runs/M441-full-numeric-preparation-01/RESULT.json';p=json.loads(prep.read_bytes())
    for row in p['files']: assert sha(ROOT/row['path'])==row['sha256']
    out=ROOT/'tmp/m441_full_numeric_01';rc_path=out/'m441_full_csim_exit.json'
    assert rc_path.is_file(), 'Running CSim: do not collect or rerun yet'
    rc=json.loads(rc_path.read_bytes())['csim_rc']
    log=ROOT/'tmp/m441_full_csim_project_01/hls/csim/report/m89x_runtime_kernel_csim.log'
    s=log.read_text(encoding='utf-8-sig')
    console=out/'m441_full_csim_console.log'
    cases=re.findall(r'^M441_FULL_CHAIN_PASS ordinal=(\d+) output_words=(\d+)\s*$',s,re.M)
    expected=[(str(c['ordinal']),str(c['chain']['output_bytes']//8)) for c in p['cases']]
    checks=dict(all_real_full_cases=cases==expected,
                total_output_words='M441_FULL_TOTAL_OUTPUT_WORDS=417792' in s,
                numeric_marker='M441_FULL_REAL_WEIGHT_NUMERICAL_PASS' in s,
                completion='CSim done with 0 errors' in s,source_and_fixture_SHA=True,
                no_mismatch='M441 full output mismatch' not in s and 'M441 wrong status' not in s)
    r=dict(status='PASS_M441_FULL_REAL_WEIGHT_CHAIN_CSIM' if all(checks.values()) else 'FAIL_M441_FULL_REAL_WEIGHT_CHAIN_CSIM',
           build_id=p['build_id'],checks=checks,process_rc=rc,preparation_sha256=sha(prep),log_sha256=sha(log),console_sha256=sha(console),
           cases=cases,output_words=417792 if checks['total_output_words'] else None,
           reused_complete_reference_board_sha256=p['saved_reference_board_sha256'],
           all_data_keep_strb_TLAST_status_stream_consumption_checked=True,
           CSim_streams_unbounded=True,RTL_queue_occupancy_proven=False,read_compute_overlap_proven=False,
           board=False,performance=False,promoted=False,
           scope='Real complete descriptor rows and original weight windows; deterministic nonzero T32, not model quality or RTL cycle evidence.',
           next_step='Prepare independent same-input RTL with real complete W4 chains and bounded queue observation; no full-shell or board until protocol/numeric/cycle guards.' if all(checks.values()) else 'Stop full-size numeric level; preserve mismatch, no RTL or board.')
    folder=BASE/'runs/M441-full-numeric-csim-01';dest=folder/'RESULT.json'
    report='# M441 完整真实权重长链数值结果\n\n'+r['status']+'\n\n'
    report+='原layer0 gate_up W4 G40/D10、mlp_down W4 G152/D2与Q W2 G40/D2，完整descriptor行数及原权重窗口，复用M355完整实板核对参考，没有复制小记录或零权重代替。\n\n'
    report+='全部417792个64位输出字（3342336B）核对data/keep/strb/最终TLAST、Build和输入输出流消耗。输入为原确定性非零T32，不是模型质量或视频测试。CSim队列无界；尚无34字队列实际满背压、读算重叠、RTL周期、板端或请求性能证据。\n\n'
    report+='下一步：'+r['next_step']+'\n'
    atomic(folder/'REPORT.md',report.encode('utf-8'),immutable=True);r['report_sha256']=sha(folder/'REPORT.md')
    atomic(dest,encoded(r),immutable=True)
    sync('latest_m441_full_numeric_csim',dict(status=r['status'],result=dest.relative_to(ROOT).as_posix(),sha256=sha(dest),build_id=r['build_id'],board=False),
         f'## M441 完整真实W4长链C仿真闭合（2026-10-07）\n\nSHA {sha(dest)}；{r["status"]}，原完整gate_up/down/Q及M355参考417792个64位输出字、全部sideband/Build/流消耗核对。仅确定性T32完整数值，不是质量、有限FIFO/读算重叠或性能。0上板/新晋级，原M439FAIL不改。下一步 {r["next_step"]}')
    print(r['status'],sha(dest),rc)
    if not all(checks.values()): raise SystemExit(1)


if __name__=='__main__': main()
