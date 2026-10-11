"""Preserve the initial offline lifecycle expectation rejection; no board I/O."""
from m351_workflow import HERE,BASE,ROOT,sha,atomic,encoded
p=BASE/'runs/M382-offline-rejection-01/RESULT.json'
r=dict(status='REJECTED_OFFLINE_TEST_EXPECTATIONS',tests=11,failures=2,
       source_sha256={n:sha(HERE/n) for n in ('m382_ps_slot.py','test_m382_ps_slot.py','m382_prepare.py')},
       reasons=['Injected touch exception traceback retains the bytearray: sole-owner cleanup correctly rejects; initial test wrongly expected forced release',
                'Runtime identity failure is preserved as failure, but release identity error capital R did not match lowercase test regex'],
       board_upload=False,overlay_loaded=False,model_forward_calls=0,fpga_transactions=0,
       next_step='Record original failure scalar, accept retained lifecycle as failure, fix regex; do not force free traceback aliases')
atomic(p,encoded(r),immutable=True)
print(sha(p))
