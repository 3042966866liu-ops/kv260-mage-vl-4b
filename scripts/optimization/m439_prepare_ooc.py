"""Only after narrow comparison, freeze same-constraint core-only implementation."""
import json
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
from m439_close_rtl import read
closed,ce=read('runs/M439-record-load-narrow-closure-01/RESULT.json','PASS_M439_NARROW_BURST_AND_CYCLE_COMPARISON')
old=BASE/'runs/M357-core-ooc-01/RESULT.json';r=json.loads(old.read_bytes())
assert r['status']=='PASS_ISOLATED_CORE_ROUTED_TIMING' and r['target_period_ns']==4.8
for f in r['evidence']:assert sha(ROOT/f['path'])==f['sha256'],f['path']
out=ROOT/'tmp/m439_record_load_02';project=ROOT/'tmp/m439_hls_project_02'
assert not (project/'hls/impl').exists()
tcl=out/'run_core_ooc.tcl';atomic(tcl,f'open_project {{{project.as_posix()}}}\nopen_solution hls\nexport_design -rtl verilog -format ip_catalog -flow impl\nexit\n'.encode('utf-8'),immutable=True)
runner=HERE/'m439_run_core_ooc.ps1'
text='''$ErrorActionPreference='Stop'
$taskRoot=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$taskDir=Join-Path $taskRoot 'tmp/m439_record_load_02'
if(Test-Path (Join-Path $taskDir 'core_ooc_console.log')){throw 'Existing core OOC: collect only'}
if(Test-Path (Join-Path $taskRoot 'tmp/m439_hls_project_02/hls/impl')){throw 'Existing implementation: collect only'}
Push-Location (Join-Path $taskRoot 'tmp')
try {
 & 'D:/AMDDesignTools/2026.1/Vitis/bin/vitis-run.bat' --mode hls --tcl (Join-Path $taskDir 'run_core_ooc.tcl') --log (Join-Path $taskDir 'm439_core_ooc') *> (Join-Path $taskDir 'core_ooc_console.log')
 $taskRc=$LASTEXITCODE
 [IO.File]::WriteAllText((Join-Path $taskDir 'core_ooc_exit.json'),("{`"hls_rc`":$taskRc}"),[Text.UTF8Encoding]::new($false))
 if($taskRc -ne 0){throw "M439 core OOC failed rc=$taskRc"}
 Write-Output 'M439_CORE_OOC_RETURN rc=0'
} finally {Pop-Location}
'''
atomic(runner,text.encode('utf-8'),immutable=True)
ev=BASE/'runs/M439-record-load-core-OOC-preparation-01/RESULT.json'
v=dict(status='PREPARED_M439_SAME_CONSTRAINT_CORE_OOC',build_id='0x4D343339',narrow_comparison=ce,original_core_sha256=sha(old),
       original_routed_resources=r['resources'],original_WNS_ns=r['wns_ns'],original_achieved_period_ns=r['achieved_period_ns'],
       original_constraint=dict(path='tmp/m357_hls_project_02/hls/impl/verilog/m89x_runtime_kernel.xdc',sha256=sha(ROOT/'tmp/m357_hls_project_02/hls/impl/verilog/m89x_runtime_kernel.xdc')),
       tcl_sha256=sha(tcl),runner_sha256=sha(runner),target_period_ns=4.8,part='xck26-sfvc784-2LV-c',
       core_only=True,full_shell=False,board=False,maximum_FIFO_gate_pending=True,
       stop='If route fails/resource exceeds/target timing unmet, close this version; do not relax clock or proceed to board.')
atomic(ev,encoded(v),immutable=True)
sync('latest_m439_record_load_core_OOC_preparation',dict(status=v['status'],result=ev.relative_to(ROOT).as_posix(),sha256=sha(ev),build_id=v['build_id'],board=False),
     f'## M439 同约束核心OOC准备（2026-10-07）\n\nSHA {sha(ev)}；原M357核心4.8ns XDC与实际route证据同SHA核对，候选复用相同part/目标的HLS export impl。仅核心不构建整机shell，最大FIFO/descriptor门禁仍待完成；未实现或上板。失败不放宽时钟。')
print('M439_CORE_OOC_PREPARED',sha(ev))
