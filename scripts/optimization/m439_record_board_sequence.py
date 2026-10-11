"""Record saved complete fake-flow checks without repeating them."""
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
log=ROOT/'tmp/m439_board_sequence_test02.log';s=log.read_text(encoding='utf-8-sig')
assert 'Ran 9 tests' in s and s.rstrip().endswith('OK')
assert 'PASS_M439_COMPARE' in s and 'FAIL_M439_COMPARE' in s and 'FAIL_UNSAFE_RETAINED' in s
r=dict(status='PASS_M439_COMPLETE_BOARD_FLOW_FAKE_ONLY',build_id='0x4D343339',tests_run=9,additional_new_flow_tests=5,inherited_recovery_tests=4,probe_sha256=sha(HERE/'m439_board_probe.py'),test_sha256=sha(HERE/'test_m439_board_sequence.py'),log_path=log.relative_to(ROOT).as_posix(),log_sha256=sha(log),rejected_harness_log_sha256=sha(ROOT/'tmp/m439_board_sequence_test.log'),rejected_harness_reason='Fake Compare fixture omitted packaged baseline bit. Added fake baseline only; actual probe unchanged.',checks=['Descriptor W2 and restore','W2 full Q plus W4 two-descriptor chain and restore','All217 balanced/primer/formal transactions,150 owned allocations and9 Overlay selections','No measured benefit retains failure and safely restores stable without repeating samples','Chain timeout retains all buffers,process,lock andOverlay'],fake_DMA=True,board=False,overlay_loaded=False)
p=BASE/'runs/M439-board-sequence-checks-01/RESULT.json';atomic(p,encoded(r),immutable=True)
sync('latest_m439_board_sequence_checks',dict(status=r['status'],result=p.relative_to(ROOT).as_posix(),sha256=sha(p),build_id=r['build_id'],board=False),'## M439 完整板测控制流离线核对（2026-10-07）\n\nSHA '+sha(p)+'；实际新probe全流程CPU fake检查9项（5新流程＋4既有恢复），覆盖全部217固定对照事务/150所有者分配/9次Overlay选择及无收益安全恢复、链超时保留。首fake入口缺baseline bit失败保留，只补fake夹具，真实probe无改；0上板/实板性能。')
print(r['status'],sha(p))
