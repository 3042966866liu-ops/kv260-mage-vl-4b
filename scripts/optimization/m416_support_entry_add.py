"""Add the real early-FAIL envelope check before freezing support evidence."""
from m351_workflow import HERE,atomic
source=(HERE/'m416_support.py').read_text(encoding='utf-8')
needle="        producer.time = SimpleNamespace(sleep=lambda seconds:None)  # Export pacing stub only, explicit synthetic Windows fixture\n"
assert source.count(needle)==1
replacement="""        # Actual main stops in installed-source verification, before Torch/model import.
        early_output=folder/'early/RESULT.json';producer.OUTPUT=early_output
        original_argv=sys.argv;sys.argv=['m416_gate.py',digest,'--enable-local-MLP-A8-screen']
        try: early_rc=producer.main()
        finally:sys.argv=original_argv
        early=json.loads(early_output.read_bytes())
        assert early_rc==1 and early['errors'] and early['visual_forward_calls']==early['dma_allocations']==early['fpga_transactions']==0
        stream=io.StringIO()
        original_sleep=producer.time.sleep;producer.time.sleep=lambda _:None
        try:
            with contextlib.redirect_stdout(stream):producer.export()
        finally:producer.time.sleep=original_sleep
        assert workflow.decode(stream.getvalue()+'M416_DONE gate_rc=1 export_rc=0\\n')[2]==early
        producer.OUTPUT=folder/'capture/RESULT.json'
"""+needle
source=source.replace(needle,replacement)
source=source.replace("'m416_support.py'","'m416_support02.py'")
source=source.replace('actual_export_early_FAIL_and_full_PASS=True,','actual_export_early_FAIL_and_full_PASS=True,actual_main_installed_source_failure_saved=True,')
atomic(HERE/'m416_support02.py',source.encode('utf-8'),immutable=True)
print('M416_ENTRY_FAILURE_SUPPORT_READY')
