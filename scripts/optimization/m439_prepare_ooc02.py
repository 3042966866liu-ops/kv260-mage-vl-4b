"""HLS csynth precreates impl RTL; reject run artifacts, not generated inputs."""
import json
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
project=ROOT/'tmp/m439_hls_project_02';impl=project/'hls/impl'
files=sorted(p for p in impl.rglob('*') if p.is_file())
assert len(files)==141
for p in files:
    assert p.suffix in ('.png','.tcl','.v','.vhd','.mdd','.yaml','.txt','.c','.h') or p.relative_to(impl).as_posix()=='misc/drivers/m89x_runtime_kernel_v1_0/src/Makefile',p
    assert p.suffix not in ('.rpt','.xml','.zip','.xpr','.dcp')
syn=project/'hls/syn/verilog'
for p in syn.glob('*.v'):assert sha(p)==sha(impl/'verilog'/p.name),p
ev=BASE/'runs/M439-OOC-precheck-repair-01/RESULT.json'
r=dict(status='PREPARED_M439_OOC_PRECHECK_GENERATED_INPUT_DISTINCTION',original_preparer_sha256=sha(HERE/'m439_prepare_ooc.py'),
       rationale='Original OOC preparer rejected existing impl directory. Completed csynth normally precreates RTL/VHDL/FP-IP Tcl and drivers there; no route/project/report/export artifacts or OOC run log. Actual implementation has not run.',
       verified_preexisting_generated_inputs=[dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p)) for p in files],board=False,implementation_started=False)
atomic(ev,encoded(r),immutable=True)
sync('latest_m439_OOC_precheck_repair',dict(status=r['status'],result=ev.relative_to(ROOT).as_posix(),sha256=sha(ev),build_id='0x4D343339',board=False),
     f'## M439 OOC前置目录分类修正（2026-10-07）\n\nSHA {sha(ev)}；原准备器在运行前因csynth预建impl目录拒绝，0OOC执行。141个已生成输入逐文件核对且无project/route/report/export产物，实际Verilog与综合源同SHA；02保留原检查，改为拒绝真实运行产物与任何原OOC日志，不删目录或重跑综合。')
s=(HERE/'m439_prepare_ooc.py').read_text(encoding='utf-8')
s=s.replace("assert not (project/'hls/impl').exists()", "assert not (out/'core_ooc_console.log').exists()\nassert not any(p.suffix in ('.rpt','.xml','.zip','.xpr','.dcp') for p in (project/'hls/impl').rglob('*') if p.is_file())")
s=s.replace("if(Test-Path (Join-Path $taskRoot 'tmp/m439_hls_project_02/hls/impl')){throw 'Existing implementation: collect only'}", "if(Get-ChildItem (Join-Path $taskRoot 'tmp/m439_hls_project_02/hls/impl') -Recurse -File | Where-Object {$_.Extension -in '.rpt','.xml','.zip','.xpr','.dcp'}){throw 'Existing implementation run artifacts: collect only'}")
s=s.replace('M439-record-load-core-OOC-preparation-01','M439-record-load-core-OOC-preparation-02').replace("'latest_m439_record_load_core_OOC_preparation'","'latest_m439_record_load_core_OOC_preparation02'")
ns={'__name__':'m439_prepare_ooc02','__file__':str(HERE/'m439_prepare_ooc02.py')};exec(compile(s,str(HERE/'m439_prepare_ooc02.py')+':generated-input-guard','exec'),ns)
