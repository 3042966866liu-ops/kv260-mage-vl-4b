"""Collect original in-owner read inspection; no board connection or retry."""
import json
from m351_workflow import ROOT,BASE,sha,atomic,sync
from m400_cpu_sentinel_workflow import decode


def main():
    log=ROOT/'tmp/m400/live_inspect02_run.log'
    text=log.read_text(encoding='utf-8-sig')
    raw,d,r=decode(text.replace('M400_LIVE_SHA256','M400_SENTINEL_SHA256').replace('M400_LIVE_CHUNK','M400_SENTINEL_CHUNK'))
    pkg=BASE/'candidates/M400-owner-live-inspect-02'
    if r['manifest_sha256']!=sha(pkg/'PACKAGE_MANIFEST.json') or r['original_owner_pid']!=22715 or r['original_owner_start_ticks']!='1935627':
        raise RuntimeError('Original owner identity differs')
    if any(r[k] for k in ('resources_released','new_overlay_loads','new_DMA_allocations','stable_overlay_restored')):
        raise RuntimeError('Read-only scope exceeded')
    if not r['owner_after']['state'].startswith(('T','t')) or r['owner_after']['start_ticks']!='1935627':
        raise RuntimeError('Original owner no longer stopped')
    if '__M400_LIVE_RUN_RC_'+str(r['gate_return_code'])+'__' not in text:raise RuntimeError('Original return code absent')
    if r['gate_return_code']==0:
        if r['status']!='PASS_LIVE_OWNER_PRISTINE_SOURCE_ABORT' or r['live_owner']['gate_return_code'] or not r['live_owner']['proof']['pristine_source_abort_conditions_passed']:
            raise RuntimeError('Incomplete original Python-owner proof')
    elif r['gate_return_code']!=1 or not r.get('traceback'):raise RuntimeError('Unknown read inspection result')
    out=BASE/'runs/M400-owner-live-inspect-board-02/BOARD_RESULT.json'
    atomic(out,raw,immutable=True);atomic(out.parent/'UART.log',log.read_bytes(),immutable=True)
    sync('latest_m400_owner_live_inspect_board_02',dict(status=r['status'],result=out.relative_to(ROOT).as_posix(),sha256=d,
         original_owner_recovered=False,stable_overlay_restored=False),
         f'## M400 原owner内部只读检查结果（2026-10-04）\n\nSHA `{d}`，原rc{r["gate_return_code"]}，{r["status"]}。精确PID22715/startticks保留，检查后已重新挂起；释放0/新Overlay0/新DMA0/稳定恢复false。失败只调试本回收入口，不重跑模型或改原结果；尚未受控回收，不解锁单层重试。')
    print(json.dumps(r,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
