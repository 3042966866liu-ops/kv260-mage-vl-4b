"""Check changed pre-entry, exact same numerical regions, new receipt routing."""
import ast
import copy
import importlib.util
import json
import subprocess
import tempfile
from unittest.mock import patch
from m351_workflow import ROOT,HERE,BASE,sha,atomic,encoded,sync
import m400_layer_entry_02 as entry
import m400_collect02 as collector
from m400_support import export,synthetic_layer

PKG=BASE/'candidates/M400-tail-layer-02'
OLD=BASE/'candidates/M400-tail-layer-01'
PS=r'C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell\pwsh.exe'


def main():
    prior=BASE/'runs/M400-tail-layer-support-01/RESULT.json'
    assert sha(prior)=='55976627edc4b85e2b33e389a242ee7b3ddb5b092f1f1a758130d63a4b1d5031'
    prep=json.loads((BASE/'runs/M400-tail-layer-preparation-02/RESULT.json').read_text(encoding='utf-8'))
    source=ROOT/'release_staging/kv260-mage-vl-4b-prebuilt-install-20260926-v7/deployment/mage_vl4b/m242_m241_fixed_text_board_candidate/m241_video_language_runtime.py'
    with patch.object(entry,'HERE',PKG),patch.object(entry,'SOURCE',source):
        proof=entry.precheck(sha(PKG/'PACKAGE_MANIFEST.json'))
    assert proof==prep['source_precheck']
    # Changed collector envelope accepts both explicit fake PASS and original failure;
    # all numerical/lifetime validation AST is unchanged from 101 prior negative checks.
    r=synthetic_layer();r['manifest_sha256']=sha(PKG/'PACKAGE_MANIFEST.json');r['source_precheck_before_hardware_import']=proof
    assert collector.decode(export(r))[2]==r
    failure=json.loads((BASE/'runs/M400-tail-layer-board-01/BOARD_RESULT.json').read_text(encoding='utf-8'))
    failure.update(manifest_sha256=r['manifest_sha256'],source_precheck_before_hardware_import=proof)
    assert collector.decode(export(failure))[2]==failure
    negatives=0
    for field,value in [('source_precheck_before_hardware_import',{}),('manifest_sha256',sha(OLD/'PACKAGE_MANIFEST.json')),('layer_result',{}),('released_buffers',[]),('transactions',[])]:
        q=copy.deepcopy(r);q[field]=value
        try:collector.decode(export(q))
        except (ValueError,KeyError):negatives+=1
        else:raise AssertionError('Changed envelope accepted '+field)
    oldtree=ast.parse((HERE/'m400_collect.py').read_text(encoding='utf-8'));newtree=ast.parse((HERE/'m400_collect02.py').read_text(encoding='utf-8'))
    ov=next(n for n in oldtree.body if isinstance(n,ast.FunctionDef) and n.name=='validate_layer')
    nv=next(n for n in newtree.body if isinstance(n,ast.FunctionDef) and n.name=='validate_layer')
    assert ast.dump(ov)==ast.dump(nv)
    od=next(n for n in oldtree.body if isinstance(n,ast.FunctionDef) and n.name=='decode')
    nd=next(n for n in newtree.body if isinstance(n,ast.FunctionDef) and n.name=='decode')
    nd.body=[n for n in nd.body if not (isinstance(n,ast.If) and 'source_precheck_before_hardware_import' in ast.unparse(n.test))]
    assert ast.dump(od)==ast.dump(nd)
    spec=importlib.util.spec_from_file_location('assembly02',PKG/'m400_assemble.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    assert mod.OLD.as_posix()=='/home/ubuntu/m400_tail_layer_candidate_01' and mod.OLD_SHA==sha(OLD/'PACKAGE_MANIFEST.json')
    m=json.loads((PKG/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'));old={r['path']:r for r in json.loads((OLD/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))['files']}
    delta=[r['path'] for r in m['files'] if old.get(r['path'])!=r]
    with tempfile.TemporaryDirectory(dir=ROOT/'tmp/m400') as d:
        dest=mod.HERE=__import__('pathlib').Path(d);mod.OLD=OLD
        for n in ['PACKAGE_MANIFEST.json']+delta:(dest/n).write_bytes((PKG/n).read_bytes())
        mod.main(sha(dest/'PACKAGE_MANIFEST.json'))
        assert all(sha(dest/r['path'])==r['sha256'] for r in m['files'])
    for mode in ('SelfTest','List'):
        p=subprocess.run([PS,'-NoProfile','-File',str(HERE/'m400_control02.ps1'),'-Mode',mode],capture_output=True,text=True,encoding='utf-8',check=True)
        if mode=='List':assert json.loads(p.stdout)==['PACKAGE_MANIFEST.json']+delta
        else:assert 'M400_CONTROL_SELF_TEST_PASS' in p.stdout
    # Test actual entry ordering/rejection with poisonous/fake import, no Overlay.
    p=subprocess.run([sys.executable,'-X','utf8','-B',str(HERE/'test_m400_layer_entry_02.py')],capture_output=True,text=True,encoding='utf-8',check=True)
    assert p.stderr.rstrip().endswith('OK')
    runner=(PKG/'run_m400_tail_layer.sh').read_text(encoding='utf-8')
    assert 'm400_layer_entry_02.py' in runner and 'm400_tail_layer_gate.py' not in runner
    for name in ('m400_collect02.py','m400_workflow02.py','m400_close_layer02.py','m400_prepare_layer02.py','m400_support02.py','m400_layer_entry_02.py'):
        ast.parse((HERE/name).read_text(encoding='utf-8'),feature_version=(3,10))
    workflow=(HERE/'m400_workflow02.py').read_text(encoding='utf-8');closure=(HERE/'m400_close_layer02.py').read_text(encoding='utf-8')
    assert 'latest_m400_tail_layer_transfer02' in workflow and 'from m400_collect02 import' in workflow
    assert 'M400-tail-layer-board-02' in (HERE/'m400_collect02.py').read_text(encoding='utf-8')
    assert all('latest_m400_tail_layer_'+x+'02' in closure for x in ('board','support','transfer','closure'))
    names=['m400_control02.ps1','m400_collect02.py','m400_workflow02.py','m400_close_layer02.py','m400_prepare_layer02.py','m400_support02.py','m400_layer_entry_02.py','m400_tail_source_02.py','test_m400_layer_entry_02.py']
    value=dict(status='PASS_OFFLINE_LAYER02_PREENTRY_CONTROL_AND_COLLECTION',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),source_sha256={n:sha(HERE/n) for n in names},
               preentry_actual_package_pass=True,preentry_order_and_rejection_test=True,collector_new_negative_checks=negatives,prior_101_negative_validation_AST_unchanged=True,
               prior_component_checks_7_and_region_checks_4_reused=True,prior_support_sha256=sha(prior),assembly_actual_new_source_pass=True,delta_files=delta,
               actual_PS_List_SelfTest_pass=True,python310_syntax=True,source_precheck=proof,synthetic_DMA_metadata_explicit=True,board_run=False,layer_numerical_pass=False,performance_pass=False)
    out=BASE/'runs/M400-tail-layer-support-02/RESULT.json';atomic(out,encoded(value),immutable=True);h=sha(out)
    sync('latest_m400_tail_layer_support02',dict(status=value['status'],manifest_sha256=value['manifest_sha256'],result=out.relative_to(ROOT).as_posix(),sha256=h),
         f'## M400 同级02控制/源码前置支持（2026-10-04）\n\nSHA `{h}`；实际42载荷pre-entry完整SHA/原源检查、入口拒绝和先检查后fake导入通过，实际新源assembly和PS List/SelfTest通过。新增5回收负例；原101判据及全部validate_layer AST相同，原7scope/4region证据复用。仅源码检查提前和确定性修复，不改数学/关闭/生产准入；fake硬件计数明确。下一步同COM3 sudo、manifest-first900B上传02并本单层一次执行，原01结果不改；尚未本级数值PASS。')
    print(json.dumps(dict(status=value['status'],sha256=h,delta_files=delta)))


if __name__=='__main__':
    import sys
    main()
