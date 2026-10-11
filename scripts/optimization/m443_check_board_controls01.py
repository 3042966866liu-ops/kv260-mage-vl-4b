"""Freeze actual offline lower-control and bounded transfer checks; zero board."""
import json,subprocess,sys
from pathlib import Path
import m351_workflow as w
from m441_host_io08 import atomic
RUN=w.BASE/'runs/M443-board-controls-checks-01'
OUT=w.ROOT/'tmp/m443_board_controls_01'
def main():
    assert not RUN.exists(),'Existing checks; inspect only'
    prep=w.BASE/'runs/M443-board-controls-preparation-01/RESULT.json';p=json.loads(prep.read_bytes())
    for row in p['files']:assert w.sha(w.ROOT/row['path'])==row['sha256']
    for row in p['files']:
        q=w.ROOT/row['path']
        assert w.sha(w.HERE/q.name)==row['sha256'],'Actual host control differs'
    extra=[]
    for name in ('test_m357_transfer.py','test_m357_transfer_collection.py'):
        source=(w.HERE/name).read_text(encoding='utf-8').replace('m357','m443').replace('M357','M443')
        source=source.replace('tempfile.TemporaryDirectory()', "tempfile.TemporaryDirectory(dir=str(Path(__file__).resolve().parents[2]/'tmp'))")
        target=w.HERE/name.replace('m357','m443');assert not target.exists()
        atomic(target,source.encode(),immutable=True);extra.append(target)
    commands=[
        [sys.executable,'-B','-X','utf8',str(w.HERE/'test_m443_board_controls01.py')],
        ['C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe','-NoLogo','-NoProfile','-File',str(w.HERE/'m443_control01.ps1'),'-Mode','SelfTest'],
        *[[sys.executable,'-B','-X','utf8',str(x)] for x in extra]]
    results=[]
    for i,cmd in enumerate(commands):
        r=subprocess.run(cmd,cwd=w.ROOT,capture_output=True,timeout=60)
        stdout=RUN/f'check{i}.stdout.txt';stderr=RUN/f'check{i}.stderr.txt'
        atomic(stdout,r.stdout,immutable=True);atomic(stderr,r.stderr,immutable=True)
        results.append(dict(command=cmd,rc=r.returncode,stdout_path=stdout.relative_to(w.ROOT).as_posix(),stdout_sha256=w.sha(stdout),stderr_path=stderr.relative_to(w.ROOT).as_posix(),stderr_sha256=w.sha(stderr)))
    ok=all(x['rc']==0 for x in results)
    files=p['files']+[dict(path=x.relative_to(w.ROOT).as_posix(),sha256=w.sha(x)) for x in extra+[w.HERE/'test_m443_board_controls01.py',Path(__file__)]]
    result=dict(status='PASS_M443_ACTUAL_LOWER_CONTROL_AND_TRANSFER_FIXTURES01' if ok else 'FAIL_M443_LOWER_CONTROL_FIXTURES01',build_id='0x4D343433',preparation_sha256=w.sha(prep),
        checks=results,files=files,board=False,hardware_package=False,configuration_application_accepted=False,configuration_credits_granted=0,
        actual_control_modules=True,explicit_fake_device_and_trace_fixtures=True,actual_local_socket_framing=True,fake_network_cleanup=True,
        limitations='18 unittest methods including inherited guard checks, six unknown-configuration branches and 13 collector mutations; transport fixtures and PowerShell failure collection. All traces, MMIO and CMA counter inputs here are explicit CPU fixtures, not new-bit board proof.',
        next_step='Clean whitelist package with recursive Python dependency closure, then COM3 authorized bounded transport and BuildID actual exact-bit samePID/PFN configuration observation.')
    atomic(RUN/'RESULT.json',w.encoded(result),immutable=True);w.atomic=atomic;s=w.sha(RUN/'RESULT.json')
    w.sync('latest_m443_board_controls_checks01',dict(status=result['status'],result=(RUN/'RESULT.json').relative_to(w.ROOT).as_posix(),sha256=s,board=False,build_id=result['build_id']),
        '## M443实际控制组件离线正负闭合01（2026-10-11）\n\nSHA '+s+'；'+result['status']+'。实际新配置观察器/probe/采集器/control通过明确fake设备测试；额外/失败CMA分配、缺失释放/PFN不一致/事件丢失/实例未回收保持进程/Overlay/锁且0DMA；活动DMA保留全部buffer；正确完成才恢复原稳定M9；13种采集篡改拒绝。原始stdout/stderr/rc及新传输本地socket与假地址回收留证。全为离线fixture、0新bit配置实证/0credit/0板端。下一步干净白名单及递归依赖打包，指定peer逐SHA传输后先BuildID真实配置申请。')
    print(result['status'],s)
    return 0 if ok else 1
if __name__=='__main__':raise SystemExit(main())
