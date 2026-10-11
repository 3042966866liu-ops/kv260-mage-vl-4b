"""Generate exact local framing/network-cleanup negatives for new transport."""
from m351_workflow import HERE,atomic
s=(HERE/'m439_check_transfer_controls.py').read_text(encoding='utf-8-sig')
s=s.replace('m439','m441').replace('M439','M441').replace('0x4D343339','0x4D343431')
s=s.replace('M441-transfer-controls-checks-01','M441-transfer-controls-checks-07')
s=s.replace('latest_m441_transfer_controls_checks','latest_m441_transfer_controls_checks07')
s=s.replace("rejected_first_sandbox_attempt='Local socket framing harness exceeded bounded 30s subprocess budget in sandbox; no board/real-peer connection. No transport implementation change before native local rerun.'", "inherited_prevention='Reuse bounded native local fixture tests; no board or external peer access. Prior M439 sandbox failure remains its own record.'")
compile(s,'transportchecks07','exec');atomic(HERE/'m441_check_transfer_controls07.py',s.encode(),immutable=True)
print('TRANSPORT_CHECKS07_PREPARED_ONLY')
