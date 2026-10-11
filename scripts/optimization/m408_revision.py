"""Close original wrapper-resolution failure and freeze PS-only revision02."""
import ast
import json
import re
import subprocess
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync


def change(text,old,new,count=1):
    assert text.count(old)==count,(old,text.count(old),count)
    return text.replace(old,new)


def main():
    texts={n:(ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md','docsMILESTONES.md')}
    board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    previous=board['latest_m408_local_mlp_board'];raw=ROOT/previous['result']
    assert sha(raw)==previous['sha256']=='16a338889b846ee359c5a0f9d7d4c0dbc2057dd7140cea429e0cc4b36095c16b'
    failure=json.loads(raw.read_bytes());assert failure['errors'][0]['message']=="'M196PrecisionBoundary' object has no attribute 'mlp'"
    assert failure['component_pass'] and failure['visual_forward_calls']==failure['fpga_transactions']==failure['dma_allocations']==0
    assert failure['failure_visual_owner_close_called'] and failure['gate_return_code']==1
    old=BASE/'candidates/M408-local-MLP-A8-capture-01';pkg=BASE/'candidates/M408-local-MLP-A8-capture-02'
    assert sha(old/'PACKAGE_MANIFEST.json')=='ad44fee99d4cca068f6fd1be679e0a527d2e1a12bc70bf03dd9f99aafb7dc0c3'
    done=subprocess.run(['wsl.exe','-d','Ubuntu-24.04','--','/home/lyy/projects/qwen_baseline/.venv/bin/python','-B',
                         '/mnt/c/Users/30429/Desktop/TeLLMe_FPGA_2026/scripts/optimization/m408_target_component.py'],capture_output=True)
    if done.returncode:raise RuntimeError(done.stderr.decode('utf-8',errors='replace'))
    test=json.loads(re.search(r'(?m)^M408_TARGET_JSON=(.*)$',done.stdout.decode('utf-8'))[1])
    ids=json.loads((old/'M348_SOURCE_IDENTITIES.json').read_bytes());expected={x['path']:x['sha256'] for x in ids['files']}
    assert all(expected[k]==v for k,v in test['sources'].items())
    closure=dict(status='PASS_M408_WRAPPER_FAILURE_CAUSE_AND_NARROW_FIX',original_raw_sha256=previous['sha256'],
        original_gate_rc=1,actual_board_component_pass=True,visual_forward_calls=0,overlay_loaded=False,dma_allocations=0,
        original_process_returned=True,original_PS_close_called=True,no_activity_or_DMA_held=True,
        cause='Frozen M206ProgressLayer.layer contains M196PrecisionBoundary.layer; single unwrap targeted precision wrapper rather than encoder',
        exact_three_frozen_source_SHA=True,actual_WSL_Torch_wrapper_and_encoder_forward_fixture=test,
        WSL_not_target_model=True,original_package_results_and_logs_preserved=True,performance_pass=False,
        sources={n:sha(HERE/n) for n in ('m408_revision.py','m408_target.py','m408_target_component.py')})
    p=BASE/'runs/M408-wrapper-failure-closure-01/RESULT.json';atomic(p,encoded(closure),immutable=True)
    sync('latest_m408_wrapper_failure_closure',dict(status=closure['status'],result=p.relative_to(ROOT).as_posix(),sha256=sha(p)),
        f'## M408 MLP实例包装定位失败闭合（2026-10-05）\n\nSHA {sha(p)}；原FAIL {previous["sha256"]}保持，板端原Torch组件通过但0视觉/语言/Overlay/DMA。'
        '冻结源码确认M206.layer→M196.layer→MageVLVisionEncoderLayer；原代码只unwrap一次。原PS close调用且程序正常返回，未持有DMA。'
        '真实WSL冻结两wrapper+Encoder forward的小fixture逐位/残差/钩子恢复及三种拓扑拒绝通过，不证明模型。'
        '下一步只修正严格定位与资源前组件，原数学/输入/完整SHA保持，独立02本级筛选，不扩大PL或24层。')
    review=ROOT/'DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md';oldreview=review.read_text(encoding='utf-8-sig')
    note=f'''## M408 视觉层双重包装定位遗漏（2026-10-05）

- 原FAIL SHA `{previous['sha256']}`，原rc1/export0，13块严格回收并同步；完整资产/49源码/板端真实Torch组件均通过，构造后错误发生在MLP实例定位，视觉前向0、语言/Overlay/DMA/PL0。不能当作A8精度或性能失败。原PS close调用且进程正常返回，无活动DMA。
- 实际冻结拓扑是M206ProgressLayer.layer→M196PrecisionBoundary.layer→MageVLVisionEncoderLayer。此前只解开外层，遗漏精度边界。以后模块插桩须从已解析的冻结构造源码追踪到真实叶模块，不能从单个属性名推测层级；按精确class、index和target/output dtype拒绝错误路径。
- 独立02保留原包/结果/日志，三份源SHA原样。实际冻结wrapper和Encoder forward的真实Torch小fixture逐位/残差/恢复及错拓扑拒绝先于模型构造；原输入/数学和全部资产SHA不删。只在PS捕获级修复重试，禁止借此重新画像、语言或硬件；实际新producer/collector/传输/目的地配套检查后才能启动。

'''
    title,rest=oldreview.split('\n',1);atomic(review,(title+'\n\n'+note+rest.lstrip('\n')).encode('utf-8'))
    gate=(old/'m408_gate.py').read_text(encoding='utf-8')
    gate=change(gate,'m408_mlp_capture_01','m408_mlp_capture_02')
    gate=change(gate,'from m408_component import component','from m408_component import component\nfrom m408_target import resolve_target\nfrom m408_target_component import from_sources')
    gate=change(gate,"        result['component_pass'] = True\n","        result['component_pass'] = True\n        print('M408_SMALL_WRAPPER_FIXTURE_BEGIN',flush=True)\n        result['target_component'] = from_sources(torch,RELEASE)\n        print('M408_SMALL_WRAPPER_FIXTURE_END',flush=True)\n")
    gate=change(gate,"        layer = runtime.vision.encoder.layers[12].layer\n", "        from m206_ps_vision_runtime import M206ProgressLayer\n        from ps_vision_runtime import M196PrecisionBoundary\n        layer,result['target_resolution'] = resolve_target(runtime.vision,M206ProgressLayer,M196PrecisionBoundary,torch)\n")
    ast.parse(gate,feature_version=(3,10))
    if pkg.exists():raise RuntimeError('Immutable revision already exists')
    pkg.mkdir()
    oldmanifest=json.loads((old/'PACKAGE_MANIFEST.json').read_bytes())
    unchanged=[]
    for row in oldmanifest['files']:
        name=row['path'];assert sha(old/name)==row['sha256']
        if name=='SHA256SUMS':continue
        blob=(old/name).read_bytes()
        if name=='m408_gate.py':blob=gate.encode('utf-8')
        elif name=='run_m408_capture.sh':blob=change(blob.decode('utf-8'),'m408_mlp_capture_01','m408_mlp_capture_02').encode('utf-8')
        else:unchanged.append(name)
        atomic(pkg/name,blob,immutable=True)
    for name in ('m408_target.py','m408_target_component.py'):atomic(pkg/name,(HERE/name).read_bytes(),immutable=True)
    files=sorted(pkg.iterdir());atomic(pkg/'SHA256SUMS',''.join(f'{sha(x)}  {x.name}\n' for x in files).encode('ascii'),immutable=True)
    files=sorted(pkg.iterdir());manifest=dict(oldmanifest,file_count=len(files),total_bytes=sum(x.stat().st_size for x in files),files=[dict(path=x.name,bytes=x.stat().st_size,sha256=sha(x)) for x in files])
    atomic(pkg/'PACKAGE_MANIFEST.json',encoded(manifest),immutable=True)
    workflow=(HERE/'m408_workflow.py').read_text(encoding='utf-8')
    substitutions=[('M408-local-MLP-A8-capture-01','M408-local-MLP-A8-capture-02'),('tmp/m408','tmp/m40802'),
        ('M408-local-MLP-transfer-01','M408-local-MLP-transfer-02'),('M408-local-MLP-A8-board-01','M408-local-MLP-A8-board-02'),
        ('latest_m408_local_mlp_transfer','latest_m408_local_mlp_transfer02'),('latest_m408_local_mlp_board','latest_m408_local_mlp_board02'),
        ('m408_mlp_capture_01','m408_mlp_capture_02')]
    for a,b in substitutions:assert a in workflow;workflow=workflow.replace(a,b)
    anchor="        c = r['component']\n"
    extra="        tc = r['target_component']\n        if not tc['actual_frozen_wrappers_and_encoder_forward'] or not tc['original_capture_bit_exact'] or not tc['hooks_restored'] or tc['topology_rejects'] != 3 or tc['target_path'] != 'encoder.layers.12.layer.layer': raise ValueError('Target wrapper component incomplete')\n        if r['target_resolution'] != tc['topology']: raise ValueError('Actual target wrapper differs')\n"
    workflow=change(workflow,anchor,extra+anchor)
    atomic(HERE/'m408_workflow02.py',workflow.encode('utf-8'),immutable=True)
    control=(HERE/'m408_control.ps1').read_text(encoding='utf-8')
    for a,b in [('M408-local-MLP-A8-capture-01','M408-local-MLP-A8-capture-02'),('m408_local_mlp_candidate_01','m408_local_mlp_candidate_02'),
        ('latest_m408_local_mlp_preparation','latest_m408_local_mlp_preparation02'),('latest_m408_local_mlp_support','latest_m408_local_mlp_support02'),
        ('latest_m408_local_mlp_transfer','latest_m408_local_mlp_transfer02'),('m408_workflow.py','m408_workflow02.py'),
        ('tmp/m408','tmp/m40802'),('M408-local-MLP-A8-board-01','M408-local-MLP-A8-board-02')]:assert a in control;control=control.replace(a,b)
    control=change(control,"'latest_m407_visual_mlp_layout_closure',","'latest_m407_visual_mlp_layout_closure','latest_m408_wrapper_failure_closure',")
    atomic(HERE/'m408_control03.ps1',control.encode('utf-8'),immutable=True)
    support=(HERE/'m408_support.py').read_text(encoding='utf-8')
    for a,b in [('latest_m408_local_mlp_preparation','latest_m408_local_mlp_preparation02'),('import m408_workflow as workflow','import m408_workflow02 as workflow'),
        ('m408_control.ps1','m408_control03.ps1'),('m408_workflow.py','m408_workflow02.py'),('m408_support.py','m408_support02.py'),
        ('tmp/m408','tmp/m40802'),('m408_mlp_capture_01','m408_mlp_capture_02'),('latest_m408_local_mlp_board','latest_m408_local_mlp_board02'),
        ('latest_m408_local_mlp_support','latest_m408_local_mlp_support02'),('M408-local-MLP-support-01','M408-local-MLP-support-02')]:assert a in support;support=support.replace(a,b)
    support=change(support,"            capture_manifest=capture,elapsed_s_diagnostic_not_performance=1)","            capture_manifest=capture,elapsed_s_diagnostic_not_performance=1,\n            target_component=dict(actual_frozen_wrappers_and_encoder_forward=True,original_capture_bit_exact=True,hooks_restored=True,topology_rejects=3,target_path='encoder.layers.12.layer.layer',topology={'explicit_fake':True}),target_resolution={'explicit_fake':True})")
    atomic(HERE/'m408_support02.py',support.encode('utf-8'),immutable=True)
    value=dict(status='PASS_M408_NARROW_TARGET_RESOLUTION_REVISION02',prior_failure_closure_sha256=sha(p),
        manifest_sha256=sha(pkg/'PACKAGE_MANIFEST.json'),unchanged_payloads=unchanged,actual_WSL_component=test,
        original_quantizer_GELU_attention_input_weights_unchanged=True,board_run=False,local_A8_screen_pass=False,performance_pass=False,
        source_sha256={n:sha(HERE/n) for n in ('m408_revision.py','m408_target.py','m408_target_component.py','m408_control03.ps1','m408_workflow02.py','m408_support02.py')})
    p=BASE/'runs/M408-local-MLP-preparation-02/RESULT.json';atomic(p,encoded(value),immutable=True)
    sync('latest_m408_local_mlp_preparation02',dict(status=value['status'],result=p.relative_to(ROOT).as_posix(),sha256=sha(p),manifest_sha256=value['manifest_sha256']),
        f'## M408 严格双包装定位02准备（2026-10-05）\n\nSHA {sha(p)}；仅原M206/M196/Encoder精确解包和资源前实际源码组件，'
        '新02结果路径，原量化/GELU/输入及全部asset/source SHA保持。独立控制03/workflow02需实际路由/回收/完整回执检查后才准入；0新上板，质量/性能未通过。')
    print('M408_REVISION02_PREPARED',sha(p),value['manifest_sha256'])


if __name__=='__main__':main()
