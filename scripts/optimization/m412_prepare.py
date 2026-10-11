"""Immutable separate retry at M411 capacity failure level, with user authorization."""
import ast,json
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
from m412_workflow import PKG
from m412_policy import POLICY
def main():
    if PKG.exists():raise RuntimeError('Immutable package exists')
    recovery={n:dict(full_read=True,sha256=sha(ROOT/n),characters=len((ROOT/n).read_text(encoding='utf-8-sig'))) for n in ('CURRENT_STATE.md','DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md','docsMILESTONES.md')}
    b=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    for key in ('latest_m409_reference_board','latest_m410_visual_descriptor','latest_m410_visual_chain','latest_m410_visual_lower_closure','latest_m411_complete_mlp_capacity_closure','latest_m365_staged_layer_closure','latest_m368_video_closure'):
        e=b[key];assert sha(ROOT/e['result'])==e['sha256'];assert all(e['sha256'] in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    old=BASE/'candidates/M411-complete-visual-MLP-01';plan=json.loads((old/'PLAN.json').read_bytes())
    plan['actual_CMA_reserve_bytes']=None;plan['independent_admission']=POLICY
    plan['scope']='Independent fixed392-row MLP only; allocate exact3.281265MiB seven buffers then seal all new public DMA allocation. Original production64MiB/source/services/boot/DTB/CMA policy unchanged.'
    plan['prior_failed_attempt']=b['latest_m411_complete_mlp_board'];plan['user_authorization']='2026-10-06: 你就试试啊，应该放的下的'
    for row in plan['reused_packages']:
        local=BASE/'candidates'/('M410-visual-linear-01' if 'm410' in row['directory'] else 'M409-saved-MLP-reference-01')
        assert sha(local/'PACKAGE_MANIFEST.json')==row['manifest_sha256']
        for p in json.loads((local/'PACKAGE_MANIFEST.json').read_bytes())['files']:assert sha(local/p['path'])==p['sha256']
    component=BASE/'runs/M412-policy-component-01/RESULT.json';assert json.loads(component.read_bytes())['status']=='PASS_M412_ACTUAL_INDEPENDENT_POLICY_COMPONENT'
    PKG.mkdir()
    for n in ('m412_gate.py','m412_policy.py','m412_export.py'):
        raw=(HERE/n).read_bytes();ast.parse(raw,feature_version=(3,10));atomic(PKG/n,raw,immutable=True)
    for n in ('m411_mlp_binding.py','test_m411_binding.py'):
        raw=(old/n).read_bytes();ast.parse(raw,feature_version=(3,10));atomic(PKG/n,raw,immutable=True)
    atomic(PKG/'PLAN.json',encoded(plan),immutable=True)
    runner=(old/'run_m411_mlp.sh').read_bytes().replace(b'M411',b'M412').replace(b'm411',b'm412')
    atomic(PKG/'run_m412_mlp.sh',runner,immutable=True)
    files=sorted(PKG.iterdir());atomic(PKG/'SHA256SUMS',''.join(f'{sha(p)}  {p.name}\n' for p in files).encode('ascii'),immutable=True)
    files=sorted(PKG.iterdir());manifest=dict(file_count=len(files),total_bytes=sum(p.stat().st_size for p in files),files=[dict(path=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in files]);atomic(PKG/'PACKAGE_MANIFEST.json',encoded(manifest),immutable=True)
    v=dict(status='PASS_M412_COMPLETE_MLP_INDEPENDENT_PREPARATION_ONLY',recovery=recovery,manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),file_count=manifest['file_count'],total_bytes=manifest['total_bytes'],
        actual_policy_component_sha256=sha(component),inverse_AST_source_diff_sha256=sha(BASE/'runs/M412-policy-source-diff-01/RESULT.json'),admission_policy=POLICY,
        original_binding_and_actual_Torch_component_same_SHA={n:sha(old/n) for n in ('m411_mlp_binding.py','test_m411_binding.py')},protocol=plan['protocol'],hardware_executed=False,
        source_sha256={n:sha(HERE/n) for n in ('m412_prepare.py','m412_gate.py','m412_policy.py','m412_export.py','m412_workflow.py','m412_control.ps1')})
    p=BASE/'runs/M412-complete-MLP-preparation-01/RESULT.json';atomic(p,encoded(v),immutable=True)
    sync('latest_m412_complete_mlp_preparation',dict(status=v['status'],result=p.relative_to(ROOT).as_posix(),sha256=sha(p),manifest_sha256=v['manifest_sha256']),
        f'## M412 独立视觉MLP实际需求准入准备（2026-10-06）\n\nSHA {sha(p)}；用户授权独立尝试，M411原FAIL保留。复用M364政策依据/M365及M368已分配封锁路线，只新固定392行入口：实际七DMA3,440,656B成功后封锁新增公共分配，256MiB普通RSS增长预算＋64MiB普通可用余量，CmaFree仅记录。原数学/计时/参考/35SHA/49源码及生产64MiB均保持。实际新Owner内存/计划分配/部分失败回收/拒绝和allocator恢复组件通过，显式fake MMIO/allocator；无新硬件或容量证明。只完整MLP数值后原预定AB预热＋ABBABAAB8完整段，不扩24层。')
    print('M412_PREPARED',sha(p),v['manifest_sha256'],manifest['file_count'],manifest['total_bytes'])
if __name__=='__main__':main()
