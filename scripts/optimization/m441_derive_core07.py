from m351_workflow import HERE,atomic
s=(HERE/'m441_prepare_core06.py').read_text(encoding='utf-8-sig')
for a,b in [('m441_boundary_control06','m441_boundary_control07'),('M441-boundary-timeout-06','M441-boundary-timeout-07'),('latest_m441_boundary06_timeout','latest_m441_boundary07_timeout'),('M441-core-admission06','M441-core-admission07'),('PREPARED_M441_CORE_ADMISSION06','PREPARED_M441_CORE_ADMISSION07'),('latest_m441_core_admission06','latest_m441_core_admission07'),('m441_core_ooc06','m441_core_ooc07'),('m441_collect_core_ooc06','m441_collect_core_ooc07'),('准入06','准入07')]:
    assert a in s,a;s=s.replace(a,b)
atomic(HERE/'m441_prepare_core07.py',s.encode('utf-8'),immutable=True)
