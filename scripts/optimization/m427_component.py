"""New partition/baseline boundary checks; reuse previously passed arithmetic."""
import ast,json,subprocess,sys
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
PKG=BASE/'candidates/M427-half-ranges-software-01'
STAGE=ROOT/'tmp/m42701/component_stage'

def prepare():
    ref=BASE/'candidates/M417-layer13-saved-reference-02'
    for row in json.loads((ref/'PACKAGE_MANIFEST.json').read_bytes())['files']:assert sha(ref/row['path'])==row['sha256']
    STAGE.mkdir(exist_ok=False,parents=True)
    for name in ('m426_range02.py','m427_saved_baseline.py'):atomic(STAGE/name,(PKG/name).read_bytes(),immutable=True)
    old=(HERE/'test_m426_range.py').read_text(encoding='utf-8')
    text=old[:old.index('    with torch.inference_mode():')].replace('from m426_range import','from m426_range02 import')
    text=text.replace('layers.append(p(b(inner,dtype,torch.bfloat16),index=i,','layers.append(p(inner if i<2 else b(inner,dtype,torch.bfloat16),index=i,')
    text+='''    verified=[]
    with torch.inference_mode():
        with RangeScope(torch,layers,targets,SELECTED,'original',load,initial,host,sink,lambda label:None) as scope:original=forward()
        assert scope.complete and scope.restored and clean() and not loads
        original_boundaries=tuple(boundary)
        for selected in (tuple(range(2,13)),tuple(range(13,24))):
            boundary.clear();loads.clear()
            with RangeScope(torch,layers,targets,selected,'software',load,initial,host,sink,lambda label:None) as scope:software=forward()
            assert scope.complete and scope.restored and clean() and loads==list(selected) and scope.peak_live_layer_scopes==1
            assert sum(len(batch) for parts in scope.batches.values() for batch in parts.values())==286
            assert boundary[0]==original_boundaries[0] and boundary[1]==original_boundaries[1]
            if selected[0]==13:assert tuple(boundary[:13])==original_boundaries[:13]
            with ExitStack() as stack:
                for i in selected:stack.enter_context(SoftwareMLPBinding(torch,targets[i].mlp,cases[i]['chains'],cases[i]['windows'],initial,host.pack_chain_input,host.parse_chain_output))
                independent=forward()
            assert torch.equal(software,independent) and clean()
            verified.append(dict(selected_layers=list(selected),logical_reference_calls=286,full_output_exact=True,restored=True))
    return dict(partitions=verified,actual_frozen_wrappers_encoder_M207=True,synthetic_narrow_weights_and_attention=True,
        native_BF16_prefix_preserved=True,original_reference_reused_in_both_halves=True,model_quality_or_performance=False)
'''
    ast.parse(text,feature_version=(3,10));atomic(STAGE/'test_m427_partitions.py',text.encode('utf-8'),immutable=True)
    atomic(STAGE/'test_m427_baseline.py',(HERE/'test_m427_baseline.py').read_bytes(),immutable=True)
    entry="""import sys,json
from pathlib import Path
assert sys.flags.isolated
root=Path('/mnt/c/Users/30429/Desktop/TeLLMe_FPGA_2026')
stage=root/'tmp/m42701/component_stage'
ref=root/'deployment/mage_vl4b/optimization_v1/candidates/M417-layer13-saved-reference-02'
sys.path[:0]=[str(stage),str(ref)]
import torch
torch.set_num_threads(1)
from test_m427_partitions import component
from test_m427_baseline import component as baseline_component
print('M427_COMPONENT='+json.dumps(dict(partitions=component(root),baseline=baseline_component())),flush=True)
"""
    atomic(STAGE/'entry.py',entry.encode('utf-8'),immutable=True)
    print('M427_ISOLATED_PARTITION_STAGE_READY')

def run():
    folder=ROOT/'tmp/m42701/component'
    if folder.exists():raise RuntimeError('Immutable component byte logs exist')
    cp=subprocess.run(['wsl.exe','-d','Ubuntu-24.04','--','/home/lyy/projects/qwen_baseline/.venv/bin/python','-I','-B','/mnt/c/Users/30429/Desktop/TeLLMe_FPGA_2026/tmp/m42701/component_stage/entry.py'],capture_output=True,timeout=180)
    atomic(folder/'stdout.bin',cp.stdout,immutable=True);atomic(folder/'stderr.bin',cp.stderr,immutable=True)
    if cp.returncode:raise RuntimeError('Partition component refused; inspect byte logs')
    lines=[x.split('=',1)[1] for x in cp.stdout.decode('utf-8').splitlines() if x.startswith('M427_COMPONENT=')];assert len(lines)==1
    value=json.loads(lines[0]);assert len(value['partitions']['partitions'])==2 and len(value['baseline']['negative_checks'])==9
    r=dict(status='PASS_M427_ISOLATED_PARTITIONS_AND_SAVED_BASELINE_COMPONENT',component=value,
        stdout_sha256=sha(folder/'stdout.bin'),stderr_sha256=sha(folder/'stderr.bin'),staged_sources={p.name:sha(p) for p in STAGE.iterdir()},manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),board_run=False,actual_quality_pass=False,performance_pass=False)
    out=BASE/'runs/M427-half-component-01/RESULT.json';atomic(out,encoded(r),immutable=True)
    sync('latest_m427_half_component',dict(status=r['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out),manifest_sha256=r['manifest_sha256']),
        f'## M427 两个固定半区及保存原版身份组件（2026-10-06）\n\nSHA {sha(out)}；真实冻结包装/encoder/M207、明确合成窄权重/Attention，两个11层各286批流式结果与独立同时绑定逐位一致，原版与BF16前缀不改、钩子恢复。保存原始数组的完整SHA/边界/文件身份9项负例通过；root所有权在离线fixture中明确模拟，真实板端必须uid0，不宣称实际模型质量。无板端执行或硬件/性能。')
    print('M427_COMPONENT_SYNC',sha(out))

if __name__=='__main__':{'prepare':prepare,'run':run}[sys.argv[1]]()
