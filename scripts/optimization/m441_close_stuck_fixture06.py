"""Explicit local-only early abort for proven VIP harness failure, not timeout.
Terminate only this exact compiled xsim kernel, never board/other processes.
Original controller returns/collector then save their own original FAIL.
"""
import argparse,ctypes,json,re,time
from ctypes import wintypes
from m351_workflow import ROOT,BASE,atomic,encoded,sha,sync,HERE
from m441_continue_offline import kernel,opened,exit_code
from m441_boundary_control06 import synchronized,verify_compiled_snapshot

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--enable',action='store_true');a=ap.parse_args();assert a.enable,'Default disabled'
    run=BASE/'runs/M441-boundary-fixture-early-abort-06';assert not (run/'RESULT.json').exists()
    component=BASE/'runs/M441-vip-tail-component-13/RESULT.json'
    synchronized(component,'PASS_M441_ACTUAL_VIP_RELEASE_DIAGNOSIS_COMPONENT','latest_m441_vip_tail_component13')
    assert sha(component)=='cc64a9e27602d4f581bf953545423a0417f3575aacb69e609c214c52348bfe1e'
    verify_compiled_snapshot()
    live=json.loads((ROOT/'tmp/m441_boundary_protocol_06/verilog/max_LIVE.json').read_bytes())
    owner=live['process'];assert owner['pid']==10372 and owner['creation_FILETIME']==134359951219613447
    handle,born=opened(owner['pid'],owner['creation_FILETIME']);assert handle
    try:assert exit_code(handle)==259
    finally:kernel.CloseHandle(handle)
    pid=5116;handle,born=opened(pid);assert handle
    try:
        assert exit_code(handle)==259
        kernel.QueryFullProcessImageNameW.argtypes=[wintypes.HANDLE,wintypes.DWORD,wintypes.LPWSTR,ctypes.POINTER(wintypes.DWORD)]
        kernel.QueryFullProcessImageNameW.restype=wintypes.BOOL
        size=wintypes.DWORD(32768);buf=ctypes.create_unicode_buffer(size.value)
        assert kernel.QueryFullProcessImageNameW(handle,0,buf,ctypes.byref(size))
        image=buf.value
    finally:kernel.CloseHandle(handle)
    target=ROOT/'tmp/m441_boundary_protocol_06/verilog/xsim.dir/m441_max_trace/xsimk.exe'
    assert image.casefold()==str(target).casefold()
    log=ROOT/'tmp/m441_boundary_protocol_06/verilog/max.log';raw=log.read_bytes();text=raw.decode('utf-8-sig',errors='replace')
    assert 'M441_BOUNDARY_LAST_HOLD valid_cycles=128 accepted_before=327679' in text
    progress=re.findall(r'^M441_PROGRESS ([^\r\n]+)',text,re.M);assert len(progress)>2
    assert all('output=327679 ' in x for x in progress[-2:]) and 'terminal=0' in progress[-1]
    assert not re.search(r'^M441MAX_DONE ',text,re.M)
    atomic(run/'ORIGINAL_LOG_SNAPSHOT.log',raw,immutable=True)
    proposal=dict(status='PREPARED_LOCAL_SIMULATOR_EARLY_ABORT_FOR_PROVEN_VIP_RELEASE_FAILURE',
        process_pid=pid,creation_FILETIME=born,exact_image=image,image_sha256=sha(target),batch_owner=owner,
        actual_VIP_component_sha256=sha(component),last_progress=progress[-2:],
        snapshot_sha256=sha(run/'ORIGINAL_LOG_SNAPSHOT.log'),original_control_no_kill_contract_superseded_for_this_local_fixture_failure_only=True,
        termination_reason='Actual unchanged vendor receiver reproduces force/release READY retained0; interposer succeeds. More stalled cycles cannot complete this harness.',
        board=False,COM3=False,DMA=False,process_termination_code=7,script_sha256=sha(HERE/'m441_close_stuck_fixture06.py'))
    prep=run/'PREPARATION.json';atomic(prep,encoded(proposal),immutable=True)
    sync('latest_m441_local_fixture_abort_preparation06',dict(status=proposal['status'],sha256=sha(prep),result=prep.relative_to(ROOT).as_posix(),board=False),
         f'## M441 已证实本地fixture故障提前停止06（2026-10-09）\n\nSHA {sha(prep)}；实际VIP复现SHA {sha(component)}：release后READY保留0，327679卡住；握手interposer小组件通过。只允许精确PID/出生时间/完整exe路径的本地xsim kernel退出码7，覆盖此前本地no-kill约定的这一已证明测试入口错误，非超时kill/板端/DMA。原日志快照先原子保存，原工具与门禁FAIL仍分别保存，禁止晋级。')
    # Re-open with termination rights and recheck exact creation identity immediately.
    h=kernel.OpenProcess(0x1001,False,pid);assert h
    try:
        times=[wintypes.FILETIME() for _ in range(4)]
        assert kernel.GetProcessTimes(h,*[ctypes.byref(x) for x in times])
        assert ((times[0].dwHighDateTime<<32)|times[0].dwLowDateTime)==born and exit_code(h)==259
        kernel.TerminateProcess.argtypes=[wintypes.HANDLE,wintypes.UINT];kernel.TerminateProcess.restype=wintypes.BOOL
        assert kernel.TerminateProcess(h,7)
        deadline=time.monotonic()+10
        while exit_code(h)==259 and time.monotonic()<deadline:time.sleep(.1)
        final=exit_code(h);assert final==7
    finally:kernel.CloseHandle(h)
    result=dict(proposal,status='STOPPED_LOCAL_SIMULATOR_PROVEN_VIP_FIXTURE_FAILURE',termination_rc=final,process_killed=True,
        stable_and_board_untouched=True,tool_rc_pending_separate_original_controller=True,preparation_sha256=sha(prep))
    ev=run/'RESULT.json';atomic(ev,encoded(result),immutable=True)
    sync('latest_m441_local_fixture_abort06',dict(status=result['status'],sha256=sha(ev),result=ev.relative_to(ROOT).as_posix(),board=False),
         f'## M441 本地fixture故障受控提前退出06（2026-10-09）\n\nSHA {sha(ev)}；仅匹配精确身份的本地xsim kernel终止码7，外部控制干预明确保留。旧controller自身process_killed=False不代表这次外部未停止，原工具/collector FAIL随后闭合；0板端/DMA/稳定改动，不加预算。')
    print(result['status'],sha(ev),flush=True)

if __name__=='__main__':main()
