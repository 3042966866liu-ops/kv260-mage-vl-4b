"""Decode saved snapshot and preserve the failed native debugger attempt."""
import json
from m351_workflow import ROOT,BASE,sha,atomic,sync
from m400_cpu_sentinel_workflow import decode


def main():
    log=ROOT/'tmp/m400/native_stack02_run.log';text=log.read_text(encoding='utf-8-sig')
    raw,d,r=decode(text.replace('M400_STACK_SHA256','M400_SENTINEL_SHA256').replace('M400_STACK_CHUNK','M400_SENTINEL_CHUNK'))
    if r['manifest_sha256']!=sha(BASE/'candidates/M400-native-stack-02/PACKAGE_MANIFEST.json') or r['original_owner_pid']!=22715:
        raise RuntimeError('Snapshot identity differs')
    if not r['function_calls_forbidden'] or any(r[k] for k in ('resources_released','new_overlay_loads','new_DMA_allocations','owner_resumed')):
        raise RuntimeError('Read-only stack scope exceeded')
    if '__M400_STACK_RUN_RC_'+str(r['gate_return_code'])+'__' not in text or r['owner_after']['start_ticks']!='1935627':
        raise RuntimeError('Original return code/owner differs')
    out=BASE/'runs/M400-native-stack-board-02/BOARD_RESULT.json'
    atomic(out,raw,immutable=True);atomic(out.parent/'UART.log',log.read_bytes(),immutable=True)
    atomic(out.parent/'GDB.log',r.get('gdb_log','').encode('utf-8'),immutable=True)
    sync('latest_m400_native_stack_board_02',dict(status=r['status'],result=out.relative_to(ROOT).as_posix(),sha256=d,
          original_owner_recovered=False,stable_overlay_restored=False),
         f'## M400 只读native调试现场（2026-10-04）\n\nSHA `{d}`，原rc{r["gate_return_code"]}，{r["status"]}；仅保存文件/native stack，GDB禁止函数调用，无SIGCONT/close/新Overlay/DMA。stdout保存，原PID22715保持；原owner未回收、稳定未恢复。后续仅根据实际日志定位调试阻塞，不反复相同注入，不重跑模型。')
    print(json.dumps(r,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
