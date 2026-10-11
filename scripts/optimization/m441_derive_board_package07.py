"""Prepare guarded package builder; do not stage hardware or access board."""
from m351_workflow import HERE,atomic
s=(HERE/'m439_prepare_board_package.py').read_text(encoding='utf-8-sig')
s=s.replace('m439','m441').replace('M439','M441').replace('0x4D343339','0x4D343431')
begin=s.index("    names=[");end=s.index("    for name in names:",begin)
s=s[:begin]+"""    names=['M441-record-pipeline-preparation-02','M441-full-numeric-csim-01',
      'M441-actual-schedule-queue-guard-01','M441-W4-zero-continuation-05',
      'M441-long-B-gate_up-zero-02','M441-boundary-rtl-07','M441-boundary-timeout-07',
      'M441-record-pipeline-core-OOC-closure-01','M441-full-shell-01','M441-hwh-abi-01',
      'M441-board-support-preparation-07','M441-board-support-checks-07','M441-transfer-controls-checks-07']
"""+s[end:]
s=s.replace('M441-record-load-preparation-02','M441-record-pipeline-preparation-02')
s=s.replace('M441-board-support-preparation-01','M441-board-support-preparation-07').replace('M441-board-support-checks-01','M441-board-support-checks-07')
s=s.replace("('m441_control.ps1','m441_transfer.py','m441_transfer_collection.py')", "('m441_control07.ps1','m441_transfer.py','m441_transfer_collection.py','m441_board_collection.py','test_m441_board_support07.py','m441_prepare_board_support07.py','m441_freeze_board_support07.py')")
old="change='Only current W2/W4 record sequential load into 17-word PL buffer; original MAC scheduling/order/output preserved.'"
assert old in s
s=s.replace(old,"change='Per-shard bounded 34-word DATAFLOW stream overlaps sequential current/next W2-W4 record loading with unchanged compute. Original MAC order/math/output and board ABI preserved.'")
s=s.replace('next_record_prefetch=False','next_record_prefetch=True')
s=s.replace("schema='m441-record-load-candidate-v1'","schema='m441-bounded-record-pipeline-candidate-v1'")
# Original helper names have been frozen separately; actual host files are not payload.
s=s.replace("p.name not in ('m441_control07.ps1'", "p.name not in ('m441_control07.ps1'")
compile(s,'package07','exec')
atomic(HERE/'m441_prepare_board_package07.py',s.encode(),immutable=True)
print('GUARDED_BOARD_PACKAGE07_BUILDER_PREPARED_ONLY')
