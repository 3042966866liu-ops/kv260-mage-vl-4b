"""Freeze isolated real-input capture/screen with strict M407 prerequisites."""
import ast
import json
import subprocess
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
from m408_workflow import PKG


def main():
    if PKG.exists(): raise RuntimeError('Immutable package already exists')
    recovery = {n:dict(bytes=len((ROOT/n).read_text(encoding='utf-8-sig').encode('utf-8')),
                       sha256=sha(ROOT/n),full_read=True) for n in
                ('CURRENT_STATE.md','DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md','docsMILESTONES.md')}
    b = json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    keys = {'latest_m407_visual_mlp_contract':'f59ef66f9ad1252272f17f878a9f76f26443ef0962853bd10d8ba80d0266ab89',
            'latest_m407_visual_mlp_layout_closure':'60d40d15fcea261b84acb1a598be0fafb64e7ac54a12a88c59fab8744829aec2'}
    for k,digest in keys.items():
        assert sha(ROOT/b[k]['result']) == b[k]['sha256'] == digest
        assert all(digest in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    old = BASE/'candidates/M406-vision-cost-observer-02'
    assert sha(old/'PACKAGE_MANIFEST.json') == 'ee4b34b88c351187d4362c68bc8e2f3dce74154b78c00440e6d71bb90ffb570f'
    m = json.loads((old/'PACKAGE_MANIFEST.json').read_bytes())
    for row in m['files']: assert sha(old/row['path']) == row['sha256']
    done = subprocess.run(['wsl.exe','-d','Ubuntu-24.04','--','/home/lyy/projects/qwen_baseline/.venv/bin/python','-B',
                          '/mnt/c/Users/30429/Desktop/TeLLMe_FPGA_2026/scripts/optimization/m408_component.py'],capture_output=True)
    if done.returncode: raise RuntimeError(done.stderr.decode('utf-8',errors='replace'))
    checked = json.loads(done.stdout.decode('utf-8').strip())
    assert checked['actual_M207_class'] and checked['actual_frozen_class_AST_executed'] and checked['original_hooks_restored']
    ids = json.loads((old/'M348_SOURCE_IDENTITIES.json').read_bytes())
    path = 'tmp/m223_realtime/m223_realtime_delta/m207_ps_vision_runtime.py'
    assert checked['actual_frozen_class_file_sha256'] == next(x['sha256'] for x in ids['files'] if x['path'] == path)
    PKG.mkdir(parents=True)
    for name in ('EXPECTED.json','frozen_video_identity.py','M348_SOURCE_IDENTITIES.json','m406_vision_observer.py'):
        atomic(PKG/name,(old/name).read_bytes(),immutable=True)
    for name in ('m407_mlp_contract.py','m408_mlp_capture.py','m408_component.py','m408_gate.py','run_m408_capture.sh'):
        raw = (HERE/name).read_bytes()
        if name.endswith('.py'): ast.parse(raw.decode('utf-8-sig'),feature_version=(3,10))
        atomic(PKG/name,raw,immutable=True)
    prerequisite = dict(contract_sha256=keys['latest_m407_visual_mlp_contract'],
        layout_closure_sha256=keys['latest_m407_visual_mlp_layout_closure'],
        layout_sha256='2d9bea77b8868d24fa7775886feb1b9c88b8e768d51b2e192802a439060b03c1',
        default_off=True,selected_layer=12,PS_only=True,local_screen_only=True,
        PL_arithmetic_proven=False,semantic_quality_proven=False,performance_pass=False,
        thresholds=dict(cosine=.999,relative_l2=.02,min_token_cosine=.995),
        capacity=dict(entry_bytes=(1<<30)+(192<<20)+(64<<20),capture_disk_max=32<<20),
        stop='Local screen FAIL stops before PL; no24 layers or changed production precision')
    atomic(PKG/'PREREQUISITE.json',encoded(prerequisite),immutable=True)
    files = sorted(PKG.iterdir()); atomic(PKG/'SHA256SUMS',''.join(f'{sha(p)}  {p.name}\n' for p in files).encode('ascii'),immutable=True)
    files = sorted(PKG.iterdir())
    manifest = dict(schema='M408-local-MLP-A8-capture-v1',default_off=True,file_count=len(files),
                    total_bytes=sum(p.stat().st_size for p in files),files=[dict(path=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in files])
    atomic(PKG/'PACKAGE_MANIFEST.json',encoded(manifest),immutable=True)
    value = dict(status='PASS_M408_PS_CAPTURE_A8_PREPARATION',recovery=recovery,strict_M407_prerequisites=keys,
        WSL_CPU_component=checked,WSL_not_target_board=True,manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),
        file_count=len(files),payload_bytes=manifest['total_bytes'],default_off=True,
        board_run=False,real_input_captured=False,PL_arithmetic_proven=False,semantic_quality_proven=False,performance_pass=False,
        source_sha256={n:sha(HERE/n) for n in ('m408_prepare.py','m408_gate.py','m408_mlp_capture.py','m408_component.py','m408_workflow.py','m408_control.ps1')})
    out = BASE/'runs/M408-local-MLP-preparation-01/RESULT.json';atomic(out,encoded(value),immutable=True)
    sync('latest_m408_local_mlp_preparation',dict(status=value['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out),
        manifest_sha256=value['manifest_sha256']),
        f'## M408 真实第12视觉层MLP捕获/局部A8准备（2026-10-05）\n\nSHA {sha(out)}；严格绑定M407合同和layout补充。'
        '真实WSL Torch CPU执行冻结M207类/原quantizer，原逐位/13批/zero/五拒绝/异常及重复捕获恢复通过；不是目标模型或板端质量。'
        f'{len(files)}载荷默认关闭，最多32MiB捕获，一次原PS视觉及两次局部回放，无profiler/语言/Overlay/DMA。'
        '保留原bias/GELU和完整视觉SHA，局部A8只拒绝筛选，不证明FP16/FTZ PL数学、语义或提速。下一步实际控制/回收检查，再一次PS捕获。')
    print('M408_PREPARED',sha(out),value['manifest_sha256'],len(files),manifest['total_bytes'])


if __name__ == '__main__': main()
