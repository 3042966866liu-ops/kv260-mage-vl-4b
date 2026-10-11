"""Actual exporter/save/collector/receipt paths with explicitly synthetic data."""
import contextlib
import copy
import hashlib
import importlib.util
import io
import json
import re
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import numpy as np
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
from m408_mlp_capture import SHAPES
import m408_workflow03 as workflow


def main():
    b = json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    prep = b['latest_m408_local_mlp_preparation03']; assert sha(ROOT/prep['result']) == prep['sha256']
    pkg = workflow.PKG; digest = sha(pkg/'PACKAGE_MANIFEST.json'); assert digest == prep['manifest_sha256']
    manifest = json.loads((pkg/'PACKAGE_MANIFEST.json').read_bytes())
    for row in manifest['files']: assert sha(pkg/row['path']) == row['sha256']
    temp_root = ROOT/'tmp/m40803/support'; temp_root.mkdir(parents=True,exist_ok=True)
    rejects = 0
    with tempfile.TemporaryDirectory(dir=temp_root) as temporary:
        folder = ROOT/temporary
        spec = importlib.util.spec_from_file_location('m408_actual_producer_fixture',pkg/'m408_gate.py')
        producer = importlib.util.module_from_spec(spec); spec.loader.exec_module(producer)
        producer.OUTPUT = folder/'capture/RESULT.json'
        producer.os = SimpleNamespace(geteuid=lambda:0,fsync=__import__('os').fsync,replace=__import__('os').replace)
        producer.time = SimpleNamespace(sleep=lambda seconds:None)
        original = sys.argv; sys.argv = ['m408_gate.py']
        try:
            try: producer.main()
            except RuntimeError as error: assert 'Default-off' in str(error)
            else: raise AssertionError('Default-off failed')
        finally: sys.argv = original
        producer.OUTPUT.parent.mkdir()
        # Actual bounded NPY saving and whole file/tensor identities, with self-owned synthetic arrays.
        values = {k:np.ones(shape,np.float32) for k,shape in SHAPES.items()}
        capture = producer.save_arrays(values)
        assert len(capture['files']) == 6 and sha(producer.OUTPUT.parent/'CAPTURE_MANIFEST.json') == capture['sha256']
        for row in capture['files']:
            path = producer.OUTPUT.parent/row['path']
            assert sha(path) == row['file_sha256'] and producer.tensor(np.load(path,allow_pickle=False)) == row['tensor']
        capture['path'] = '/home/ubuntu/m408_mlp_capture_03/CAPTURE_MANIFEST.json'
        expected = json.loads((pkg/'EXPECTED.json').read_bytes())
        bad = dict(status='FAIL_M408_PS_LOCAL_MLP_CAPTURE_A8_SCREEN',gate_return_code=1,
            errors=[dict(message='EXPLICIT SYNTHETIC early FAIL')],
            gate_level='PS-only-real-input-local-MLP-A8-rejection-screen',manifest_sha256=digest,selected_layer=12,
            overlay_loaded=False,cache_policy_changed=False,thread_settings_changed=False,
            PL_arithmetic_proven=False,semantic_quality_proven=False,performance_pass=False,formal_promotion_allowed=False,
            dma_allocations=0,fpga_transactions=0,language_forward_calls=0,local_A8_screen_pass=False)
        quality = {k:dict(cosine=1.,relative_l2=0.,min_token_cosine=1.,RMSE=0.,max_abs=0.,shape=list(SHAPES.get(k,(392,1024))))
                   for k in ('fc1','gelu','fc2','output','residual_sum')}
        backend = dict(settings_changed=False,explicit_synthetic_fixture=True)
        batches = {k:[dict(start=s,rows=min(32,392-s),shift=0,clipped=0) for s in range(0,392,32)] for k in ('input','gelu')}
        good = dict(bad,status='PASS_M408_PS_LOCAL_MLP_CAPTURE_A8_SCREEN',gate_return_code=0,errors=[],
            visual_forward_calls=1,local_mlp_forward_calls=2,component_pass=True,capture_exact=True,
            local_A8_screen_pass=True,bindings_restored=True,visual_owner_closed=True,no_pynq_import=True,
            visual=expected['visual'],preprocessed=expected['preprocessed'],backend_before=backend,backend_after=backend,
            component=dict(real_torch_CPU=True,actual_M207_class=True,exception_and_duplicate_restoration=True,
                           original_hooks_restored=True,rejects=5,full_392_T32_geometry=True,explicit_synthetic_fixture=True),
            quality_metrics=quality,A8_batches=batches,capture={k:producer.tensor(v) for k,v in values.items()},
            capture_manifest=capture,elapsed_s_diagnostic_not_performance=1,
            target_component=dict(actual_frozen_wrappers_and_encoder_forward=True,original_capture_bit_exact=True,hooks_restored=True,topology_rejects=4,target_path='encoder.layers.12.layer.layer',topology=json.loads((pkg/'EXPECTED_TARGET.json').read_bytes())['topology']),target_resolution=json.loads((pkg/'EXPECTED_TARGET.json').read_bytes())['topology'],target_matrices=json.loads((pkg/'EXPECTED_TARGET.json').read_bytes())['matrices'])
        def export(value):
            producer.OUTPUT.write_bytes(encoded(value))
            stream = io.StringIO()
            with contextlib.redirect_stdout(stream): producer.export()
            return stream.getvalue()+f'M408_DONE gate_rc={value["gate_return_code"]} export_rc=0\n'
        complete = export(good)
        assert workflow.decode(complete)[2] == good and workflow.decode(export(bad))[2] == bad
        mutations = []
        for key,value in [('manifest_sha256','0'*64),('visual_forward_calls',2),('local_mlp_forward_calls',3),
            ('bindings_restored',False),('visual_owner_closed',False),('capture_exact',False),('fpga_transactions',1),
            ('performance_pass',True),('semantic_quality_proven',True),('PL_arithmetic_proven',True),
            ('selected_layer',11),('local_A8_screen_pass',False),('elapsed_s_diagnostic_not_performance',601)]:
            obj = copy.deepcopy(good); obj[key] = value; mutations.append(export(obj))
        obj = copy.deepcopy(good); obj['quality_metrics']['fc2']['relative_l2'] = .03; mutations.append(export(obj))
        obj = copy.deepcopy(good); obj['A8_batches']['input'][-1]['rows'] = 32; mutations.append(export(obj))
        obj = copy.deepcopy(good); obj['capture_manifest']['files'][0]['tensor']['shape'] = [1]; mutations.append(export(obj))
        mutations += [complete+complete,complete.replace('M408_RESULT_CHUNK=1/','M408_RESULT_CHUNK=0/'),
            re.sub(r'(?m)^M408_RESULT_CHUNK=1/.*\n','',complete),complete.replace('export_rc=0','export_rc=1'),
            complete.replace('gate_rc=0','gate_rc=1'),complete.replace('M408_RESULT_SHA256=','M408_RESULT_SHA256=0')]
        for text in mutations:
            try: workflow.decode(text)
            except (ValueError,KeyError): rejects += 1
            else: raise AssertionError('Invalid result accepted')
        log = folder/'saved.log'; log.write_text(complete,encoding='utf-8')
        calls = []; out = folder/'collected/BOARD_RESULT.json'
        workflow.collect(log,out=out,sync_function=lambda *args:calls.append(args))
        assert out.read_bytes() == encoded(good) and len(calls) == 1 and calls[0][0] == 'latest_m408_local_mlp_board03'
        assert out.with_name('REPORT.md').exists()
        try: atomic(out,encoded(bad),immutable=True)
        except RuntimeError: pass
        else: raise AssertionError('Immutable evidence overwritten')
        for name in ['PACKAGE_MANIFEST.json']+[r['path'] for r in manifest['files']]:
            prefix = 'upload_'+name.replace('.','_'); size = (pkg/name).stat().st_size; count = (size+899)//900
            (folder/(prefix+'_final.log')).write_text('M212_CHUNKED_FILE_PASS '+sha(pkg/name),encoding='utf-8')
            for i in range(1,count+1):
                (folder/f'{prefix}_chunk_{i:03}.log').write_text(f'M212_CHUNK_PASS {i} {count} {min(i*900,size)} EXPLICIT_SYNTHETIC\n',encoding='utf-8')
        (folder/'syntax.log').write_text('__M408_SYNTAX_RC_0__',encoding='utf-8')
        receipts = workflow.transfer(folder=folder,save=False)
        assert len(receipts['files']) == manifest['file_count']+1
        next(folder.glob('upload_*_chunk_001.log')).unlink()
        try: workflow.transfer(folder=folder,save=False)
        except RuntimeError: pass
        else: raise AssertionError('Missing transfer receipt accepted')
    ps = 'C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe'
    subprocess.run([ps,'-NoProfile','-File',str(HERE/'m408_control04.ps1'),'-Mode','SelfTest'],check=True)
    control = (HERE/'m408_control04.ps1').read_text(encoding='utf-8')
    assert control.index('catch { $gateError=$_ }',control.index("if ($Mode -ne 'Run')")) < control.index("$workflow collect 'tmp/m40803/run.log'")
    assert 'Original run exists; Collect only' in control and '$LASTEXITCODE -ne 0' in control
    r = dict(status='PASS_M408_ACTUAL_CONTROL_COLLECTION_SUPPORT',manifest_sha256=digest,
        actual_NPY_save_file_tensor_SHA=True,actual_export_early_FAIL_and_full_PASS=True,
        collector_negative_checks=rejects,actual_atomic_destination_and_BOARD_key=True,immutable=True,
        manifest_first_all_file_chunk_receipts=True,missing_transfer_receipt_rejected=True,
        default_off_and_control_failure_collect=True,all_data_explicit_synthetic_not_target_model=True,
        source_sha256={n:sha(HERE/n) for n in ('m408_support03.py','m408_workflow03.py','m408_control04.ps1')},
        new_board_run=False,performance_pass=False)
    out = BASE/'runs/M408-local-MLP-support-03/RESULT.json'; atomic(out,encoded(r),immutable=True)
    sync('latest_m408_local_mlp_support03',dict(status=r['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out),manifest_sha256=digest),
        f'## M408 实际捕获/控制/回收配套检查（2026-10-05）\n\nSHA {sha(out)}；实际有界NPY/file/tensor SHA保存、producer早期FAIL/完整PASS、'
        f'{rejects}回收拒绝、原子保存目标/BOARD键/immutable、全部manifest-first/900B假回执及缺失拒绝、默认关闭/故意失败仍收集通过。'
        '全部明确自有合成数据，不证明目标模型或PL。下一步同COM3授权后一次纯PS真实捕获及局部A8筛选；尚无质量/性能PASS。')
    print('M408_SUPPORT_PASS',sha(out),rejects)


if __name__ == '__main__': main()
