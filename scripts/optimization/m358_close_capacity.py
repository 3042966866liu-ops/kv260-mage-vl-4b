"""Close saved capacity failure including post-save destructor diagnostics."""
import json
import m351_workflow as w
from ps_slot_capacity import never_submitted_release

path=w.BASE/'runs/M358-candidate-capacity-board-01/BOARD_RESULT.json'
assert w.sha(path)=='b079a82a89fe01f7131fca275ba1482f381cca814a23683ad6b9358497ea514e'
r=json.loads(path.read_text(encoding='utf-8'))
assert r['status']=='FAIL_M357_COMPLETE_RUNTIME_CAPACITY' and r['gate_return_code']==1
assert len(r['errors'])==1 and r['errors'][0].startswith('CapacityRejected: M357 complete runtime reserve rejected:')
assert r['host_calls']==r['logical_calls']==r['fpga_transactions']==r['model_forward_calls']==0
assert not r['blocked_inference_attempts'] and r['ps_slot']=={} and not r['worker_started']
assert len(r['allocated_buffers'])==len(r['released_buffers'])==r['original_buffer_release_count']==7
assert sorted(r['allocated_buffers'],key=lambda x:x['address'])==sorted(r['released_buffers'],key=lambda x:x['address'])
assert r['safe_buffers_released'] and not r['unsafe_buffers_retained']
assert never_submitted_release(r['final_snapshot'],0,0,[],7)
assert never_submitted_release(r['stable_restore_snapshot'],0,0,[],7)
assert r['stable_overlay_reloaded'] and not r['stable_restore_transaction_submitted']
assert r['stable_bit_sha256']=='1cbf7bbb86cfe64c2349418d5a15890d735bea3fa4c999060c8a9da9ac3206ac'
capacity=r['loaded_capacity'];assert capacity['cma_free_bytes']==34537472 and capacity['required_cma_bytes']==67108864
log=w.ROOT/'tmp/m358_board/run_uart.log';text=log.read_text(encoding='utf-8-sig')
warnings=text.count('RuntimeError: Duplicate original-buffer free refused');assert warnings==7
assert 'M358_DONE gate_rc=1 export_rc=0' in text
out=path.parent/'INTERPRETATION.json'
v=dict(status='CLOSED_CAPACITY_FAILURE_NO_MODEL_ADVANCE',build_id='0x4D333537',raw_sha256=w.sha(path),
 actual_runtime_cma_mib=capacity['cma_free_bytes']/(1<<20),required_cma_mib=64,
 deficit_mib=(capacity['required_cma_bytes']-capacity['cma_free_bytes'])/(1<<20),
 actual_runtime_mem_available_bytes=capacity['mem_available_bytes'],
 observed_system_cma_total_bytes=r['stages'][0]['memory']['system_bytes']['CmaTotal'],
 full_runtime_objects_loaded=True,extra_cma_bank=False,extra_ps_slot=False,
 fpga_transactions=0,forward_calls=0,original_buffers_safely_released=7,
 duplicate_destructor_calls_refused=warnings,destructor_warning_caveat='Seven post-result duplicate free attempts were refused before backend free; original raw did not contain these post-save stderr warnings. Full UART log preserved. Existing idempotent OwnedBufferRelease must replace this legacy wrapper before another gate.',
 stable_overlay_reloaded=True,stable_restore_legal_transaction=False,
 initial_dmasr_zero='Never submitted provenance only; not completed idle',
 no_cache_eviction=True,no_config_change=True,performance_scope='M357 representative Q-chain benefit remains valid; no full model or video claim',
 next_step='Stay at runtime capacity obstacle. No layer/text/video/complete request attempt; do not repeat unchanged load, lower reserve or resume closed O_DIRECT route.')
w.atomic(out,w.encoded(v),immutable=True);digest=w.sha(out)
note=f'## M358 完整runtime容量失败闭合，模型级未启动（2026-10-02）\n\nBuild0x4D333537；完整原M276/M273/M238/M241已构造，0forward/FPGA事务；实际CMA {v["actual_runtime_cma_mib"]:.4f}MiB，64MiB门槛缺{v["deficit_mib"]:.4f}MiB，MemAvailable {capacity["mem_available_bytes"]}B，非4GB耗尽。当前观测CmaTotal800MiB，助手未修改配置；空闲高值仍不证明运行时容量。原7缓冲各安全释放，稳定bit重新加载，但未提交恢复事务，DMASR0仅从未提交生命周期。7次析构重复free被拒绝的退出stderr完整保留，不冒充无告警；未来改用已有幂等包装，不能硬件重跑来消除原告警。原始SHA `{w.sha(path)}`；闭合SHA `{digest}`。M357单Q链3.5279比值/71.6549%耗时减少仍有效，仅L4，无完整模型/视频/晋级；不启动M359层/文本，留容量障碍级，不降低余量或重启已关闭路线。'
w.sync('latest_m358_capacity_closure',dict(status=v['status'],sha256=digest,result=out.relative_to(w.ROOT).as_posix()),note)
report=w.BASE/'M356_RTL_SHARD_OVERLAP_INVESTIGATION.md'
s=report.read_text(encoding='utf-8')
if digest not in s:s+='\n## 完整runtime前置裁决（2026-10-02）\n\n'+note.split('\n\n',1)[1]+'\n\n单层/固定文本原数学对照仅有未校验草稿 `scripts/optimization/m359_runtime_gate.py`，未打包、未上传、未执行；容量条件成立前保持禁用。\n'
w.atomic(report,s.encode('utf-8'))
print(json.dumps(v))
