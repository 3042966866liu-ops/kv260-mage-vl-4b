"""Only move request Build patch after unchanged loader identity checks."""
import ast
import json
import shutil
import m351_workflow as w


def main():
    old=w.BASE/'candidates/M368-staged-video-02';pkg=w.BASE/'candidates/M368-staged-video-03';out=w.BASE/'runs/M368-video-support-03'
    if pkg.exists() or out.exists():raise RuntimeError('Immutable identity repair exists')
    raw=w.BASE/'runs/M368-staged-video-board-01/BOARD_RESULT.json';r=json.loads(raw.read_text(encoding='utf-8'))
    assert w.sha(raw)=='ccdb2d478c5b0f586fca1bc2869f304a2b5b7d5ec52df60113034ec120af19fa'
    assert r['fpga_transactions']==0 and not r['allocated_buffers'] and not r['overlay_loaded']
    for n in ('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'):assert w.sha(raw) in (w.ROOT/n).read_text(encoding='utf-8')
    for p in old.iterdir():
        if p.name not in ('PACKAGE_MANIFEST.json','SHA256SUMS'):pkg.mkdir(exist_ok=True);shutil.copyfile(p,pkg/p.name)
    p=pkg/'m368_staged_video_gate.py';text=p.read_text(encoding='utf-8')
    early="        patch(video_server,'BUILD_ID',TARGET_BUILD)\n"
    assert text.count(early)==1;text=text.replace(early,'')
    needle='        engine.load()\n';assert text.count(needle)==1
    text=text.replace(needle,needle+early).replace('m368_staged_video_01','m368_staged_video_02')
    needle="        verify_self(HERE,args.manifest_sha); result['manifest_sha256'] = args.manifest_sha"
    extra="""
        identity_path=Path('/home/ubuntu/m368_identity_preflight_01/RESULT.json')
        if sha256(identity_path)!=os.environ.get('M368_IDENTITY_PREFLIGHT_SHA'):raise RuntimeError('Identity preflight raw SHA differs')
        identity=json.loads(identity_path.read_text(encoding='utf-8'))
        if identity['status']!='PASS_ACTUAL_LOADER_IDENTITY_SEQUENCE' or identity['manifest_sha256']!=args.manifest_sha or identity['gate_return_code']:raise RuntimeError('Actual loader identity sequence prerequisite differs')"""
    assert text.count(needle)==1;text=text.replace(needle,needle+extra)
    assert text.index('engine.load()')<text.index("patch(video_server,'BUILD_ID',TARGET_BUILD)")<text.index('engine.stream(request)')
    ast.parse(text,feature_version=(3,10));w.atomic(p,text.encode('utf-8'))
    shutil.copyfile(w.HERE/'m368_identity_preflight.py',pkg/'m368_identity_preflight.py')
    export="""import base64,hashlib,json,os
from pathlib import Path
if os.geteuid()!=0:raise RuntimeError('Root required')
raw=Path('/home/ubuntu/m368_identity_preflight_01/RESULT.json').read_bytes();r=json.loads(raw)
print('M368_IDENTITY_SHA256='+hashlib.sha256(raw).hexdigest(),flush=True)
print('M368_IDENTITY_RC='+str(r['gate_return_code']),flush=True)
parts=[raw[i:i+900] for i in range(0,len(raw),900)]
for i,p in enumerate(parts):print(f'M368_IDENTITY_CHUNK={i}/{len(parts)}:'+base64.b64encode(p).decode(),flush=True)
"""
    w.atomic(pkg/'m368_identity_export.py',export.encode('utf-8'))
    runner=pkg/'run_m368_staged_video.sh';t=runner.read_text(encoding='utf-8').replace('m368_staged_video_01','m368_staged_video_02')
    needle='if [[ $2 == Collect ]]; then'
    block='''if [[ $2 == Identity || $2 == IdentityCollect ]]; then
  if [[ $2 == Identity ]]; then
    [[ ! -e /home/ubuntu/m368_identity_preflight_01/RESULT.json ]] || exit 67
    set +e
    "$task_python" -B "$task_dir/m368_identity_preflight.py" "$1" --enable
    task_identity_rc=$?
    "$task_python" -B "$task_dir/m368_identity_export.py"
    task_export_rc=$?
    set -e
    echo "M368_IDENTITY_DONE gate_rc=$task_identity_rc export_rc=$task_export_rc"
    if [[ $task_identity_rc != 0 ]]; then exit "$task_identity_rc"; fi
    exit "$task_export_rc"
  fi
  "$task_python" -B "$task_dir/m368_identity_export.py"; exit 0
fi
'''
    assert t.count(needle)==1;t=t.replace(needle,block+needle);w.atomic(runner,t.encode('utf-8'))
    exportp=pkg/'m368_export_result.py';w.atomic(exportp,exportp.read_text(encoding='utf-8').replace('m368_staged_video_01','m368_staged_video_02').encode('utf-8'))
    assembler=pkg/'m368_assemble.py';t=assembler.read_text(encoding='utf-8').replace('/home/ubuntu/m366_staged_text_candidate_03','/home/ubuntu/m368_staged_video_candidate_02').replace('9434b439a23daa021c39086e43736b331225460eedaf261e2c70b3a6ff9545ca',w.sha(old/'PACKAGE_MANIFEST.json'));w.atomic(assembler,t.encode('utf-8'))
    rows=[dict(path=p.name,bytes=p.stat().st_size,sha256=w.sha(p)) for p in sorted(pkg.iterdir())]
    w.atomic(pkg/'SHA256SUMS',''.join(x['sha256']+'  '+x['path']+'\n' for x in rows).encode('ascii'))
    rows.append(dict(path='SHA256SUMS',bytes=(pkg/'SHA256SUMS').stat().st_size,sha256=w.sha(pkg/'SHA256SUMS')))
    w.atomic(pkg/'PACKAGE_MANIFEST.json',w.encoded(dict(schema='m368-independent159-video-identity-repair-v3',files=rows,file_count=len(rows),total_bytes=sum(x['bytes'] for x in rows))))
    for p in pkg.glob('*.py'):ast.parse(p.read_text(encoding='utf-8'),feature_version=(3,10))
    control=(w.HERE/'m368_control.ps1').read_text(encoding='utf-8').replace("'SelfTest')","'SelfTest','Identity','IdentityCollect')").replace('M368-staged-video-02','M368-staged-video-03').replace('M368-video-support-02','M368-video-support-03').replace('m368_staged_video_candidate_02','m368_staged_video_candidate_03').replace('tmp/m368/','tmp/m36803/').replace('M368-video-transfer-01','M368-video-transfer-02').replace('candidates/M366-staged-text-03/PACKAGE_MANIFEST.json','candidates/M368-staged-video-02/PACKAGE_MANIFEST.json')
    needle="if($Mode -eq 'Run'){\n $taskTransfer="
    block="""if($Mode -in @('Identity','IdentityCollect')){
 $taskIdentityLog=if($Mode -eq 'Identity'){'tmp/m36803/identity.log'}else{'tmp/m36803/identity_collect.log'}
 if($Mode -eq 'Identity' -and(Test-Path(Join-Path $taskRoot $taskIdentityLog))){throw 'Identity original attempt exists; IdentityCollect only'}
 Invoke-GateAndCollect {
  & $taskUart -Command "sudo -n bash $taskRemote/run_m368_staged_video.sh $taskDigest $Mode B1" -LogPath $taskIdentityLog -TimeoutSeconds 90 -MarkerPrefix '__M368_IDENTITY_RC_'
 } {
  & $taskPython -B (Join-Path $PSScriptRoot 'm368_identity_collect.py') (Join-Path $taskRoot $taskIdentityLog)
  if($LASTEXITCODE -ne 0){throw 'Identity collection incomplete; recover saved bytes only'}
 }
 exit 0
}
$taskIdentitySHA=''
if($Mode -eq 'Run'){
 $taskIdentityPath=Join-Path $taskRoot 'deployment/mage_vl4b/optimization_v1/runs/M368-identity-board-01/BOARD_RESULT.json'
 $taskIdentity=Get-Content $taskIdentityPath -Raw -Encoding UTF8|ConvertFrom-Json
 if($taskIdentity.status -ne 'PASS_ACTUAL_LOADER_IDENTITY_SEQUENCE'){throw 'Actual loader identity sequence not PASS'}
 $taskIdentitySHA=(Get-FileHash $taskIdentityPath -Algorithm SHA256).Hash.ToLowerInvariant()
 foreach($taskName in @('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json')){if(-not[IO.File]::ReadAllText((Join-Path $taskRoot $taskName)).Contains($taskIdentitySHA)){throw 'Identity evidence not synchronized'}}
}
"""
    assert control.count(needle)==1;control=control.replace(needle,block+needle).replace('env M368_ENABLE_STAGED_VIDEO=1','env M368_IDENTITY_PREFLIGHT_SHA=$taskIdentitySHA M368_ENABLE_STAGED_VIDEO=1')
    w.atomic(w.HERE/'m36803_control.ps1',control.encode('utf-8'))
    collect=(w.HERE/'m368_collect.py').read_text(encoding='utf-8').replace('M368-staged-video-02','M368-staged-video-03').replace('M368-staged-video-board-01','M368-staged-video-board-02');w.atomic(w.HERE/'m36803_collect.py',collect.encode('utf-8'))
    control=control.replace('m368_collect.py','m36803_collect.py').replace('m368_transfer_receipt.py','m36803_transfer_receipt.py');w.atomic(w.HERE/'m36803_control.ps1',control.encode('utf-8'))
    receipt=(w.HERE/'m368_transfer_receipt.py').read_text(encoding='utf-8').replace('from m368_collect','from m36803_collect').replace('tmp/m368/','tmp/m36803/').replace('M368-video-transfer-01','M368-video-transfer-02').replace('已冻结M366-03','已冻结M368-02');w.atomic(w.HERE/'m36803_transfer_receipt.py',receipt.encode('utf-8'))
    prior=w.BASE/'runs/M368-video-support-02/RESULT.json';result=json.loads(prior.read_text(encoding='utf-8'))
    result.update(manifest_sha256=w.sha(pkg/'PACKAGE_MANIFEST.json'),identity_patch_only_after_load=True,requires_actual_CPU_only_preflight_before_hardware=True,prior_failed_raw_sha256=w.sha(raw),prior_support_sha256=w.sha(prior))
    w.atomic(out/'RESULT.json',w.encoded(result),immutable=True);d=w.sha(out/'RESULT.json')
    w.sync('latest_m368_video_support',dict(status=result['status'],sha256=d,result=(out/'RESULT.json').relative_to(w.ROOT).as_posix(),manifest_sha256=result['manifest_sha256']),f'## M368 加载身份时序03修复准备\n\n02失败在原M243发布preflight，0Overlay/缓冲/FPGA；只将请求Build patch移到engine.load之后，原校验/数学不改，原失败保留。03要求实际冻结CPU-only preflight先原稳定PASS/提前候选FAIL/恢复PASS，并三记录同步后才准入硬件。支持SHA `{d}`。尚未重新执行视频，性能未解锁。')
    print(json.dumps(dict(status=result['status'],manifest_sha256=result['manifest_sha256'],support_sha256=d)))


if __name__=='__main__':main()
