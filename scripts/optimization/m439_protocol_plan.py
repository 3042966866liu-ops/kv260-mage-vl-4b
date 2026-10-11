"""Freeze protocol-gate requirements; do not build, simulate or load hardware."""
from m351_workflow import ROOT, BASE, HERE, atomic, encoded, sha, sync
import json

p = BASE / 'runs/M439-record-load-protocol-plan-01/RESULT.json'
narrow = BASE / 'runs/M439-record-load-narrow-closure-01/RESULT.json'
assert sha(narrow) == '5ed933437978abc82b0067cae5fd714f3a9ac2f28e81f53d56bedf130bf40c60'
assert json.loads(narrow.read_bytes())['status'] == 'PASS_M439_NARROW_BURST_AND_CYCLE_COMPARISON'
sources = ['m357_prepare_fifo_fixture.py', 'm357_prepare_chunked_max.py',
           'm357_collect_max_fifo.py', 'm357_prepare_timeout.py',
           'm357_prepare_debug_guard.py', 'm357_rtl_watchdog.sv']
r = dict(
    status='PLANNED_M439_MAXIMUM_PROTOCOL_GATE_NOT_EXECUTED', build_id='0x4D343339',
    prerequisite='Actual same-constraint core OOC PASS and three-record synchronization; failure closes this version.',
    source_evidence=[dict(path=(HERE / s).relative_to(ROOT).as_posix(), sha256=sha(HERE / s)) for s in sources],
    maximum_case=dict(bits=4, groups=1, descriptors=10, rows_per_shard=512,
                      fifo_capacity=8192, output_words=327680, output_bytes=2621440,
                      oracle='Nonzero activation and packed codes, zero scales; all output words exactly zero. Numerical nonzero W2/W4 evidence remains separate.'),
    checks=[
        'Fresh candidate RTL and vendor FP wrappers with exact SHA closure; never reuse old compiled DUT snapshot.',
        'All actual VIP TV filenames, four pointer scalar TV files, widths and stream counts closed before compile.',
        'Compile with accessible debug metadata; resolve actual hierarchy uniquely from generated RTL, no old hierarchy guessing.',
        'Shared VIP w0 ARREADY hold for 10000 cycles: DUT ARVALID and ARREADY confirm real pending address backpressure.',
        'Shared VIP output-ready hold for 100000 cycles: actual held-valid and at least one FIFO occupancy8192 before release; no overflow on any shard.',
        'If planned pause does not actually saturate FIFO, fail this gate; do not report capacity evidence from configured depth alone.',
        'After release, all10 descriptors/four shards complete, all requested beats received, no pending requests or bad RLAST/RRESP.',
        'Burst address coverage/length/4KiB boundaries and unchanged weight word totals; output data/keep/strb/final TLAST/Build/ap_done exact.',
        'Bounded 10000-cycle Tcl checkpoints, virtual3100000-cycle budget and1800-second wall budget; preserve simulator original rc and failure logs.',
        'Separate watchdog-negative after actual ap_start, 200-cycle noncompletion: fatal visible and adjudicated as expected failure, not kernel PASS.',
        'Collect saved bytes only after any failure; evidence atomic then BOARD/CURRENT/docs synchronize before next gate.'
    ],
    full_shell=False, rtl_executed=False, board=False, promotion=False,
    prohibited=['next-record prefetch', 'PS slot/CMA bank', 'clock relaxation', 'stable-service changes', 'full-model performance claim'],
    next_step='Only after core OOC PASS prepare this bounded same-version protocol gate; after PASS full shell and COM3 Build/descriptor/chain order. Board single-chain benefit precedes M437 whole-request comparison.'
)
atomic(p, encoded(r), immutable=True)
report = '# M439 第一版后续协议门禁规格\n\n这是准备规格，不是执行结果。核心同约束时序失败则结束本版，不启动本门禁。\n\n'
report += '\n'.join('- ' + s for s in r['checks']) + '\n\n' + r['next_step'] + '\n'
atomic(p.parent / 'PLAN.md', report.encode('utf-8'), immutable=True)
sync('latest_m439_record_load_protocol_plan', dict(status=r['status'], result=p.relative_to(ROOT).as_posix(), sha256=sha(p), build_id=r['build_id'], board=False),
     '## M439 最大协议门禁规格（2026-10-07）\n\nSHA ' + sha(p) + '；仅规格，0新增仿真/板端。须核心同约束OOC先PASS；保留最大10descriptor/8192实际FIFO占满、共享VIP地址/输出背压、完整2621440B输出与独立超时负例。旧仿真失败模式已纳入前置检查，无下一条预取/PS/CMA/服务改动。')
print(r['status'], sha(p))
