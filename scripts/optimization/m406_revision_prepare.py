"""Prove the original scalar serialization mismatch and freeze a narrow revision."""
import ast
import importlib.util
import json
import sys
import numpy as np
from m351_workflow import ROOT, BASE, HERE, atomic, encoded, sha, sync

PKG = BASE / 'candidates/M406-vision-cost-observer-02'
OLD = BASE / 'candidates/M406-vision-cost-observer-01'

def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value

def change(text, old, new):
    assert text.count(old) == 1, (old, text.count(old))
    return text.replace(old, new)

def main():
    recovery = {}
    for name in ('CURRENT_STATE.md', 'DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md', 'docsMILESTONES.md'):
        text = (ROOT/name).read_text(encoding='utf-8-sig')
        recovery[name] = dict(sha256=sha(ROOT/name), lines=len(text.splitlines()), full_read=True)
    board = json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    previous = board['latest_m406_vision_cost_board']
    assert previous['sha256'] == sha(ROOT/previous['result']) == '5048e793ecd0bc224b031f732dd0626e2d5a81dc5eee434a87b540a84ec2450d'
    failure = json.loads((ROOT/previous['result']).read_bytes())
    assert failure['visual_forward_calls'] == 0 and failure['component_pass']
    assert failure['errors'][0]['message'] == 'Original preprocessed tensors differ'
    assert sha(OLD/'PACKAGE_MANIFEST.json') == '4f4279ec40a1778a0f7690a4ebb761ced83013529813bf103ea7a4731e7b060b'
    frozen = BASE/'candidates/M403-tail-performance-01/m368_video_contract.py'
    gold = module('frozen_m368_contract', frozen)
    prepfile = ROOT/'deployment/mage_vl4b/m277_m276_fixed_window_board_candidate/m273_latest_multiscale_contract.py'
    assert sha(prepfile) == 'c5826f77f95f4b3d6fbf1c406d9f341650316958ba5cfa1ba2467605eef3273a'
    preprocess = module('frozen_m273_contract', prepfile).preprocess
    identity = module('fixed_video_identity', OLD/'frozen_video_identity.py')
    folder = ROOT/'release_staging/m328_release_video_addon_20260926_v3/fixtures'
    frames = []
    for name, digest in identity.FRAMES.items():
        assert sha(folder/name) == digest
        frames.append(np.load(folder/name, allow_pickle=False))
    frames = np.ascontiguousarray(np.stack(frames))
    import hashlib
    assert hashlib.sha256(frames.tobytes()).hexdigest() == identity.STACK_SHA
    tensors = preprocess(np.ascontiguousarray(frames[-1:]))
    expected = json.loads((OLD/'EXPECTED.json').read_bytes())['preprocessed']
    normalized = {k: gold.tensor(v) for k,v in sorted(tensors.items())}
    assert normalized == expected
    direct = {k: dict(shape=list(v.shape), dtype=str(v.dtype), bytes=int(v.nbytes),
                     sha256=hashlib.sha256(v.tobytes()).hexdigest()) for k,v in sorted(tensors.items())}
    different = {k:dict(direct=direct[k], frozen=normalized[k]) for k in direct if direct[k] != normalized[k]}
    assert set(different) == {'merged_visual_tokens','view_count'}
    for row in different.values():
        assert row['direct']['shape'] == [] and row['frozen']['shape'] == [1]
        assert {k:v for k,v in row['direct'].items() if k != 'shape'} == {k:v for k,v in row['frozen'].items() if k != 'shape'}
    closure = dict(status='PASS_M406_FAILURE_CAUSE_PROVEN_OFFLINE', original_raw_sha256=previous['sha256'],
        recovery=recovery, original_gate_rc=1, visual_forward_calls=0, model_constructed=False,
        same_fixed_frames_all_sha_verified=True, preprocessing_source_sha256=sha(prepfile),
        frozen_serializer_sha256=sha(frozen), exact_frozen_preprocessing_match=normalized,
        differences=different, original_byte_hashes_unchanged=True,
        cause='scalar shape serialization only; frozen np.ascontiguousarray maps 0-D to [1]',
        actual_board_component_pass=True, actual_backend=failure['backend_before'],
        no_new_board_run=True, performance_pass=False, prior_failure_preserved=True)
    out=BASE/'runs/M406-vision-failure-closure-01/RESULT.json'
    atomic(out, encoded(closure), immutable=True)
    sync('latest_m406_vision_failure_closure',dict(status=closure['status'],sha256=sha(out),result=out.relative_to(ROOT).as_posix()),
         f'## M406视觉前置失败闭合（2026-10-05）\n\nSHA {sha(out)}；保留原FAIL SHA {previous["sha256"]}。'
         '同四帧文件/stack和冻结M273预处理本地复现，全部字节SHA不变；仅merged_visual_tokens/view_count两个零维标量的记录shape []与原serializer [1]不同。'
         '原八项板端Torch逐位组件已通过，0模型构造/视觉前向/Overlay/DMA/语言；正常退出，无待回收DMA。'
         '下一步仅修正记录器使用原连续化/finite检查，不删除任何完整参考校验；原包01/原日志不覆盖。')
    gate=(OLD/'m406_vision_gate.py').read_text(encoding='utf-8')
    old='''def tensor(value):
    return dict(shape=list(value.shape), dtype=str(value.dtype), bytes=int(value.nbytes),
                sha256=hashlib.sha256(value.tobytes()).hexdigest())'''
    new='''def tensor(value):
    import numpy as np
    x = np.ascontiguousarray(value)
    if not np.isfinite(x).all(): raise FloatingPointError('Nonfinite model output')
    return dict(shape=list(x.shape), dtype=str(x.dtype), bytes=x.nbytes,
                sha256=hashlib.sha256(x.tobytes()).hexdigest())'''
    gate=change(gate,old,new)
    gate=change(gate,'m406_vision_cost_observation_01','m406_vision_cost_observation_02')
    gate=change(gate,"if {k: tensor(v) for k, v in sorted(tensors.items())} != expected['preprocessed']:",
                "result['preprocessed'] = {k: tensor(v) for k, v in sorted(tensors.items())}\n        if result['preprocessed'] != expected['preprocessed']:")
    ast.parse(gate, feature_version=(3,10))
    if PKG.exists(): raise RuntimeError('Revision package exists')
    PKG.mkdir()
    manifest=json.loads((OLD/'PACKAGE_MANIFEST.json').read_bytes())
    unchanged=[]
    for row in manifest['files']:
        name=row['path']
        assert sha(OLD/name)==row['sha256']
        if name=='SHA256SUMS':continue
        blob=(OLD/name).read_bytes()
        if name=='m406_vision_gate.py':blob=gate.encode('utf-8')
        elif name=='run_m406_vision.sh':blob=change(blob.decode('utf-8'),'m406_vision_cost_observation_01','m406_vision_cost_observation_02').encode('utf-8')
        else:unchanged.append(name)
        atomic(PKG/name,blob,immutable=True)
    files=sorted(PKG.iterdir())
    atomic(PKG/'SHA256SUMS',''.join(f'{sha(p)}  {p.name}\n' for p in files).encode('ascii'),immutable=True)
    files=sorted(PKG.iterdir())
    value=dict(manifest,files=[dict(path=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in files],
               total_bytes=sum(p.stat().st_size for p in files))
    atomic(PKG/'PACKAGE_MANIFEST.json',encoded(value),immutable=True)
    namespace={}; exec(compile(ast.Module(body=[next(n for n in ast.parse(gate).body if isinstance(n,ast.FunctionDef) and n.name=='tensor')],type_ignores=[]),'<revised-serializer>','exec'),dict(hashlib=hashlib),namespace)
    fn=namespace['tensor']
    assert {k:fn(v) for k,v in tensors.items()}==expected
    for sample in (np.asarray(2,np.int64),np.ones((3,4),np.float32)[:,::2],np.zeros((0,2),np.float32)):
        assert fn(sample)==gold.tensor(sample)
    try:fn(np.asarray([np.nan],np.float32))
    except FloatingPointError:pass
    else:raise AssertionError('finite check removed')
    # Explicit routing changes only; retain original checked producer/collector logic.
    workflow=(HERE/'m406_workflow.py').read_text(encoding='utf-8').replace('from m406_prepare import PKG','from m406_revision_prepare import PKG')
    for a,b in [('tmp/m406','tmp/m40602'),('M406-vision-transfer-01','M406-vision-transfer-02'),('M406-vision-cost-board-01','M406-vision-cost-board-02')]:workflow=workflow.replace(a,b)
    atomic(HERE/'m406_workflow02.py',workflow.encode('utf-8'),immutable=True)
    control=(HERE/'m406_control02.ps1').read_text(encoding='utf-8')
    for a,b in [('M406-vision-cost-observer-01','M406-vision-cost-observer-02'),('m406_vision_cost_candidate_01','m406_vision_cost_candidate_02'),('m406_workflow.py','m406_workflow02.py'),('tmp/m406','tmp/m40602'),('M406-vision-cost-board-01','M406-vision-cost-board-02')]:control=control.replace(a,b)
    atomic(HERE/'m406_control03.ps1',control.encode('utf-8'),immutable=True)
    support=(HERE/'m406_support.py').read_text(encoding='utf-8')
    for a,b in [('from m406_prepare import PKG','from m406_revision_prepare import PKG'),('import m406_workflow as workflow','import m406_workflow02 as workflow'),('tmp/m406','tmp/m40602'),('m406_control.ps1','m406_control03.ps1'),('m406_support.py','m406_support03.py'),('m406_workflow.py','m406_workflow02.py'),('M406-vision-observer-support-01','M406-vision-observer-support-03')]:support=support.replace(a,b)
    atomic(HERE/'m406_support03.py',support.encode('utf-8'),immutable=True)
    value=dict(status='PASS_OFFLINE_M406_SERIALIZER_REVISION',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),
               prior_closure_sha256=sha(out), unchanged_payloads=unchanged, exact_same_input_preprocessed_match=True,
               scalar_strided_empty_finite_checks=True, original_observer_unchanged=True,
               source_sha256={n:sha(HERE/n) for n in ('m406_revision_prepare.py','m406_workflow02.py','m406_control03.ps1','m406_support03.py')},
               board_run=False, performance_pass=False)
    out=BASE/'runs/M406-vision-observer-preparation-02/RESULT.json';atomic(out,encoded(value),immutable=True)
    sync('latest_m406_vision_observer_preparation',dict(status=value['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out),manifest_sha256=value['manifest_sha256']),
         f'## M406视觉观察02准备（2026-10-05）\n\nSHA {sha(out)}；仅修正已证实的原serializer连续化/finite及记录实际preprocessed，另用独立02结果目录。'
         '同输入所有预处理参考形状/类型/字节/SHA精确通过，标量/strided/空数组/非finite拒绝检查通过；观察器/原模型和五份参考载荷不变。'
         '下一步核对实际02控制/collector路由和拒绝检查后执行同失败PS视觉级；不运行语言或新增性能对照。')
    print('M406_REVISION_PREPARED',value['manifest_sha256'])

if __name__=='__main__':main()
