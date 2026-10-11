"""Reuse checked board topology; stage only after this candidate's RTL gates."""
from m351_workflow import HERE, ROOT, sha, atomic

# No staging or implementation is performed while any prerequisite is absent.
s=(HERE/'m357_prepare_shell.py').read_text(encoding='utf-8')
begin=s.index("    gates=[")
end=s.index('    proof=[]',begin)
s=s[:begin]+'''    gates=[('M439-record-load-csim-02','PASS_M439_REAL_RECORD_NUMERICAL_CSIM'),
           ('M439-record-load-narrow-closure-01','PASS_M439_NARROW_BURST_AND_CYCLE_COMPARISON'),
           ('M439-max-protocol-rtl-01','PASS_M439_MAXIMUM_PROTOCOL_RTL'),
           ('M439-timeout-negative-01','PASS_M439_EXPECTED_TIMEOUT_NEGATIVE'),
           ('M439-record-load-core-OOC-closure-01','PASS_M439_SAME_CONSTRAINT_CORE_ROUTED_TIMING')]
'''+s[end:]
s=s.replace('m357','m439').replace('M357','M439').replace('0x4D333537','0x4D343339')
s=s.replace('assert len(same)==50',"assert len(same)==len(list(source.glob('*.v')))-1")
s=s.replace('same_computational_rtl=50','same_computational_rtl=len(same)')
s=s.replace("result=dict(status='PREPARED_FRESH_SHELL_INPUTS_AFTER_RTL_GATES',", "result=dict(template_source_sha256=w.sha(ROOT/'scripts/optimization/m357_prepare_shell.py'),preparer_sha256=w.sha(ROOT/'scripts/optimization/m439_prepare_shell.py'),status='PREPARED_FRESH_SHELL_INPUTS_AFTER_RTL_GATES',")
s=s.replace("rejected_preparation='Initial exact observer subtraction left export-only blank lines and correctly stopped before staging; compare nonblank lines exact after subtracting the one known synthesis-excluded observer block. No DUT/export change or hardware rerun.'", "inherited_rejection_prevention='Reuse proven M357 export observer check: remove only one known synthesis-excluded block, require every remaining nonblank computational line exact. This is not a new M439 rejection.'")
ns={'__name__':'m439_prepare_shell','__file__':str(HERE/'m439_prepare_shell.py')}
exec(compile(s,str(HERE/'m439_prepare_shell.py')+':checked-template','exec'),ns)
if __name__=='__main__':
    ns['main']()
    t=(HERE/'m357_build_shell.tcl').read_text(encoding='utf-8')
    # The original M357 route passed but include-bit XSA export failed because
    # bitgen was manual rather than an implementation-run step. Keep the
    # separate original bit + matching HWH contract used by its closed repair.
    t=t.replace('m357','m439').replace('M357','M439').replace('0x4D333537','0x4D343339')
    assert t.count('write_hw_platform -fixed -include_bit -file')==1
    t=t.replace('write_hw_platform -fixed -include_bit -file','write_hw_platform -fixed -file')
    atomic(HERE/'m439_build_shell.tcl',t.encode('utf-8'),immutable=True)
    run=(HERE/'m357_run_shell.ps1').read_text(encoding='utf-8').replace('m357','m439').replace('M357','M439')
    atomic(HERE/'m439_run_shell.ps1',run.encode('utf-8'),immutable=True)
    print('M439 guarded shell runner prepared; no Vivado implementation started')
