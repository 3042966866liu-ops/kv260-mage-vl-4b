#!/usr/bin/env python3
"""Synchronize the verified M238 real-board PASS into authoritative state."""
from __future__ import annotations
import hashlib, json, os
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
FORMAL=ROOT/'deployment/mage_vl4b/M238_INPUT_PREFETCH_BOARD_RESULT_02.json'
OFFLINE=ROOT/'deployment/mage_vl4b/M238_INPUT_PREFETCH_OFFLINE_RESULT.json'
UART=ROOT/'tmp/m238_input_prefetch/attempt_02/run_uart.log'
BOARD=ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json'
CURRENT=ROOT/'CURRENT_STATE.md'; MILESTONES=ROOT/'docsMILESTONES.md'
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def atomic(path,text):
    partial=path.with_name(path.name+'.partial'); partial.write_text(text,encoding='utf-8',newline='\n'); os.replace(partial,path)
def append_once(path,marker,block):
    text=path.read_text(encoding='utf-8')
    if marker in text: raise RuntimeError(f'duplicate M238 block in {path}')
    atomic(path,text.rstrip()+'\n\n'+block.strip()+'\n')
def main():
    formal=json.loads(FORMAL.read_text(encoding='utf-8')); family=formal['family']; offline=json.loads(OFFLINE.read_text(encoding='utf-8'))
    if formal.get('status')!='PASS' or family.get('status')!='PASS' or formal.get('service_restore_marker') is not True: raise RuntimeError('M238 board/service PASS missing')
    if family.get('output_bit_exact') is not True or float(family.get('maximum_abs_error'))!=0.0: raise RuntimeError('M238 numerical identity missing')
    if float(family['wall_speedup'])<float(family['required_wall_speedup']): raise RuntimeError('M238 speed threshold missing')
    if offline.get('status')!='PASS' or offline.get('packet_bit_exact') is not True or offline.get('injected_adaptive_retry_pass') is not True: raise RuntimeError('M238 offline gate mismatch')
    board=json.loads(BOARD.read_text(encoding='utf-8'))
    board['latest_m238_input_pack_prefetch']={
        'status':'PASS','classification':'Real KV260 M236-versus-M238 frozen 849-token q-family T32 host-pipeline comparison; independent of T64; not fixed-text, video, Web, or real-time evidence.',
        'candidate_build_id':family['build_id'],'tokens':family['tokens'],'t32_blocks':family['t32_blocks_per_run'],
        'm236_wall_ms':family['m236_wall_ms'],'m238_wall_ms':family['m238_wall_ms'],'wall_speedup':family['wall_speedup'],'required_wall_speedup':family['required_wall_speedup'],
        'output_bit_exact':family['output_bit_exact'],'maximum_abs_error':family['maximum_abs_error'],'host_calls':family['host_calls'],'expected_host_calls':family['expected_host_calls'],
        'pack_prefetch_submissions':family['pack_prefetch_submissions'],'prepacked_launches':family['prepacked_launches'],'pipeline_retry_launches':family['pipeline_retry_launches'],
        'cpu_linear_fallback':family['cpu_linear_fallback'],'delta_manifest_sha256':formal['delta_manifest_sha256'],
        'formal_result':FORMAL.relative_to(ROOT).as_posix(),'formal_result_sha256':sha(FORMAL),'uart_log':UART.relative_to(ROOT).as_posix(),'uart_log_sha256':sha(UART),
        'service_restore_marker':True,'boot_dtb_cma_partitions_services_changed':False,'stable_rollback_preserved':True,
        'next_gate':'Measure the complete frozen 849-token language Prefill with per-family/phase evidence before Web integration; do not extrapolate q-family speedup to full model.'
    }
    atomic(BOARD,json.dumps(board,indent=2,ensure_ascii=False)+'\n')
    block=f'''<!-- M238_INPUT_PACK_PREFETCH_START -->
## M238 — T32 输入预打包与 M236 解析流水并行：REAL_KV260_PASS（2026-09-01）

- 不修改 T64、不改 xclbin、模型数学、量化公式或 FPGA 事务；在 PL 执行 T32 块 N 时，由独立 A53 worker 预先量化并打包块 N+1，同时保留 M236 的输出解析流水。
- 离线 849-token/27-block packet、输出位精确及注入非有限值后的自适应降档重试全部通过。
- 真实 KV260 q-family：`{family['m236_wall_ms']:.3f} -> {family['m238_wall_ms']:.3f} ms`，提升 `{family['wall_speedup']:.5f}x`；输出 SHA 一致、最大误差 0、54/54 host calls、无重试、无 CPU Linear fallback。
- 27 次预打包的主线程等待仅 `{family['pack_prefetch_wait_ms_total']:.3f} ms`；pack 工作已基本隐藏，但 PL `launch_wait` 仍约 `{family['m238_phase_ms']['launch_wait']:.3f} ms`，继续表明主要下限在 T32 PL 执行/批次数。
- 候选 manifest `{formal['delta_manifest_sha256']}`；服务恢复 PID `116831` 并通过 health。boot、DTB、CMA、分区和稳定回滚未改变。
- 正式结果：`{FORMAL.relative_to(ROOT).as_posix()}`（SHA-256 `{sha(FORMAL)}`）；UART SHA-256 `{sha(UART)}`。该 4.7% 仅为单 q-family，不得外推为完整 4B 或视频加速。
<!-- M238_INPUT_PACK_PREFETCH_END -->'''
    append_once(CURRENT,'<!-- M238_INPUT_PACK_PREFETCH_START -->',block); append_once(MILESTONES,'<!-- M238_INPUT_PACK_PREFETCH_START -->',block)
    print(json.dumps({'gate':'M238-state-sync','status':'PASS','formal_sha256':sha(FORMAL),'uart_sha256':sha(UART),'next_gate':'complete frozen 849-token language Prefill phase profile'},indent=2)); print('M238_STATE_SYNC_PASS'); return 0
if __name__=='__main__': raise SystemExit(main())
