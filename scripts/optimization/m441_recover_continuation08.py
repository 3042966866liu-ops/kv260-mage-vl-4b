"""Wait existing core once, collect saved outputs, then one authorized shell.
Never restarts core/simulation or changes frozen tools, RTL or constraints.
"""
import argparse
import json
import os
import subprocess
import time
import traceback
from m351_workflow import ROOT, BASE, HERE, encoded, sha
from m441_host_io08 import atomic, observation
from m441_supervisor04 import boot, process, classify, log_snapshot
from m441_boundary_control07 import synchronized

PY = 'C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
PS = 'C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe'
RUN = BASE / 'runs/M441-supervision-recovery-08'
PREP = RUN / 'PREPARATION.json'
OUT = ROOT / 'tmp/m441_record_pipeline_02'
NAMES = ['m441_recover_continuation08.py', 'm441_host_io08.py', 'm441_saved_stage08.py',
         'm441_collect_core_ooc07.py', 'm441_prepare_shell07.py', 'm441_record_hwh07.py',
         'm441_aux_readback07.py', 'm441_collect_shell07.py', 'm441_core_ooc07.py',
         'm441_supervisor04.py', 'm351_workflow.py']


def robust_sync(key, value, note):
    import m351_workflow
    previous = m351_workflow.atomic
    try:
        m351_workflow.atomic = atomic
        m351_workflow.sync(key, value, note)
    finally:
        m351_workflow.atomic = previous


def prepare():
    assert not PREP.exists() and not (RUN / 'START.json').exists()
    recovery_read = {}
    for name in ['CURRENT_STATE.md', 'DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md',
                 'docsMILESTONES.md', 'deployment/mage_vl4b/BOARD_GATE_RESULT.json']:
        path = ROOT / name
        text = path.read_text(encoding='utf-8-sig')
        recovery_read[name] = dict(sha256=sha(path), lines_read=len(text.splitlines()))
    failures = {}
    for name, status, key in [
        ('M441-boundary-core-continuation-07', 'STOP_M441_BOUNDARY_CORE07_AT_FAILED_LEVEL', 'latest_m441_boundary_core_result07'),
        ('M441-shell-continuation-07', 'STOP_M441_SHELL07_AT_FAILED_LEVEL', 'latest_m441_shell_result07')]:
        path = BASE / 'runs' / name / 'RESULT.json'
        result = synchronized(path, status, key)
        failures[name] = dict(path=path.relative_to(ROOT).as_posix(), sha256=sha(path), errors=result['errors'])
    live = json.loads((OUT / 'core_ooc_LIVE.json').read_bytes())
    native = process(live['process']['pid'], live['process']['creation_FILETIME'])
    controller = process(20808, 134359976825687248)
    assert classify(live['start_boot'], boot(), native) == 'RUNNING_IDENTITY_CONFIRMED'
    assert controller['status'] == 'ALIVE'
    assert not (OUT / 'core_ooc_exit.json').exists()
    assert not (ROOT / 'tmp/m441_shell_exit.json').exists()
    assert not (BASE / 'runs/M441-shell-preparation-01/RESULT.json').exists()
    old = BASE / 'runs/M441-shell-continuation-07/PREPARATION.json'
    previous = json.loads(old.read_bytes())
    for row in previous['files']:
        assert sha(ROOT / row['path']) == row['sha256']
    import test_m441_host_io08
    tests = test_m441_host_io08.main()
    checks = RUN / 'HOST_IO_CHECKS.json'
    atomic(checks, encoded(tests), immutable=True)
    result = dict(status='PREPARED_M441_EXISTING_CORE_RECOVERY08', native=native,
                  controller=controller, start_boot=live['start_boot'], failures=failures,
                  recovery_read=recovery_read, original_shell_preparation_sha256=sha(old),
                  original_shell_files=previous['files'],
                  files=[dict(path=(HERE / name).relative_to(ROOT).as_posix(), sha256=sha(HERE / name)) for name in NAMES],
                  host_io_tests_sha256=sha(checks),
                  core_deadline_epoch=live['start_boot']['captured_epoch'] + 8*3600 + 90,
                  shell_budget_s=8*3600, total_budget_s=18*3600,
                  exact_original_failure_operation_proven=False,
                  no_native_restart=True, no_kill=True, board=False, performance=False)
    atomic(PREP, encoded(result), immutable=True)
    robust_sync('latest_m441_supervision_recovery08',
                dict(status=result['status'], sha256=sha(PREP), result=PREP.relative_to(ROOT).as_posix(), board=False),
                f'## M441 原核心监督与收集恢复08准备（2026-10-09）\n\nSHA {sha(PREP)}；原07监督器PermissionError及整壳等待失败保留，原核心及其原控制器PID/出生时间/主机启动核对存活。旧日志无traceback，具体失败I/O尚未证明；7项实际Windows共享锁及明确注入检查通过，新增证据I/O仅5s有界重试、保留traceback。只等原核心退出并收集，禁止重启核心/仿真；核心同约束完整PASS及三记录同步后，仅接续已授权一次8h整壳和严格原07收集，0板端/性能。')
    print(result['status'], sha(PREP), flush=True)


def run():
    p = synchronized(PREP, 'PREPARED_M441_EXISTING_CORE_RECOVERY08', 'latest_m441_supervision_recovery08')
    for row in p['files'] + p['original_shell_files']:
        assert sha(ROOT / row['path']) == row['sha256']
    assert not (RUN / 'RESULT.json').exists()
    # Exclusive creation is the launch lock; never execute this finite sequence twice.
    with (RUN / 'START.json').open('xb') as stream:
        stream.write(encoded(dict(pid=os.getpid(), process=process(os.getpid()), boot=boot(), preparation_sha256=sha(PREP))))
        stream.flush()
        os.fsync(stream.fileno())
    stage = 'waiting_original_core'
    jobs, errors = [], []
    started = time.monotonic()
    def state(**extra):
        atomic(RUN / 'PROGRESS.json', encoded(dict(stage=stage, elapsed_s=time.monotonic()-started, jobs=jobs, **extra)))
    def invoke(name, args, budget):
        nonlocal stage
        stage = name + ' ' + ','.join(args)
        state()
        path = HERE / name
        log = RUN / (str(len(jobs)) + '_' + name + '.log')
        if name.endswith('.ps1'):
            command = [PS, '-NoLogo', '-NoProfile', '-File', str(path), *args]
        else:
            command = [PY, '-B', '-X', 'utf8', str(HERE / 'm441_saved_stage08.py'), name, sha(path), *args]
        with log.open('xb') as stream:
            child = subprocess.Popen(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT,
                                     creationflags=subprocess.CREATE_NO_WINDOW)
            owner = process(child.pid)
            assert owner['status'] == 'ALIVE', owner
            initial = boot()
            at = time.monotonic()
            while child.poll() is None:
                native = process(child.pid, owner['creation_FILETIME'])
                state(owner=native, classification=classify(initial, boot(), native),
                      log=observation(log_snapshot, log))
                if time.monotonic()-at > budget:
                    raise RuntimeError('Stage budget; original child retained, no downstream: ' + str(owner))
                if time.monotonic()-started > p['total_budget_s']:
                    raise RuntimeError('Total budget; original child retained, no downstream')
                time.sleep(10)
        jobs.append(dict(script=name, args=args, original_rc=child.returncode,
                         log=log.relative_to(ROOT).as_posix(), sha256=sha(log)))
        state()
        return child.returncode
    try:
        while True:
            native = process(p['native']['pid'], p['native']['creation_FILETIME'])
            controller = process(p['controller']['pid'], p['controller']['creation_FILETIME'])
            classification = classify(p['start_boot'], boot(), native)
            state(native=native, original_controller=controller, classification=classification,
                  log=observation(log_snapshot, OUT / 'core_ooc_console.log'))
            assert abs(boot()['boot_epoch_estimate'] - p['start_boot']['boot_epoch_estimate']) <= 10, 'Host boot changed'
            assert 'UNPROVEN_QUERY_ERROR' not in [native['status'], controller['status']], 'Process identity query unavailable'
            assert 'PID_REUSED' not in [native['status'], controller['status']], 'Original process identity changed'
            receipt = OUT / 'core_ooc_exit.json'
            if receipt.exists():
                saved = json.loads(receipt.read_bytes())
                assert saved.get('hls_rc') is not None and not saved.get('process_retained'), saved
                if native['status'] != 'ALIVE' and controller['status'] != 'ALIVE':
                    break
            elif controller['status'] != 'ALIVE':
                raise RuntimeError('Original core controller ended without native exit receipt; collect only, no restart')
            if time.time() > p['core_deadline_epoch']:
                raise RuntimeError('Original core budget reached; retain processes, no downstream')
            time.sleep(30)
        assert invoke('m441_collect_core_ooc07.py', [], 600) == 0, 'Original core collector rejected'
        core = synchronized(BASE / 'runs/M441-record-pipeline-core-OOC-closure-01/RESULT.json',
                            'PASS_M441_SAME_CONSTRAINT_CORE_ROUTED_TIMING', 'latest_m441_record_pipeline_core_OOC')
        assert all(core['checks'].values()) and core['original_rc'] == 0
        assert invoke('m441_prepare_shell07.py', [], 600) == 0, 'Shell preparation rejected'
        controls = synchronized(BASE / 'runs/M441-shell-control-preparation-07/RESULT.json',
                                'PREPARED_M441_FROZEN_SHELL_CONTROLS', 'latest_m441_shell_control_preparation07')
        assert sha(HERE / 'm441_build_shell.tcl') == controls['Tcl_sha256']
        assert sha(HERE / 'm441_run_shell.ps1') == controls['controller_sha256']
        assert invoke('m441_run_shell.ps1', ['-Run'], p['shell_budget_s']) == 0, 'Original shell tool rejected'
        assert (ROOT / 'tmp/m441_shell_exit.json').exists(), 'Missing native shell exit receipt'
        assert invoke('m441_record_hwh07.py', [], 600) == 0, 'HWH ABI rejected'
        assert invoke('m441_aux_readback07.py', ['prepare'], 600) == 0, 'Auxiliary input classification rejected'
        rc = invoke('m441_aux_readback07.py', ['run', '--run'], 650)
        closed = invoke('m441_aux_readback07.py', ['collect'], 600)
        assert rc == 0 and closed == 0, 'Auxiliary readback rejected'
        assert invoke('m441_collect_shell07.py', [], 600) == 0, 'Shell closure rejected'
        stage = 'complete_shell_board_pending'
    except Exception as exc:
        errors.append(dict(error=repr(exc), traceback=traceback.format_exc(),
                           filename=getattr(exc, 'filename', None), winerror=getattr(exc, 'winerror', None)))
    result = dict(status='PASS_M441_RECOVERED_CORE_AND_SHELL08' if not errors else 'STOP_M441_RECOVERY08_AT_FAILED_LEVEL',
                  last_stage=stage, errors=errors, jobs=jobs, preparation_sha256=sha(PREP),
                  elapsed_s=time.monotonic()-started, no_native_restart=True, no_kill=True,
                  board=False, performance=False, promotion=False)
    path = RUN / 'RESULT.json'
    atomic(path, encoded(result), immutable=True)
    robust_sync('latest_m441_supervision_result08',
                dict(status=result['status'], sha256=sha(path), result=path.relative_to(ROOT).as_posix(), board=False),
                f'## M441 原核心监督恢复08末态（2026-10-09）\n\nSHA {sha(path)}；{result["status"]}，末级{stage}。原07失败保持，未重启核心/仿真；实际子返回值与新完整traceback见原结果。0板端/性能/晋级。失败仅处理当前级，PASS后才准备板端固定顺序门禁。')
    print(result['status'], sha(path), flush=True)
    return int(bool(errors))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['Prepare', 'Run'])
    parser.add_argument('--enable', action='store_true')
    args = parser.parse_args()
    if args.mode == 'Prepare':
        prepare()
    else:
        assert args.enable, 'Default disabled'
        raise SystemExit(run())
