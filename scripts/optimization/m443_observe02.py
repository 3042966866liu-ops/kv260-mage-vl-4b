"""Recover supervision of the already-running original tool, never relaunch."""
import ctypes
import json
from pathlib import Path
import time
from m441_host_io08 import atomic
from m351_workflow import ROOT, BASE, encoded, sha, sync
from m441_supervisor04 import boot, process, classify

RUN = BASE / 'runs/M443-pair-pipeline-hls-observation-02'
ORIGINAL = ROOT / 'tmp/m443_pair_pipeline_01'


def main():
    if RUN.exists():
        raise RuntimeError('Existing observation: do not restart')
    state = process(552)
    assert state.get('creation_FILETIME') is not None and state.get('status') != 'NOT_FOUND'
    born = state['creation_FILETIME']
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
    kernel.OpenProcess.restype = ctypes.c_void_p
    kernel.GetExitCodeProcess.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint32)]
    kernel.GetExitCodeProcess.restype = ctypes.c_int
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    handle = kernel.OpenProcess(0x1000 | 0x100000, 0, 552)
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    RUN.mkdir(parents=True)
    started_boot = boot()
    tool_epoch = (born - 116444736000000000) / 10000000
    deadline = time.monotonic() + max(0, tool_epoch + 7200 - time.time())
    error = 'Original controller launched cmd PID552, then sha(__file__) received str instead of Path. AttributeError before ACTIVE write; actual tool continues. New observer retains handle to query actual original exit code. No tool rerun.\n'
    atomic(RUN / 'CONTROLLER01_FAILURE.txt', error.encode(), immutable=True)
    active = dict(status='RUNNING_M443_ORIGINAL_TOOL_OBSERVED02', original_tool_pid=552, original_tool_creation_FILETIME=born,
                  original_controller_sha256=sha(ROOT / 'scripts/optimization/m443_control01.py'), observer_sha256=sha(Path(__file__)),
                  original_source_sha256=sha(ORIGINAL / 'hls/mage_prefill_m89x_runtime/mage_prefill_m89x_runtime.cpp'), wall_budget_s=7200,
                  original_boot=started_boot, supervision_failure_sha256=sha(RUN / 'CONTROLLER01_FAILURE.txt'), tool_relaunched=False, tool_killed=False)
    atomic(RUN / 'ACTIVE.json', encoded(active), immutable=True)
    sync('latest_m443_hls_observation', dict(status=active['status'], result=(RUN/'ACTIVE.json').relative_to(ROOT).as_posix(), sha256=sha(RUN/'ACTIVE.json'), board=False),
         f'## M443原工具监督恢复02（2026-10-10）\n\nSHA {sha(RUN / "ACTIVE.json")}；控制01启动后记录路径类型异常，原cmd PID552/HLS仍运行，未重复启动。02仅持有原进程句柄读取实际退出码、原生日与2h预算；原日志/源码同SHA保留。当前未裁决数值/综合/板端。')
    print(json.dumps(active), flush=True)
    rc = ctypes.c_uint32()
    retained = False
    try:
        while True:
            if not kernel.GetExitCodeProcess(handle, ctypes.byref(rc)):
                raise ctypes.WinError(ctypes.get_last_error())
            current = process(552, born)
            atomic(RUN/'PROGRESS.json', encoded(dict(original_rc=None if rc.value == 259 else rc.value,
                   process=current, boot=boot(), elapsed_s=time.time()-tool_epoch, wall_budget_s=7200)))
            if rc.value != 259:
                break
            if time.monotonic() > deadline:
                retained = True
                break
            time.sleep(10)
    finally:
        kernel.CloseHandle(handle)
    result = dict(status='M443_ORIGINAL_HLS_EXIT_REQUIRES_COLLECTION02' if not retained and rc.value == 0 else 'STOP_M443_ORIGINAL_HLS02',
                  original_rc=None if retained else rc.value, elapsed_s=time.time()-tool_epoch, tool_relaunched=False,
                  tool_killed=False, process_retained=retained, budget_exceeded=retained, console_sha256=sha(ORIGINAL/'hls_console.log'))
    atomic(RUN/'EXIT.json', encoded(result), immutable=True)
    sync('latest_m443_hls_exit', dict(status=result['status'], result=(RUN/'EXIT.json').relative_to(ROOT).as_posix(), sha256=sha(RUN/'EXIT.json'), board=False),
         f'## M443原HLS工具退出观察（2026-10-10）\n\nSHA {sha(RUN / "EXIT.json")}；原rc{result["original_rc"]}，retained={retained}，无工具重启/kill。下一步只收集原七数值/实际II/DSP/资源；未有RTL或板端收益。')
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
