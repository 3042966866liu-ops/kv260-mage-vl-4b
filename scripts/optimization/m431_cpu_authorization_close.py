"""Close one sudo stop and freeze fresh CPU upload receipt paths."""
import json
import subprocess
from m351_workflow import ROOT, BASE, HERE, atomic, encoded, sha, sync
from m431_cpu_finalize import PKG


def main():
    log = ROOT / 'tmp/m431cpu01/sudo_upload.log'
    value = log.read_text(encoding='utf-8-sig')
    assert '__M431_BOOT_SUDO_RC_1__' in value and 'a password is required' in value and 'ubuntu@kria:~$' in value
    assert not (ROOT / 'tmp/m431cpu01/absence.log').exists()
    assert not list((ROOT / 'tmp/m431cpu01').glob('upload_*'))
    host = (HERE / 'm431_cpu_host.py').read_text(encoding='utf-8')
    old, new = "FOLDER=ROOT/'tmp/m431cpu01'", "FOLDER=ROOT/'tmp/m431cpu02'"
    assert host.count(old) == 1
    revised = host.replace(old, new)
    assert revised.replace(new, old) == host
    atomic(HERE / 'm431_cpu_host02.py', revised.encode('utf-8'), immutable=True)
    control = (HERE / 'm431_cpu_control.ps1').read_text(encoding='utf-8')
    revised = control.replace("$folder='tmp/m431cpu01'", "$folder='tmp/m431cpu02'").replace("'m431_cpu_host.py'", "'m431_cpu_host02.py'")
    guard = """Evidence 'latest_m431_CPU_authorization_precheck'
$auth=Get-Content (Join-Path $workspace $board.latest_m431_CPU_authorization_precheck.result) -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($p in $auth.resume_source_sha256.PSObject.Properties) {
    if ((Get-FileHash (Join-Path $PSScriptRoot $p.Name) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $p.Value) { throw 'Resume source changed' }
}
"""
    anchor = "if ($Mode -eq 'Upload') {"
    assert revised.count(anchor) == 1
    revised = revised.replace(anchor, guard + anchor)
    atomic(HERE / 'm431_cpu_control02.ps1', revised.encode('utf-8'), immutable=True)
    pwsh = 'C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe'
    cp = subprocess.run([pwsh, '-NoProfile', '-File', str(HERE / 'm431_cpu_control02.ps1'), '-Mode', 'SelfTest'], capture_output=True)
    atomic(ROOT / 'tmp/m431cpu02/control_stdout.bin', cp.stdout, immutable=True)
    atomic(ROOT / 'tmp/m431cpu02/control_stderr.bin', cp.stderr, immutable=True)
    assert cp.returncode == 0 and b'M431_BOOTSTRAP_CONTROL_PASS' in cp.stdout
    m = json.loads((PKG / 'PACKAGE_MANIFEST.json').read_bytes())
    final = dict(status='FROZEN_M431_BORROWED_CPU_FINAL_PACKET', manifest_sha256=sha(PKG / 'PACKAGE_MANIFEST.json'),
                 file_count=m['file_count'], total_bytes=m['total_bytes'], full286_geometry_component_pass=True,
                 actual_export_host_support_pass=True, board_uploaded=False,
                 original_draft01_preserved=True, temperature_measurement_enabled=False, performance_pass=False)
    packet = BASE / 'runs/M431-borrowed-CPU-packet-final-02/RESULT.json'
    atomic(packet, encoded(final), immutable=True)
    sync('latest_m431_borrowed_CPU_packet', dict(status=final['status'], result=packet.relative_to(ROOT).as_posix(), sha256=sha(packet), manifest_sha256=final['manifest_sha256']),
         f'## M431 借用DMA CPU小包最终冻结（2026-10-06）\n\nSHA {sha(packet)}，manifest {final["manifest_sha256"]}；{m["file_count"]}载荷/{m["total_bytes"]}B。02真实-I组件、完整286批/22暂存和实际export→host/控制门禁已过；01未执行稿及离线暂存失败保留。尚未上传/上板，不证明完整runtime容量/硬件数值/完整请求性能，不测温。')
    r = dict(status='M431_WAIT_SAME_COM3_SUDO_RENEWAL_NO_UPLOAD', manifest_sha256=final['manifest_sha256'],
             shell_confirmed=True, sudo_return_code=1, log='tmp/m431cpu01/sudo_upload.log', log_sha256=sha(log),
             packet_absence_not_queried=True, upload_started=False, CPU_fixture_started=False, Overlay_loads=0, model_forward_calls=0,
             original_host_support_sources_preserved={n: sha(HERE / n) for n in ('m431_cpu_host.py', 'm431_cpu_control.ps1', 'm431_cpu_host_prepare.py')},
             resume_source_sha256={n: sha(HERE / n) for n in ('m431_cpu_host02.py', 'm431_cpu_control02.ps1')},
             resume_equivalence='Host02 only changes transfer receipt folder. Control02 changes only fresh receipt/host paths and adds exact resume-source guard; packet, checker, decoder and output path unchanged.',
             next_step='After fresh manual same-COM3 shell/sudo confirmation, directly Upload then Run m431_cpu_control02.ps1. CPU-only synthetic DMA fixture; no real model or Overlay. Existing saved attempt permits Collect only.')
    out = BASE / 'runs/M431-CPU-authorization-precheck-01/RESULT.json'
    atomic(out, encoded(r), immutable=True)
    sync('latest_m431_CPU_authorization_precheck', dict(status=r['status'], result=out.relative_to(ROOT).as_posix(), sha256=sha(out), manifest_sha256=r['manifest_sha256']),
         f'## M431 CPU小包授权阻塞（2026-10-06）\n\nSHA {sha(out)}。COM3 shell已确认，sudo rc1需要密码；0查询packet/上传/运行/Overlay/模型。M430完整视觉净收益7.686577%与资源恢复已闭合；M431仅下一完整请求接入前CPU组件，尚未上板。原日志/支持源码同SHA保留，02恢复控制SelfTest通过，只改新回执路径并核SHA。等待人工续期后直接Upload/Run，不重复阻塞探测，不测温。')
    print('M431_CPU_AUTHORIZATION_SYNC', sha(out))


if __name__ == '__main__':
    main()
