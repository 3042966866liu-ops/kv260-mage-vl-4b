"""Run one isolated actual-oracle fixture, preserving stdout/stderr bytes."""
import json,subprocess
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
def main():
    folder=ROOT/'tmp/m42601/component'
    if folder.exists():raise RuntimeError('Original component outputs exist; reuse or explicitly repair, never overwrite')
    stage=ROOT/'tmp/m42601/component_stage'
    ref=BASE/'candidates/M417-layer13-saved-reference-02'
    manifest=json.loads((ref/'PACKAGE_MANIFEST.json').read_bytes())
    for row in manifest['files']:assert sha(ref/row['path'])==row['sha256']
    cp=subprocess.run(['wsl.exe','-d','Ubuntu-24.04','--','/home/lyy/projects/qwen_baseline/.venv/bin/python','-I','-B','/mnt/c/Users/30429/Desktop/TeLLMe_FPGA_2026/tmp/m42601/component_stage/entry.py'],capture_output=True,timeout=180)
    atomic(folder/'stdout.bin',cp.stdout,immutable=True);atomic(folder/'stderr.bin',cp.stderr,immutable=True)
    if cp.returncode:raise RuntimeError('Component rc='+str(cp.returncode)+'; inspect original byte files')
    lines=[x.split('=',1)[1] for x in cp.stdout.decode('utf-8').splitlines() if x.startswith('M426_COMPONENT=')];assert len(lines)==1
    value=json.loads(lines[0]);assert value['logical_reference_calls']==572 and value['independent_all_bindings_full_output_exact'] and len(value['negative_checks'])==9
    r=dict(status='PASS_M426_ISOLATED_CUMULATIVE_ORACLE_COMPONENT',component=value,
        stdout_sha256=sha(folder/'stdout.bin'),stderr_sha256=sha(folder/'stderr.bin'),
        staged_sources={p.name:sha(p) for p in stage.iterdir()},reference_manifest_sha256=sha(ref/'PACKAGE_MANIFEST.json'),
        board_run=False,real_model_quality_pass=False,performance_pass=False,
        note='Actual frozen wrappers/encoder/M207 and unchanged exact arithmetic; synthetic narrow MLP weights and Attention, real392x1024 boundaries; all22 orchestration and partial restoration only.')
    out=BASE/'runs/M426-range-component-01/RESULT.json';atomic(out,encoded(r),immutable=True)
    sync('latest_m426_range_component',dict(status=r['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out),board_run=False,performance_pass=False),f'## M426 干净隔离22层精确软件参考组件（2026-10-06）\n\nSHA {sha(out)}；实际冻结包装/encoder/M207与不改的M409精确算术，合成窄MLP权重/Attention明确。真实392×1024边界、572参考调用、全部22层流式执行与独立同时绑定全输出一致，9项异常/部分进入/恢复拒绝检查。仅离线组件，不是实际模型质量或板端性能；原stdout/stderr字节保留。')
    print('M426_COMPONENT_SYNC',sha(out),json.dumps(value))
if __name__=='__main__':main()
