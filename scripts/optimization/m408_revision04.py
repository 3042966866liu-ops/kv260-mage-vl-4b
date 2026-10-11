"""Close original-native-rank capture failure and freeze same-level revision04."""
import ast
import json
import re
import subprocess
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
from m408_revision03 import replace

def main():
    recovery={n:dict(full_read=True,sha256=sha(ROOT/n),lines=len((ROOT/n).read_text(encoding='utf-8-sig').splitlines())) for n in ('CURRENT_STATE.md','DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md','docsMILESTONES.md')}
    b=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes());oldraw=b['latest_m408_local_mlp_board03']
    assert sha(ROOT/oldraw['result'])==oldraw['sha256']=='2c20e922dc5adc9fcbc1e068b7d6f27a66e32c22a8b7fdbbd0fbea8a090e6b55'
    fail=json.loads((ROOT/oldraw['result']).read_bytes())
    assert fail['errors'][0]['message']=='Original finite FP32 matrix required'
    assert 'layer_norm2(hidden_states)' in fail['errors'][0]['traceback'] and fail['visual_forward_calls']==1 and fail['local_mlp_forward_calls']==0
    assert fail['failure_visual_owner_close_called'] and fail['dma_allocations']==fail['fpga_transactions']==0
    shape_path=ROOT/'tmp/m40804/actual_shapes.json';replay_path=ROOT/'tmp/m40804/capture_replay.json'
    shapes=json.loads(shape_path.read_bytes());replay=json.loads(replay_path.read_bytes())
    assert replay['real_same_input_frozen_MLP_replay_bit_exact'] and replay['owner_collected'] and replay['hooks_restored']
    assert shapes['visual']['sha256']==replay['original_capture_visual_sha256']
    assert {k:v['shape'] for k,v in shapes['records'].items()}==replay['native_shapes']
    run=subprocess.run(['wsl.exe','-d','Ubuntu-24.04','--','/home/lyy/projects/qwen_baseline/.venv/bin/python','-B',
        '/mnt/c/Users/30429/Desktop/TeLLMe_FPGA_2026/scripts/optimization/m408_target_component04.py'],capture_output=True)
    if run.returncode:raise RuntimeError(run.stderr.decode('utf-8',errors='replace'))
    fixture=json.loads(re.search(r'(?m)^M408_TARGET_JSON=(.*)$',run.stdout.decode('utf-8'))[1])
    assert fixture['topology_rejects']==fixture['bad_shapes_rejected']==4 and fixture['native_single_batch_preserved']
    closure=dict(status='CLOSED_M408_CAPTURE_NATIVE_BATCH_RANK_FAILURE',raw_sha256=oldraw['sha256'],gate_rc=1,
        visual_attempts=1,visual_completed=False,local_MLP_A8_started=False,dma_allocations=0,fpga_transactions=0,
        PS_owner_close_called=True,process_returned=True,board_hook_restoration_not_recorded=not fail['bindings_restored'],
        board_shape_not_explicitly_recorded=True,cause_inferred_from_exact_frozen_forward_and_input='Original encoder/MLP tensors have rank3 single batch; rank2-only capture rejected norm2 residual',
        original_shape_audit=shapes,real_capture_replay_check=replay,small_native_wrapper_fixture=fixture,
        shape_observation_sha256=sha(shape_path),replay_observation_sha256=sha(replay_path),recovery=recovery,
        original_packages_results_logs_preserved=True,WSL_not_board=True,performance_pass=False,
        offline_rejected_harness='Shape-only audit first forward finished, then undefined local m in cleanup caused NameError; fixed before saved audit, no board effect')
    p=BASE/'runs/M408-native-shape-failure-closure-03/RESULT.json';atomic(p,encoded(closure),immutable=True)
    sync('latest_m408_native_shape_failure_closure',dict(status=closure['status'],result=p.relative_to(ROOT).as_posix(),sha256=sha(p)),
        f'## M408 原单batch维度捕获失败闭合（2026-10-05）\n\nSHA {sha(p)}；原FAIL {oldraw["sha256"]}保持，19块严格回收。原视觉尝试1，在第12层norm2前hook拒绝，未完成视觉/未开始A8回放，0语言/Overlay/DMA/PL，原owner close和正常退出。'
        '板端未保存实际shape及hook恢复，不能把它当显式证明；冻结同输入WSL原forward六点均[1,392,K] FP32，推定二维-only捕获拒绝。'
        '真实原模型的新单batch捕获/三维MLP回放逐位与原GELU/两13批量化及释放通过，只WSL组件。04只保存时去单batch维、计算保持三维；源码/输入/全部SHA不删，仅同PS失败级重试，未准入PL或24层。')
    review=ROOT/'DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md';title,rest=review.read_text(encoding='utf-8-sig').split('\n',1)
    note=f'''## M408 捕获矩阵合同遗漏原单batch维（2026-10-05）

- 原FAIL SHA `{oldraw['sha256']}`，rc1/export0、19块完整回收。真实视觉尝试1在第12层norm2前hook失败，0局部A8/语言/Overlay/DMA/PL；原PS close且进程返回。raw没记录实际shape或hook恢复，保留此限制，不能解释为非finite模型输出或A8质量失败。
- 冻结原代码/同固定输入在WSL真实forward表明六捕获点均FP32 [1,392,K]；原二维-only要求不符合实际MLP接口。04仅序列化时移除严格单batch，实际MLP回放/量化返回保持三维，拒绝多batch/额外维/FP64/nonfinite。完整原模型和真实输入的捕获/逐位回放/量化几何及释放先于上板；不能再用二维小fixture代替原native rank。
- 三旧包与raw保持。WSL输出SHA不同于板端参考，明确仅平台内组件，不替代板端原视觉SHA；下一次仍要求原board参考完整SHA。只有实际producer/collector/native-shape/目标路径/BOARD键和完整传输回执检查通过才重试PS级；不得删除检查或扩大到PL。

'''
    atomic(review,(title+'\n\n'+note+rest.lstrip('\n')).encode('utf-8'))
    old=BASE/'candidates/M408-local-MLP-A8-capture-03';pkg=BASE/'candidates/M408-local-MLP-A8-capture-04'
    assert sha(old/'PACKAGE_MANIFEST.json')=='404d3fd49d19fa57580324c5902e410d3200b115a1c03cfd9a7d54ea894d34e5'
    gate=(old/'m408_gate.py').read_text(encoding='utf-8')
    for a,c in [('m408_mlp_capture_03','m408_mlp_capture_04'),('from m408_mlp_capture import','from m408_mlp_capture04 import'),
        ('from m408_component import','from m408_component04 import'),('from m408_target_component03 import','from m408_target_component04 import')]:gate=replace(gate,a,c)
    gate=replace(gate,"        result['bindings_restored'] = captured.restored\n","        result['bindings_restored'] = captured.restored\n        result['native_capture_shapes'] = captured.native_shapes\n        if captured.native_shapes != {k:[1,*s] for k,s in SHAPES.items()}: raise RuntimeError('Original native batch geometry differs')\n")
    gate=replace(gate,"x = torch.from_numpy(captured.values['input'])","x = torch.from_numpy(captured.values['input']).unsqueeze(0)")
    gate=replace(gate,"                arr, rows = qdq_matrix(value.detach().numpy(),contract_runtime.quantize_t32)","                if list(value.shape) != [1,*SHAPES[key]]: raise RuntimeError('Original QDQ native rank differs')\n                arr, rows = qdq_matrix(value.detach().numpy()[0],contract_runtime.quantize_t32)")
    gate=replace(gate,"return torch.from_numpy(arr)","return torch.from_numpy(arr).unsqueeze(0)")
    gate=replace(gate,"        captured = replay = candidate = mlp = layer = None\n        if runtime is not None:","        result['bindings_restored'] = all(obj.restored for obj in (captured,replay,candidate) if obj is not None)\n        captured = replay = candidate = mlp = layer = None\n        if runtime is not None:")
    ast.parse(gate,feature_version=(3,10))
    if pkg.exists():raise RuntimeError('Immutable package exists')
    pkg.mkdir();unchanged=[]
    for row in json.loads((old/'PACKAGE_MANIFEST.json').read_bytes())['files']:
        n=row['path'];assert sha(old/n)==row['sha256']
        if n in ('SHA256SUMS','m408_mlp_capture.py','m408_component.py','m408_target_component03.py'):continue
        blob=(old/n).read_bytes()
        if n=='m408_gate.py':blob=gate.encode('utf-8')
        elif n=='run_m408_capture.sh':blob=replace(blob.decode('utf-8'),'m408_mlp_capture_03','m408_mlp_capture_04').encode('utf-8')
        else:unchanged.append(n)
        atomic(pkg/n,blob,immutable=True)
    for n in ('m408_mlp_capture04.py','m408_component04.py','m408_target_component04.py'):atomic(pkg/n,(HERE/n).read_bytes(),immutable=True)
    files=sorted(pkg.iterdir());atomic(pkg/'SHA256SUMS',''.join(f'{sha(x)}  {x.name}\n' for x in files).encode('ascii'),immutable=True)
    files=sorted(pkg.iterdir());manifest=dict(file_count=len(files),total_bytes=sum(x.stat().st_size for x in files),files=[dict(path=x.name,bytes=x.stat().st_size,sha256=sha(x)) for x in files]);atomic(pkg/'PACKAGE_MANIFEST.json',encoded(manifest),immutable=True)
    workflow=(HERE/'m408_workflow03.py').read_text(encoding='utf-8')
    for a,c in [('M408-local-MLP-A8-capture-03','M408-local-MLP-A8-capture-04'),('tmp/m40803','tmp/m40804'),
        ('M408-local-MLP-transfer-03','M408-local-MLP-transfer-04'),('M408-local-MLP-A8-board-03','M408-local-MLP-A8-board-04'),
        ('latest_m408_local_mlp_transfer03','latest_m408_local_mlp_transfer04'),('latest_m408_local_mlp_board03','latest_m408_local_mlp_board04'),
        ('m408_mlp_capture_03','m408_mlp_capture_04'),('from m408_mlp_capture import','from m408_mlp_capture04 import')]:assert a in workflow;workflow=workflow.replace(a,c)
    workflow=replace(workflow,"        c = r['component']\n","        if not tc['native_single_batch_preserved'] or tc['bad_shapes_rejected'] != 4: raise ValueError('Native shape component incomplete')\n        c = r['component']\n")
    workflow=replace(workflow,"        if set(r['capture']) != set(SHAPES)","        if r['native_capture_shapes'] != {k:[1,*s] for k,s in SHAPES.items()}: raise ValueError('Native capture shape differs')\n        if set(r['capture']) != set(SHAPES)")
    atomic(HERE/'m408_workflow04.py',workflow.encode('utf-8'),immutable=True)
    control=(HERE/'m408_control04.ps1').read_text(encoding='utf-8')
    for a,c in [('M408-local-MLP-A8-capture-03','M408-local-MLP-A8-capture-04'),('m408_local_mlp_candidate_03','m408_local_mlp_candidate_04'),
        ('latest_m408_local_mlp_preparation03','latest_m408_local_mlp_preparation04'),('latest_m408_local_mlp_support03','latest_m408_local_mlp_support04'),
        ('latest_m408_local_mlp_transfer03','latest_m408_local_mlp_transfer04'),('m408_workflow03.py','m408_workflow04.py'),('tmp/m40803','tmp/m40804'),
        ('M408-local-MLP-A8-board-03','M408-local-MLP-A8-board-04'),('latest_m408_boundary_failure_closure','latest_m408_native_shape_failure_closure')]:assert a in control;control=control.replace(a,c)
    atomic(HERE/'m408_control06.ps1',control.encode('utf-8'),immutable=True)
    support=(HERE/'m408_support03.py').read_text(encoding='utf-8')
    for a,c in [('latest_m408_local_mlp_preparation03','latest_m408_local_mlp_preparation04'),('m408_workflow03','m408_workflow04'),
        ('m408_control04.ps1','m408_control06.ps1'),('m408_support03.py','m408_support04.py'),('tmp/m40803','tmp/m40804'),
        ('m408_mlp_capture_03','m408_mlp_capture_04'),('latest_m408_local_mlp_board03','latest_m408_local_mlp_board04'),
        ('latest_m408_local_mlp_support03','latest_m408_local_mlp_support04'),('M408-local-MLP-support-03','M408-local-MLP-support-04'),
        ('from m408_mlp_capture import','from m408_mlp_capture04 import')]:assert a in support;support=support.replace(a,c)
    support=replace(support,'topology_rejects=4,target_path=',"native_single_batch_preserved=True,bad_shapes_rejected=4,topology_rejects=4,target_path=")
    support=replace(support,'quality_metrics=quality,A8_batches=batches,','quality_metrics=quality,A8_batches=batches,native_capture_shapes={k:[1,*s] for k,s in SHAPES.items()},')
    support=replace(support,"        mutations += [complete+complete", "        for key in ('native_capture_shapes','target_component'):\n            obj=copy.deepcopy(good)\n            if key=='native_capture_shapes':obj[key]['input']=[392,1024]\n            else:obj[key]['bad_shapes_rejected']=3\n            mutations.append(export(obj))\n        mutations += [complete+complete")
    atomic(HERE/'m408_support04.py',support.encode('utf-8'),immutable=True)
    value=dict(status='PASS_M408_REAL_NATIVE_BATCH_CAPTURE_REVISION04',failure_closure_sha256=sha(p),manifest_sha256=sha(pkg/'PACKAGE_MANIFEST.json'),
        real_WSL_original_capture_replay=replay,small_fixture=fixture,unchanged_payloads=unchanged,board_run=False,performance_pass=False,
        source_sha256={n:sha(HERE/n) for n in ('m408_revision04.py','m408_make_shape_fix.py','m408_real_shape_audit.py','m408_capture_shape_check.py','m408_mlp_capture04.py','m408_component04.py','m408_target_component04.py','m408_control06.ps1','m408_workflow04.py','m408_support04.py')})
    p=BASE/'runs/M408-local-MLP-preparation-04/RESULT.json';atomic(p,encoded(value),immutable=True)
    sync('latest_m408_local_mlp_preparation04',dict(status=value['status'],result=p.relative_to(ROOT).as_posix(),sha256=sha(p),manifest_sha256=value['manifest_sha256']),
        f'## M408 原生单batch捕获04准备（2026-10-05）\n\nSHA {sha(p)}；真实冻结同输入WSL捕获/原三维MLP逐位回放、原GELU/两13批及释放通过，4形状错误和4拓扑拒绝。'
        '只保存时去严格单batch，计算/完整board视觉SHA/数学/输入保持，独立04默认关闭；实际新配套支持通过后只本PS捕获级重试，无PL/24层或性能。')
    print('M408_REVISION04_PREPARED',sha(p),value['manifest_sha256'])
if __name__=='__main__':main()
