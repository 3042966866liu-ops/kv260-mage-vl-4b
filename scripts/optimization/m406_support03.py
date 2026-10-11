"""Exercise the actual exporter/collector/receipt paths using explicit fixtures."""
import base64
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
from m351_workflow import ROOT, BASE, HERE, atomic, encoded, sha, sync
from m406_revision_prepare import PKG
import m406_workflow02 as workflow


def main():
    board = json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    prep = board['latest_m406_vision_observer_preparation']
    assert sha(ROOT/prep['result']) == prep['sha256']
    assert sha(PKG/'PACKAGE_MANIFEST.json') == prep['manifest_sha256']
    manifest = json.loads((PKG/'PACKAGE_MANIFEST.json').read_bytes())
    for row in manifest['files']:
        assert sha(PKG/row['path']) == row['sha256']
    temp_root=ROOT/'tmp/m40602/support';temp_root.mkdir(parents=True,exist_ok=True)
    negatives=0
    with tempfile.TemporaryDirectory(dir=temp_root) as temporary:
        folder=ROOT/temporary
        spec=importlib.util.spec_from_file_location('m406_fixture_gate',PKG/'m406_vision_gate.py')
        producer=importlib.util.module_from_spec(spec);spec.loader.exec_module(producer)
        producer.OUTPUT=folder/'producer/RESULT.json'
        producer.os=SimpleNamespace(geteuid=lambda:0)
        producer.time=SimpleNamespace(sleep=lambda value:None)
        source_sysargv=sys.argv
        sys.argv=['gate.py']
        try:
            try:producer.main()
            except RuntimeError as error:assert 'disabled by default' in str(error)
            else:raise AssertionError('Default-off failed')
        finally:sys.argv=source_sysargv
        expected=json.loads((PKG/'EXPECTED.json').read_bytes())['visual']
        baseline=dict(status='FAIL_PS_VISUAL_COST_OBSERVATION',gate_return_code=1,
            errors=[dict(message='intentional explicit fixture failure')],
            gate_level='PS-only-fixed-input-visual-cost-observation',manifest_sha256=prep['manifest_sha256'],
            overlay_loaded=False,cache_policy_changed=False,thread_settings_changed=False,
            performance_pass=False,formal_promotion_allowed=False,dma_allocations=0,
            language_forward_calls=0,fpga_transactions=0,numerical_pass=False)
        names=[f'encoder.layers.{i}.{kind}' for i in range(24) for kind in ('self_attn.qkv','self_attn.proj','mlp.fc1','mlp.fc2')]+['merger.mlp.0','merger.mlp.2']
        rows=[dict(name=n,category='linear_gemm',calls=1,inclusive_ns=1000000,exclusive_ns=1000000,process_cpu_ns=1000000) for n in names]
        rows+=[dict(name=f'layer{i}',category='encoder_layer_other',calls=1,inclusive_ns=1000000,exclusive_ns=1000000,process_cpu_ns=1000000) for i in range(24)]
        rows+=[dict(name='root',category='vision_total',calls=1,inclusive_ns=123000000,exclusive_ns=1000000,process_cpu_ns=123000000)]
        backend=dict(settings_changed=False,torch_version='EXPLICIT_FAKE',intraop_threads=4)
        before=dict(decode_calls=98,cache_hits=0,cache_misses=26,uncached_decode_calls=72,cache_bytes=66699264)
        after=dict(decode_calls=196,cache_hits=26,cache_misses=26,uncached_decode_calls=144,cache_bytes=66699264)
        good=dict(baseline,status='PASS_PS_VISUAL_COST_OBSERVATION',gate_return_code=0,errors=[],
            visual_forward_calls=2,numerical_pass=True,component_pass=True,bindings_restored=True,
            visual_owner_closed=True,no_pynq_import=True,visual=expected,backend_before=backend,backend_after=backend,
            component=dict(real_torch_fixture_cases=[{'explicit_fake':True}]*8,exception_propagated=True,bindings_restored=True),
            cpu_observation=dict(worker_joined=True,intervals=[{'explicit_fake':True}]),
            costs=dict(rows=rows,exclusive_sum_ns=123000000,vision_wall_ns=123000000,
                       gemm_windows=[dict(name='fake',start_ns=0,end_ns=1000000,process_cpu_ns=1000000)]),
            before_cache=before,after_cache=after,elapsed_s_diagnostic_not_performance=1,
            native_cpu_operators=[dict(name='FAKE_aten::mm',calls=98)],attention_implementations=['explicit_fake'])
        def export(value):
            producer.OUTPUT.parent.mkdir(exist_ok=True)
            producer.OUTPUT.write_bytes(encoded(value))
            stream=io.StringIO()
            with contextlib.redirect_stdout(stream):producer.export()
            return stream.getvalue()+'M406_DONE gate_rc='+str(value['gate_return_code'])+' export_rc=0\n'
        complete=export(good)
        assert workflow.decode(complete)[2]==good
        assert workflow.decode(export(baseline))[2]==baseline
        mutations=[]
        for key,value in [('manifest_sha256','0'*64),('visual_forward_calls',3),('bindings_restored',False),
                          ('visual_owner_closed',False),('numerical_pass',False),('fpga_transactions',1),
                          ('gate_return_code',1),('performance_pass',True),('elapsed_s_diagnostic_not_performance',601)]:
            obj=copy.deepcopy(good);obj[key]=value;mutations.append(export(obj))
        obj=copy.deepcopy(good);obj['costs']['rows'][0]['calls']=2;mutations.append(export(obj))
        obj=copy.deepcopy(good);obj['costs']['exclusive_sum_ns']=0;mutations.append(export(obj))
        obj=copy.deepcopy(good);obj['backend_after']['settings_changed']=True;mutations.append(export(obj))
        obj=copy.deepcopy(good);obj['after_cache']['cache_bytes']=1;mutations.append(export(obj))
        mutations += [complete+complete,complete.replace('M406_RESULT_CHUNK=1/','M406_RESULT_CHUNK=0/'),
                      re.sub(r'(?m)^M406_RESULT_CHUNK=1/.*\n','',complete),
                      complete.replace('export_rc=0','export_rc=1'),
                      complete.replace('gate_rc=0','gate_rc=1'),
                      complete.replace('M406_RESULT_SHA256=','M406_RESULT_SHA256=0')]
        for text in mutations:
            try:workflow.decode(text)
            except (ValueError,KeyError,AssertionError):negatives+=1
            else:raise AssertionError('Invalid original result accepted')
        producer.OUTPUT.write_bytes(encoded(good))
        saved=folder/'saved_uart.log';saved.write_text(complete,encoding='utf-8')
        receipts=[]
        output=folder/'board/BOARD_RESULT.json'
        workflow.collect(saved,out=output,sync_function=lambda *a:receipts.append(a))
        assert output.read_bytes()==encoded(good) and len(receipts)==1
        assert receipts[0][0]=='latest_m406_vision_cost_board'
        assert 'Linear类别' in output.with_name('REPORT.md').read_text(encoding='utf-8')
        try:atomic(output,encoded(baseline),immutable=True)
        except RuntimeError:pass
        else:raise AssertionError('Immutable evidence overwritten')
        # Execute actual transfer validation for all files and every chunk.
        for name in ['PACKAGE_MANIFEST.json']+[r['path'] for r in manifest['files']]:
            prefix='upload_'+name.replace('.','_');size=(PKG/name).stat().st_size;count=(size+899)//900
            (folder/(prefix+'_final.log')).write_text('M212_CHUNKED_FILE_PASS '+sha(PKG/name),encoding='utf-8')
            for i in range(1,count+1):
                (folder/f'{prefix}_chunk_{i:03}.log').write_text(f'M212_CHUNK_PASS {i} {count} {min(i*900,size)} fixture\n',encoding='utf-8')
        (folder/'syntax.log').write_text('__M406_SYNTAX_RC_0__',encoding='utf-8')
        transfer=workflow.transfer(folder=folder,save=False)
        assert len(transfer['files'])==manifest['file_count']+1
        first=next(folder.glob('upload_*_chunk_001.log'));first.unlink()
        try:workflow.transfer(folder=folder,save=False)
        except RuntimeError:pass
        else:raise AssertionError('Missing receipt accepted')
    shell=ROOT/'C:/no'
    ps='C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe'
    subprocess.run([ps,'-NoProfile','-File',str(HERE/'m406_control03.ps1'),'-Mode','SelfTest'],check=True)
    script=(HERE/'m406_control03.ps1').read_text(encoding='utf-8')
    assert script.index('catch { $gateError=$_ }') < script.index("$workflow collect 'tmp/m40602/run.log'")
    assert "if ($LASTEXITCODE -ne 0) { throw 'Collection failed; recover saved bytes only' }" in script
    value=dict(status='PASS_OFFLINE_M406_ACTUAL_CONTROL_AND_COLLECTION',manifest_sha256=prep['manifest_sha256'],
        actual_producer_saved_export_and_collect=True,immutable_original_bytes=True,
        collection_negative_checks=negatives,all_eight_file_receipts_and_every_chunk_checked=True,
        missing_receipt_rejected=True,default_off_before_model=True,PS_failure_collects=True,
        fake_fields_not_target_backend_or_FPGA_evidence=True,
        source_sha256={n:sha(HERE/n) for n in ('m406_support03.py','m406_workflow02.py','m406_control03.ps1')},
        new_board_run=False,performance_pass=False)
    out=BASE/'runs/M406-vision-observer-support-03/RESULT.json';atomic(out,encoded(value),immutable=True)
    digest=sha(out)
    sync('latest_m406_vision_support',dict(status=value['status'],manifest_sha256=value['manifest_sha256'],
        result=out.relative_to(ROOT).as_posix(),sha256=digest),
        f'## M406 PS视觉观察实际控制/回收检查（2026-10-05）\n\nSHA {digest}；实际默认关闭/producer原字节导出/collect保存目标及同步键、immutable、{negatives}回收拒绝、8文件全部假回执/分块及缺失拒绝、PS故意失败仍收集检查通过。'
        '只L0明确fake结果/回执，目标Torch/后端/视觉成本未证明。下一步同COM3一次PS视觉缓存预热+窄观察；不运行语言、不改线程/输入/数学。')
    print(json.dumps(value,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
