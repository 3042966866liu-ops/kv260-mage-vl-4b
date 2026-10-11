#!/usr/bin/env python3
"""Atomically synchronize the verified M236 KV260 PASS."""
from __future__ import annotations
import hashlib, json, os
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
FORMAL=ROOT/'deployment/mage_vl4b/M236_FUSED_PARSE_OVERLAP_BOARD_RESULT_01.json'
OFFLINE=ROOT/'deployment/mage_vl4b/M236_FUSED_PARSE_OVERLAP_OFFLINE_RESULT.json'
BUILD=ROOT/'deployment/mage_vl4b/M236_FUSED_PARSE_OVERLAP_BOARD_DELTA_RESULT.json'
UART=ROOT/'tmp/m236_fused_parse_overlap/attempt_01/run_uart.log'
BOARD=ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json'
CURRENT=ROOT/'CURRENT_STATE.md'; MILESTONES=ROOT/'docsMILESTONES.md'
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def atomic(path,text):
    partial=path.with_name(path.name+'.partial'); partial.write_text(text,encoding='utf-8',newline='\n'); os.replace(partial,path)
def append_once(path,marker,block):
    text=path.read_text(encoding='utf-8')
    if marker in text: raise RuntimeError(f'duplicate M236 block in {path}')
    atomic(path,text.rstrip()+'\n\n'+block.strip()+'\n')
def main():
    formal=json.loads(FORMAL.read_text(encoding='utf-8')); family=formal['family']; build=json.loads(BUILD.read_text(encoding='utf-8')); offline=json.loads(OFFLINE.read_text(encoding='utf-8'))
    if formal.get('status')!='PASS' or family.get('status')!='PASS' or not formal.get('service_restore_marker'): raise RuntimeError('M236 board/service PASS missing')
    if family.get('output_bit_exact') is not True or float(family.get('maximum_abs_error'))!=0.0: raise RuntimeError('M236 numerical identity missing')
    if float(family['wall_speedup'])<float(family['required_wall_speedup']): raise RuntimeError('M236 performance threshold missing')
    if offline.get('status')!='PASS' or offline.get('injected_adaptive_retry_pass') is not True: raise RuntimeError('M236 offline predecessor mismatch')
    board=json.loads(BOARD.read_text(encoding='utf-8'))
    board['latest_m236_fused_parse_overlap']={'status':'PASS','classification':'Real KV260 849-token single-family T32 fused-parse/launch-overlap gate with bit-exact output and restored service; independent of T64; not fixed-text, video, Web, or real-time evidence.','candidate_build_id':family['build_id'],'tokens':family['tokens'],'t32_blocks':family['t32_blocks_per_run'],'m231_wall_ms':family['m231_wall_ms'],'m236_wall_ms':family['m236_wall_ms'],'wall_speedup':family['wall_speedup'],'required_wall_speedup':family['required_wall_speedup'],'output_bit_exact':family['output_bit_exact'],'maximum_abs_error':family['maximum_abs_error'],'host_calls':family['host_calls'],'expected_host_calls':family['expected_host_calls'],'pipeline_submissions':family['pipeline_submissions'],'pipeline_reuse_waits':family['pipeline_reuse_waits'],'pipeline_retry_launches':family['pipeline_retry_launches'],'standalone_raw_finite_scan':family['standalone_raw_finite_scan'],'adaptive_scale_retry_preserved':family['adaptive_scale_retry_preserved'],'cpu_linear_fallback':family['cpu_linear_fallback'],'delta_manifest_sha256':formal['delta_manifest_sha256'],'formal_result':FORMAL.relative_to(ROOT).as_posix(),'formal_result_sha256':sha(FORMAL),'uart_log':UART.relative_to(ROOT).as_posix(),'uart_log_sha256':sha(UART),'service_restore_marker':True,'boot_dtb_cma_partitions_services_changed':False,'stable_rollback_preserved':True,'next_gate':'Frozen fixed-text complete 4B FPGA E2E with exact token and no CPU Linear fallback; do not integrate Web before it passes.'}
    atomic(BOARD,json.dumps(board,indent=2,ensure_ascii=False)+'\n')
    block=f'''<!-- M236_FUSED_PARSE_OVERLAP_START -->
## M236 — T32 fused-parse/launch overlap：REAL_KV260_PASS（2026-09-01）

- 在 M235 双输出 DMA 缓冲基础上，把有限性检查合并到已经物化的 cache-hot FP32 解析结果中；正常路径不再第二遍扫描 raw DMA 包，同时保留自适应 activation-scale 降档重试。
- 162 条合同、`161,005,568` 输出字节、1/17/32 token、注入 NaN/Inf 与注入重试离线门禁均 PASS；模型数学、量化与 FPGA 事务合同未改变。
- KV260 849-token q-family：`{family['m231_wall_ms']:.3f} -> {family['m236_wall_ms']:.3f} ms`（`{family['wall_speedup']:.5f}x`）；输出位精确、最大误差 0、54/54 calls、27 次流水提交、25 次缓冲复用等待、无重试、无 CPU Linear fallback。
- manifest-first、1,800-byte 分块上传；候选 manifest `{formal['delta_manifest_sha256']}`。服务恢复 PID `114534` 并通过 health；boot/DTB/CMA/分区与稳定回滚未改变。
- 正式结果：`{FORMAL.relative_to(ROOT).as_posix()}`（SHA-256 `{sha(FORMAL)}`）；UART SHA-256 `{sha(UART)}`。下一门禁仅运行冻结 fixed-text 完整 4B E2E，未通过前不接 Web。
<!-- M236_FUSED_PARSE_OVERLAP_END -->'''
    append_once(CURRENT,'<!-- M236_FUSED_PARSE_OVERLAP_START -->',block); append_once(MILESTONES,'<!-- M236_FUSED_PARSE_OVERLAP_START -->',block)
    print(json.dumps({'gate':'M236-state-sync','status':'PASS','formal_sha256':sha(FORMAL),'uart_sha256':sha(UART),'manifest_sha256':build['package_manifest_sha256'],'next_gate':'frozen fixed-text E2E'},indent=2)); print('M236_STATE_SYNC_PASS'); return 0
if __name__=='__main__': raise SystemExit(main())
