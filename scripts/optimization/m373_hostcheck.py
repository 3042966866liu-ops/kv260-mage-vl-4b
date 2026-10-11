"""Test new gate/collector orchestration with explicitly fake Linux/root identity."""
import importlib.util
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch
from m373_workflow import PKG, PRIOR, decode, export_fake, PREP
from m351_workflow import ROOT, HERE, BASE, sha, atomic, encoded, sync

def main():
    sys.path.insert(0,str(PKG))
    spec=importlib.util.spec_from_file_location('m373_host_gate',PKG/'m373_component_gate.py')
    gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate)
    manifest=sha(PKG/'PACKAGE_MANIFEST.json')
    with tempfile.TemporaryDirectory(dir=ROOT/'tmp/m373') as directory:
        gate.OUT=Path(directory)/'cpu-gate-success'
        fake_uname=gate.platform.uname()._replace(system='Linux',node='fake-host')
        with patch.object(gate.os,'geteuid',return_value=0,create=True), patch.object(gate.platform,'system',return_value='Linux'), patch.object(gate.platform,'uname',return_value=fake_uname), patch.object(sys,'argv',['gate',manifest,'--enable-fixture-gate']):
            rc=gate.main()
            if rc: raise RuntimeError((gate.OUT/'BOARD_RESULT.json').read_text(encoding='utf-8'))
        row=json.loads((gate.OUT/'BOARD_RESULT.json').read_bytes())
        assert decode(export_fake(row))[2]==row
        negatives=0
        for field,value in [('tests_run',16),('elapsed_s',21),('errors',['fake error']),('blocking_probe',dict(row['blocking_probe'],condition_binding_restored=False)),('lifecycle',dict(active_workers=['fake-active-worker']))]:
            try:decode(export_fake(dict(row,**{field:value})))
            except RuntimeError:negatives+=1
            else:raise AssertionError('Invalid PASS accepted')
        gate.OUT=Path(directory)/'cpu-gate-failure'
        with patch.object(gate.os,'geteuid',return_value=0,create=True), patch.object(gate.platform,'system',return_value='Linux'), patch.object(sys,'argv',['gate','0'*64,'--enable-fixture-gate']):
            assert gate.main()==1
        failed=json.loads((gate.OUT/'BOARD_RESULT.json').read_bytes())
        assert decode(export_fake(failed))[2]==failed
    auth=ROOT/'tmp/m373/sudo_precheck_02.log'
    assert '__M373_CHECK_SUDO_RC_0__' in auth.read_text(encoding='utf-8-sig')
    result=dict(status='PASS_OFFLINE_NEW_GATE_ORCHESTRATION',prior_raw_sha256=PRIOR,manifest_sha256=manifest,
        fake_linux_and_root_environment=True,host_python=sys.version,not_board_capability=True,
        real_host_future_condition_and_trace=True,adapted_tests=17,valid_pass_collected=True,pass_negative_checks=negatives,
        deliberate_failure_saved_and_collected=True,controller_failure_collection_self_test=True,
        same_terminal_sudo_rc=0,authorization_log_sha256=sha(auth),
        source_sha256={name:sha(HERE/name) for name in ('m373_workflow.py','m373_control.ps1','m373_hostcheck.py')},
        board_gate_started=False,overlay_loaded=False)
    path=BASE/'runs/M373-controller-and-authorization-01/RESULT.json'
    atomic(path,encoded(result),immutable=True);digest=sha(path)
    sync('latest_m373_controller_authorization',dict(status=result['status'],result=path.relative_to(ROOT).as_posix(),sha256=digest),
        f'## M373 新门禁控制与人工续期核对通过（2026-10-03）\n\n用户确认续期后同 COM3 sudo rc0；新控制器故意失败仍回收、收集失败停止与语法检查通过。明确 fake Linux/root 的主机新门禁编排测试：17项、真实 Future/trace 阳性、5项 PASS 拒绝、故意失败原结果保存和收集通过；仅离线编排，非板端能力。证据 {path.relative_to(ROOT).as_posix()} SHA {digest}。下一步上传隔离包，再执行一次无 Overlay 小组件。')
    print('M373_HOST_ORCHESTRATION_AND_AUTHORIZATION_PASS',digest)

if __name__=='__main__':main()
