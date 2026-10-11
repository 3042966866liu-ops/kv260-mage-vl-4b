from m351_workflow import HERE,atomic
s=(HERE/'m441_continue_boundary_core06.py').read_text(encoding='utf-8-sig')
for a,b in [('m441_continue_boundary_core06','m441_continue_boundary_core07'),('m441_boundary_control06','m441_boundary_control07'),('m441_collect_boundary06','m441_collect_boundary07'),('m441_core_ooc06','m441_core_ooc07'),('m441_collect_core_ooc06','m441_collect_core_ooc07'),('M441-boundary-core-continuation-06','M441-boundary-core-continuation-07'),('latest_m441_boundary_control06','latest_m441_boundary_control07'),('latest_m441_core_admission06','latest_m441_core_admission07'),('latest_m441_boundary06_compile','latest_m441_boundary07_compile'),('M441_FINITE_BOUNDARY_CORE06','M441_FINITE_BOUNDARY_CORE07'),('latest_m441_boundary_core_continuation06','latest_m441_boundary_core_continuation07'),('M441_BOUNDARY_TIMEOUT_CORE06','M441_BOUNDARY_TIMEOUT_CORE07'),('M441_BOUNDARY_CORE06_AT_FAILED_LEVEL','M441_BOUNDARY_CORE07_AT_FAILED_LEVEL'),('latest_m441_boundary_core_result06','latest_m441_boundary_core_result07'),('续行06','续行07')]:
    if a == 'latest_m441_boundary_control06':
        assert b in s,b
        continue
    assert a in s,a;s=s.replace(a,b)
compile(s,'continue07','exec');atomic(HERE/'m441_continue_boundary_core07.py',s.encode(),immutable=True)
source=(HERE/'m441_prepare_shell06.py').read_text(encoding='utf-8-sig')
for a,b in [('m441_core_ooc06','m441_core_ooc07'),('m441_boundary_control06','m441_boundary_control07'),('M441-boundary-rtl-06','M441-boundary-rtl-07'),('M441-boundary-timeout-06','M441-boundary-timeout-07'),('m441_prepare_shell06','m441_prepare_shell07'),('M441-shell-control-preparation-06','M441-shell-control-preparation-07'),('latest_m441_shell_control_preparation06','latest_m441_shell_control_preparation07'),('protocol06','protocol07'),('冻结06','冻结07')]:
    assert a in source,a;source=source.replace(a,b)
compile(source,'shell07','exec');atomic(HERE/'m441_prepare_shell07.py',source.encode(),immutable=True)
