"""Freeze host CPU-only control/collector and test the actual exporter."""
import ast, base64, contextlib, copy, hashlib, importlib.util, io, json, subprocess, tempfile
from unittest.mock import patch
from m351_workflow import ROOT, BASE, HERE, atomic, encoded, sha, sync
from m431_cpu_finalize import PKG


def generate():
    source = (HERE / 'm429_bootstrap_host.py').read_text(encoding='utf-8').split('def prepare():', 1)[0]
    source = source.replace('M429-isolated-bootstrap-03', 'M431-borrowed-late11-CPU-02').replace('M429-isolated-bootstrap-board-01', 'M431-borrowed-CPU-board-01')
    source = source.replace('M429-isolated-bootstrap-transfer-01', 'M431-borrowed-CPU-transfer-01').replace('tmp/m429bootstrap01', 'tmp/m431cpu01')
    source = source.replace('M429', 'M431').replace('latest_m429_isolated_bootstrap', 'latest_m431_borrowed_CPU')
    old = "    if c['complete_wire_batches']!=286 or len(c['negative_checks'])!=20 or not c['restored'] or not c['fake_PL_submit'] or not c['no_DMA_or_Overlay'] or r['elapsed_s']>210:raise ValueError('Bounded actual CPU fixture incomplete')"
    assert source.count(old) == 1
    new = """    if r['elapsed_s']>210 or not all(k in r for k in ('child_stdout','child_stderr')):raise ValueError('Bounded child evidence absent')
    if not b['numpy_path'].startswith(b['release']+'/runtime_site/numpy/'):raise ValueError('Frozen NumPy path differs')
    w=c['window'];n=c['negative']
    required=dict(complete_batches=286,staged_windows=22,staged_bytes=49020928,fake_original_buffer_bytes=33484832,alternating_outputs=[143,143],extra_DMA_allocate_or_free_calls=0)
    if any(w.get(k)!=v for k,v in required.items()):raise ValueError('Complete geometry/ownership fixture differs')
    for k in ('full286_original_geometry_and_saved_shifts','fake_DMA_MMIO_policy_and_byte_content','original_buffer_identities_unchanged','static_cache_invalidated','all_fixture_files_released'):
        if w.get(k) is not True:raise ValueError('Window fixture scope differs')
    if w['actual_PL_numerics_or_complete_runtime_capacity_proven'] is not False or n['actual_PL_or_capacity_proven'] is not False or n['extra_allocate_or_free_calls']!=0 or n['real_array_geometry_bytes']!=33484832 or len(n['negative_checks'])!=15 or not n['fake_DMA_MMIO_memory'] or not n['timeout_preserves_original_owner'] or not n['static_cache_invalidated']:raise ValueError('Fake scope/negative ownership incomplete')
"""
    source = source.replace(old, new.rstrip())
    start = source.index("    rows=r['original_child_files']")
    end = source.index('    return r', start)
    source = source[:start] + source[end:]
    source = source.replace('原失败child字节独立SHA回收，新-I显式冻结runtime_site。通过仅允许新版本继续原视觉数值级，不是硬件/质量/性能PASS。', '实际-I冻结runtime_site NumPy几何、286批/22暂存及15拒绝，DMA/MMIO明确fake；不是完整runtime容量、硬件数值或性能PASS。下一步隔离完整请求接入数值，不自动执行性能。')
    source += "\nif __name__=='__main__':\n    import sys\n    if sys.argv[1:]==['transfer']:transfer()\n    elif len(sys.argv)==3 and sys.argv[1]=='collect':collect(sys.argv[2])\n    else:raise SystemExit('transfer | collect LOG')\n"
    atomic(HERE / 'm431_cpu_host.py', source.encode('utf-8'), immutable=True)
    control = (HERE / 'm429_bootstrap_control.ps1').read_text(encoding='utf-8')
    replacements = {'M429-isolated-bootstrap-03': 'M431-borrowed-late11-CPU-02', '/home/ubuntu/m429_isolated_bootstrap_03': '/home/ubuntu/m431_borrowed_CPU_candidate_02',
                    'm429_bootstrap_host.py': 'm431_cpu_host.py', 'tmp/m429bootstrap01': 'tmp/m431cpu01', 'run_bootstrap.sh': 'run_cpu.sh',
                    'M429-isolated-bootstrap-board-01': 'M431-borrowed-CPU-board-01',
                    'latest_m429_late11_visual_numerical_closure': 'latest_m430_complete_visual_closure',
                    'latest_m429_isolated_bootstrap_support': 'latest_m431_borrowed_CPU_support',
                    'latest_m429_isolated_bootstrap_transfer': 'latest_m431_borrowed_CPU_transfer'}
    for a, b in replacements.items():
        assert a in control
        control = control.replace(a, b)
    control = control.replace('M429', 'M431')
    anchor = "$support=Get-Content"
    assert control.count(anchor) == 1
    control = control.replace(anchor, "Evidence 'latest_m431_isolated_packet_component'\nif (-not $board.latest_m430_complete_visual_closure.performance_pass) { throw 'Visual performance prerequisite failed' }\n" + anchor)
    atomic(HERE / 'm431_cpu_control.ps1', control.encode('utf-8'), immutable=True)
    print('M431_CPU_HOST_CONTROL_FROZEN')


def support():
    import m431_cpu_host as host
    for row in json.loads((PKG / 'PACKAGE_MANIFEST.json').read_bytes())['files']:
        assert sha(PKG / row['path']) == row['sha256']
    spec = importlib.util.spec_from_file_location('actual_m431_export', PKG / 'm431_cpu.py')
    export = importlib.util.module_from_spec(spec); spec.loader.exec_module(export)
    component = json.loads((BASE / 'runs/M431-isolated-packet-component-02/RESULT.json').read_bytes())['component']
    plan = json.loads((PKG / 'PLAN.json').read_bytes())
    def file(name, value):
        return dict(path=name, bytes=len(value), sha256=hashlib.sha256(value).hexdigest(), base64=base64.b64encode(value).decode(), identity=[1, 2, len(value), 4, 5, 6, 1])
    good = dict(status='PASS_M431_ISOLATED_CPU_BOOTSTRAP_ONLY', gate_return_code=0, manifest_sha256=sha(PKG / 'PACKAGE_MANIFEST.json'), errors=[],
                overlay_loads=0, DMA_allocations=0, real_model_forward_calls=0, FPGA_transactions=0, temperature_measurement_enabled=False, performance_pass=False,
                source_identities_verified=49, child_return_code=0, elapsed_s=1., component=component,
                bootstrap=dict(isolated=True, release=plan['release'], threads=1, torch_path=plan['release']+'/runtime_site/torch/__init__.py',
                               numpy_path=plan['release']+'/runtime_site/numpy/__init__.py', module_paths=[plan['release']+'/runtime_site']),
                child_stdout=file('synthetic_stdout', b'explicit synthetic child'), child_stderr=file('synthetic_stderr', b''))
    negatives = []
    with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as temporary:
        export.OUTPUT = __import__('pathlib').Path(temporary) / 'BOARD_RESULT.json'
        def emit(value):
            raw = encoded(value); export.OUTPUT.write_bytes(raw); capture = io.StringIO()
            with patch.object(export.os, 'geteuid', lambda: 0, create=True), patch.object(export.time, 'sleep', lambda *a: None), contextlib.redirect_stdout(capture):
                export.emit()
            return capture.getvalue(), raw
        text, raw = emit(good)
        assert host.decode(text)[1] == raw
        failure = copy.deepcopy(good); failure.update(status='FAIL_M431_ISOLATED_CPU_BOOTSTRAP', gate_return_code=1, errors=['Explicit synthetic fixture failure'])
        assert host.decode(emit(failure)[0])[2]['gate_return_code'] == 1
        changes = [('rc-bool', lambda r: r.__setitem__('gate_return_code', False)), ('scope', lambda r: r.__setitem__('DMA_allocations', 1)),
                   ('manifest', lambda r: r.__setitem__('manifest_sha256', '0'*64)), ('thermal', lambda r: r.__setitem__('temperature_measurement_enabled', True)),
                   ('isolation', lambda r: r['bootstrap'].__setitem__('isolated', False)), ('numpy-root', lambda r: r['bootstrap'].__setitem__('numpy_path', '/usr/numpy/__init__.py')),
                   ('geometry', lambda r: r['component']['window'].__setitem__('complete_batches', 285)), ('alternation', lambda r: r['component']['window'].__setitem__('alternating_outputs', [286, 0])),
                   ('fake-scope', lambda r: r['component']['window'].__setitem__('actual_PL_numerics_or_complete_runtime_capacity_proven', True)),
                   ('negative', lambda r: r['component']['negative']['negative_checks'].pop()), ('child-SHA', lambda r: r['child_stdout'].__setitem__('sha256', '0'*64))]
        for name, change in changes:
            r = copy.deepcopy(good); change(r)
            try: host.decode(emit(r)[0])
            except (ValueError, RuntimeError): negatives.append(name)
            else: raise AssertionError('Invalid accepted '+name)
        for name, invalid in [('missing', text.replace('M431_BOOT_RESULT_CHUNK=0/', 'REMOVED=0/')), ('duplicate', text+text), ('order', text.replace('M431_BOOT_RESULT_CHUNK=1/', 'M431_BOOT_RESULT_CHUNK=0/'))]:
            try: host.decode(invalid)
            except ValueError: negatives.append(name)
            else: raise AssertionError(name)
    pwsh = 'C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe'
    cp = subprocess.run([pwsh, '-NoProfile', '-File', str(HERE / 'm431_cpu_control.ps1'), '-Mode', 'SelfTest'], capture_output=True)
    atomic(ROOT / 'tmp/m431cpu01/control_stdout.bin', cp.stdout, immutable=True); atomic(ROOT / 'tmp/m431cpu01/control_stderr.bin', cp.stderr, immutable=True)
    assert cp.returncode == 0 and b'M431_BOOTSTRAP_CONTROL_PASS' in cp.stdout
    cp = subprocess.run(['wsl.exe', '-d', 'Ubuntu-24.04', '--', '/bin/bash', '-n', '/mnt/c/Users/30429/Desktop/TeLLMe_FPGA_2026/deployment/mage_vl4b/optimization_v1/candidates/M431-borrowed-late11-CPU-02/run_cpu.sh'], capture_output=True)
    atomic(ROOT / 'tmp/m431cpu01/bash_stdout.bin', cp.stdout, immutable=True); atomic(ROOT / 'tmp/m431cpu01/bash_stderr.bin', cp.stderr, immutable=True)
    assert cp.returncode == 0
    for name in ('m431_cpu_host.py', 'm431_cpu_host_prepare.py'):
        ast.parse((HERE / name).read_text(encoding='utf-8'), feature_version=(3, 10))
    result = dict(status='PASS_M431_ACTUAL_CPU_EXPORT_HOST_CONTROL_SUPPORT', manifest_sha256=sha(PKG / 'PACKAGE_MANIFEST.json'),
                  actual_export_to_host_PASS_FAIL=True, negative_checks=negatives, explicit_synthetic_root_and_backend=True,
                  control_intentional_failure_collect=True, bash_n=True,
                  source_sha256={name: sha(HERE / name) for name in ('m431_cpu_host.py', 'm431_cpu_control.ps1', 'm431_cpu_host_prepare.py')},
                  board_run=False, performance_pass=False, temperature_measurement_enabled=False)
    out = BASE / 'runs/M431-CPU-export-host-support-01/RESULT.json'
    atomic(out, encoded(result), immutable=True)
    sync('latest_m431_borrowed_CPU_support', dict(status=result['status'], result=out.relative_to(ROOT).as_posix(), sha256=sha(out), manifest_sha256=result['manifest_sha256']),
         f'## M431 实际CPU导出与回收支持（2026-10-06）\n\nSHA {sha(out)}，实际export→host PASS/FAIL原字节及{len(negatives)}拒绝、控制故意失败收集/bash-n/Python3.10通过。root/后端receipt明确synthetic，仅收集器支持；02包尚未上传，下一步COM3一次sudo后CPU几何组件。不测温，不宣称完整请求数值或性能。')
    print('M431_CPU_SUPPORT_SYNC', sha(out))


if __name__ == '__main__':
    import sys
    if sys.argv[1:] == ['generate']:
        generate()
    elif sys.argv[1:] == ['support']:
        support()
    else:
        raise SystemExit('generate | support')
