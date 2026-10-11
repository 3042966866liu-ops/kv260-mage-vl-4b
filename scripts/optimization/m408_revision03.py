"""Close exact dtype-check failure and prepare immutable same-level revision03."""
import ast
import json
import re
import subprocess
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync

def replace(text,old,new,count=1):
    assert text.count(old)==count,(old,text.count(old),count)
    return text.replace(old,new)

def main():
    recovery={n:dict(full_read=True,sha256=sha(ROOT/n),lines=len((ROOT/n).read_text(encoding='utf-8-sig').splitlines()))
        for n in ('CURRENT_STATE.md','DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md','docsMILESTONES.md')}
    board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    previous=board['latest_m408_local_mlp_board02'];raw=ROOT/previous['result']
    assert sha(raw)==previous['sha256']=='2b6a7f35676249e03d6e76610b54b25c722ce58fbbab56f5254daaeb4e4bb2a0'
    failure=json.loads(raw.read_bytes())
    assert failure['errors'][0]['message']=='Original FP32 precision boundary differs'
    assert failure['component_pass'] and failure['visual_forward_calls']==failure['fpga_transactions']==failure['dma_allocations']==0
    assert failure['failure_visual_owner_close_called'] and failure['gate_return_code']==1
    observation=ROOT/'tmp/m40803/actual_constructor.json'
    actual=json.loads(observation.read_bytes())
    assert actual['owner_collected'] and actual['model_forward_calls']==0 and actual['output_dtype']=='torch.bfloat16'
    old=BASE/'candidates/M408-local-MLP-A8-capture-02';pkg=BASE/'candidates/M408-local-MLP-A8-capture-03'
    assert sha(old/'PACKAGE_MANIFEST.json')=='ff628c276518e9f6f14bdaf2ea1b8c96d03f52658eb85f3f2d75fcbe9804cc1e'
    ids={x['path']:x['sha256'] for x in json.loads((old/'M348_SOURCE_IDENTITIES.json').read_bytes())['files']}
    assert all(ids[v['path']]==v['sha256']==sha(ROOT/v['path']) for v in actual['sources'].values())
    run=subprocess.run(['wsl.exe','-d','Ubuntu-24.04','--','/home/lyy/projects/qwen_baseline/.venv/bin/python','-B',
        '/mnt/c/Users/30429/Desktop/TeLLMe_FPGA_2026/scripts/optimization/m408_target_component03.py'],capture_output=True)
    if run.returncode:raise RuntimeError(run.stderr.decode('utf-8',errors='replace'))
    fixture=json.loads(re.search(r'(?m)^M408_TARGET_JSON=(.*)$',run.stdout.decode('utf-8'))[1])
    assert fixture['topology_rejects']==4 and fixture['topology']==actual['topology']
    assert all(ids[k]==v for k,v in fixture['sources'].items())
    closure=dict(status='CLOSED_M408_WRONG_OUTPUT_DTYPE_CHECK_BEFORE_FORWARD',raw_sha256=previous['sha256'],
        original_gate_rc=1,visual_forward_calls=0,dma_allocations=0,overlay_loaded=False,
        original_PS_close_called=True,original_process_returned=True,
        cause='Original layer12 inner FP32 returns through BF16 boundary; prior check and fixture incorrectly assumed FP32 boundary output',
        prior_fixture_scope_corrected='Old fixture proved its supplied topology only; not actual constructor dtype',
        additional_prevented_error='CPU store strips model.visual. prefix; previous matrix-name check would reject real modules',
        actual_frozen_constructor=actual,constructor_observation_sha256=sha(observation),corrected_actual_wrapper_fixture=fixture,
        original_packages_results_logs_preserved=True,recovery_documents=recovery,
        math_input_boundary_GELU_cache_threads_unchanged=True,new_board_run=False,performance_pass=False,
        source_sha256={n:sha(HERE/n) for n in ('m408_revision03.py','m408_constructor_audit.py','m408_target03.py','m408_target_component03.py')})
    p=BASE/'runs/M408-boundary-failure-closure-02/RESULT.json';atomic(p,encoded(closure),immutable=True)
    sync('latest_m408_boundary_failure_closure',dict(status=closure['status'],result=p.relative_to(ROOT).as_posix(),sha256=sha(p)),
        f'## M408 实际BF16边界前置失败闭合（2026-10-05）\n\nSHA {sha(p)}；原FAIL {previous["sha256"]}保持。'
        '原包装内部FP32、输出BF16，此前检查及fixture误设输出FP32；0视觉/语言/Overlay/DMA/PL，原PS close及正常退出。'
        '真实冻结构造器在WSL CPU无forward验证全部九模块同SHA、两个实际矩阵/名称/bias和释放；仅离线元数据，不证明板端质量。'
        '新fixture保留BF16边界、原Encoder forward/FP32残差及四拒绝；同时修正CPU store短名称检查。只修插桩准入，原数学/输入不改；需实际03配套核对后同级捕获，不扩大PL或24层。')
    review=ROOT/'DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md';text=review.read_text(encoding='utf-8-sig');title,rest=text.split('\n',1)
    note=f'''## M408 fixture未覆盖实际构造精度（2026-10-05）

- 第二次原FAIL SHA `{previous['sha256']}`，gate1/export0，14块严格回收。真实构造后准入拒绝，视觉/语言/Overlay/DMA/PL均0；原owner close且程序正常返回，不是A8精度失败。
- 原M207以BF16 compute构造，第12层M196内部target FP32、output BF16；此前检查及小fixture把output误设FP32，fixture通过不能证明实际构造合同。以后直接运行冻结构造器的无forward离线核对，检查实际包装、精度、store名称、矩阵及bias，再测试插桩器。CPU store原代码剥离model.visual.，不得拿PL full name直接比较CPU模块name。
- 原01/02证据不可改。新03只纠正准入及fixture，保留原BF16输出边界和完整资产/源码SHA；实际producer/collector/目标路径/BOARD键、manifest-first完整回执、错误收集及默认关闭检查后才能重试本PS捕获级。无A8局部PASS不进入PL，无净收益不扩24层。

'''
    atomic(review,(title+'\n\n'+note+rest.lstrip('\n')).encode('utf-8'))
    gate=(old/'m408_gate.py').read_text(encoding='utf-8')
    gate=replace(gate,'m408_mlp_capture_02','m408_mlp_capture_03')
    gate=replace(gate,'from m408_target import resolve_target','from m408_target03 import resolve_target, verify_matrices')
    gate=replace(gate,'from m408_target_component import from_sources','from m408_target_component03 import from_sources')
    start=gate.index("        if not isinstance(mlp.fc1,");end=gate.index("        result['visual_forward_calls'] = 1",start)
    oldcheck=gate[start:end]
    assert 'model.visual.encoder.layers.12.mlp.' in oldcheck and oldcheck.count('raise RuntimeError')==2
    newcheck="        result['target_matrices'] = verify_matrices(layer,M207FP32GemmW4Linear,torch)\n        target_expected = json.loads((HERE/'EXPECTED_TARGET.json').read_bytes())\n        if result['target_resolution'] != target_expected['topology'] or result['target_matrices'] != target_expected['matrices']: raise RuntimeError('Actual constructor target identity differs')\n"
    gate=gate[:start]+newcheck+gate[end:]
    gate=replace(gate,'del x, qdq, mod','del x, qdq')
    ast.parse(gate,feature_version=(3,10))
    if pkg.exists():raise RuntimeError('Immutable revision already exists')
    pkg.mkdir()
    unchanged=[]
    for row in json.loads((old/'PACKAGE_MANIFEST.json').read_bytes())['files']:
        name=row['path'];assert sha(old/name)==row['sha256']
        if name in ('SHA256SUMS','m408_target.py','m408_target_component.py'):continue
        blob=(old/name).read_bytes()
        if name=='m408_gate.py':blob=gate.encode('utf-8')
        elif name=='run_m408_capture.sh':blob=replace(blob.decode('utf-8'),'m408_mlp_capture_02','m408_mlp_capture_03').encode('utf-8')
        else:unchanged.append(name)
        atomic(pkg/name,blob,immutable=True)
    for n in ('m408_target03.py','m408_target_component03.py'):atomic(pkg/n,(HERE/n).read_bytes(),immutable=True)
    atomic(pkg/'EXPECTED_TARGET.json',encoded(dict(topology=actual['topology'],matrices=actual['matrices'])),immutable=True)
    files=sorted(pkg.iterdir());atomic(pkg/'SHA256SUMS',''.join(f'{sha(x)}  {x.name}\n' for x in files).encode('ascii'),immutable=True)
    files=sorted(pkg.iterdir());manifest=dict(file_count=len(files),total_bytes=sum(x.stat().st_size for x in files),files=[dict(path=x.name,bytes=x.stat().st_size,sha256=sha(x)) for x in files])
    atomic(pkg/'PACKAGE_MANIFEST.json',encoded(manifest),immutable=True)
    workflow=(HERE/'m408_workflow02.py').read_text(encoding='utf-8')
    for a,b in [('M408-local-MLP-A8-capture-02','M408-local-MLP-A8-capture-03'),('tmp/m40802','tmp/m40803'),
        ('M408-local-MLP-transfer-02','M408-local-MLP-transfer-03'),('M408-local-MLP-A8-board-02','M408-local-MLP-A8-board-03'),
        ('latest_m408_local_mlp_transfer02','latest_m408_local_mlp_transfer03'),('latest_m408_local_mlp_board02','latest_m408_local_mlp_board03'),
        ('m408_mlp_capture_02','m408_mlp_capture_03')]:assert a in workflow;workflow=workflow.replace(a,b)
    workflow=replace(workflow,"tc['topology_rejects'] != 3","tc['topology_rejects'] != 4")
    workflow=replace(workflow,"        c = r['component']\n","        target_expected = json.loads((PKG/'EXPECTED_TARGET.json').read_bytes())\n        if r['target_resolution'] != target_expected['topology'] or r['target_matrices'] != target_expected['matrices']: raise ValueError('Target actual constructor differs')\n        c = r['component']\n")
    atomic(HERE/'m408_workflow03.py',workflow.encode('utf-8'),immutable=True)
    control=(HERE/'m408_control03.ps1').read_text(encoding='utf-8')
    for a,b in [('M408-local-MLP-A8-capture-02','M408-local-MLP-A8-capture-03'),('m408_local_mlp_candidate_02','m408_local_mlp_candidate_03'),
        ('latest_m408_local_mlp_preparation02','latest_m408_local_mlp_preparation03'),('latest_m408_local_mlp_support02','latest_m408_local_mlp_support03'),
        ('latest_m408_local_mlp_transfer02','latest_m408_local_mlp_transfer03'),('m408_workflow02.py','m408_workflow03.py'),
        ('tmp/m40802','tmp/m40803'),('M408-local-MLP-A8-board-02','M408-local-MLP-A8-board-03'),
        ('latest_m408_wrapper_failure_closure','latest_m408_boundary_failure_closure')]:assert a in control;control=control.replace(a,b)
    atomic(HERE/'m408_control04.ps1',control.encode('utf-8'),immutable=True)
    support=(HERE/'m408_support02.py').read_text(encoding='utf-8')
    for a,b in [('latest_m408_local_mlp_preparation02','latest_m408_local_mlp_preparation03'),('m408_workflow02','m408_workflow03'),
        ('m408_control03.ps1','m408_control04.ps1'),('m408_support02.py','m408_support03.py'),('tmp/m40802','tmp/m40803'),
        ('m408_mlp_capture_02','m408_mlp_capture_03'),('latest_m408_local_mlp_board02','latest_m408_local_mlp_board03'),
        ('latest_m408_local_mlp_support02','latest_m408_local_mlp_support03'),('M408-local-MLP-support-02','M408-local-MLP-support-03')]:assert a in support;support=support.replace(a,b)
    support=replace(support,"topology_rejects=3,target_path='encoder.layers.12.layer.layer',topology={'explicit_fake':True}),target_resolution={'explicit_fake':True})",
        "topology_rejects=4,target_path='encoder.layers.12.layer.layer',topology=json.loads((pkg/'EXPECTED_TARGET.json').read_bytes())['topology']),target_resolution=json.loads((pkg/'EXPECTED_TARGET.json').read_bytes())['topology'],target_matrices=json.loads((pkg/'EXPECTED_TARGET.json').read_bytes())['matrices'])")
    atomic(HERE/'m408_support03.py',support.encode('utf-8'),immutable=True)
    value=dict(status='PASS_M408_ACTUAL_CONSTRUCTOR_BOUND_REVISION03',manifest_sha256=sha(pkg/'PACKAGE_MANIFEST.json'),
        failure_closure_sha256=sha(p),actual_constructor=actual,corrected_fixture=fixture,unchanged_payloads=unchanged,
        removed_checks=oldcheck,new_checks=newcheck,board_run=False,performance_pass=False,
        source_sha256={n:sha(HERE/n) for n in ('m408_revision03.py','m408_constructor_audit.py','m408_target03.py','m408_target_component03.py','m408_control04.ps1','m408_workflow03.py','m408_support03.py')})
    p=BASE/'runs/M408-local-MLP-preparation-03/RESULT.json';atomic(p,encoded(value),immutable=True)
    sync('latest_m408_local_mlp_preparation03',dict(status=value['status'],result=p.relative_to(ROOT).as_posix(),sha256=sha(p),manifest_sha256=value['manifest_sha256']),
        f'## M408 实际构造合同03准备（2026-10-05）\n\nSHA {sha(p)}；保留原FP32内部/BF16输出、原CPU短name及实际bias SHA，冻结构造器无forward和四拒绝fixture通过。'
        '原输入/量化/GELU/完整SHA与八项载荷保持；默认关闭独立03，仅PS真实捕获筛选。新控制04/workflow03/support03须实际配套检查后才能上板；无质量或性能PASS。')
    print('M408_REVISION03_PREPARED',sha(p),value['manifest_sha256'])

if __name__=='__main__':main()
