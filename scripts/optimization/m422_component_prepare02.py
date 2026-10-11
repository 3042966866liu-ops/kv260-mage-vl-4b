"""Clean staging and isolated Linux CPU fixture, no board control."""
import ast,json,subprocess
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync

def main():
    b=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes());e=b['latest_m422_shared_DMA_integration_audit'];assert sha(ROOT/e['result'])==e['sha256']
    pkg=BASE/'candidates/M422-borrowed-visual-component-02'
    if pkg.exists():raise RuntimeError('Immutable component staging exists')
    pkg.mkdir()
    for name,source in [('m422_borrowed_visual.py',HERE/'m422_borrowed_visual.py'),('test_m422_borrowed_visual.py',HERE/'test_m422_borrowed_visual.py'),('board_safety.py',HERE/'board_safety.py'),('m411_mlp_binding.py',BASE/'candidates/M420-layers12-13-full-visual-02/m411_mlp_binding.py')]:
        ast.parse(source.read_text(encoding='utf-8-sig'),feature_version=(3,10));atomic(pkg/name,source.read_bytes(),immutable=True)
    harness="import sys\nfrom pathlib import Path\nsys.path.insert(0,str(Path(__file__).resolve().parent))\nfrom test_m422_borrowed_visual import main\nmain()\n"
    atomic(pkg/'component_entry.py',harness.encode('utf-8'),immutable=True)
    names=sorted(p.name for p in pkg.iterdir());atomic(pkg/'SHA256SUMS',''.join(f'{sha(pkg/n)}  {n}\n' for n in names).encode('ascii'),immutable=True)
    files=sorted(pkg.iterdir());m=dict(file_count=len(files),total_bytes=sum(p.stat().st_size for p in files),files=[dict(path=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in files]);atomic(pkg/'PACKAGE_MANIFEST.json',encoded(m),immutable=True)
    command=['wsl.exe','-d','Ubuntu-24.04','--','/home/lyy/projects/qwen_baseline/.venv/bin/python','-I','-B','/mnt/c/Users/30429/Desktop/TeLLMe_FPGA_2026/'+(pkg/'component_entry.py').relative_to(ROOT).as_posix()]
    cp=subprocess.run(command,capture_output=True,timeout=60)
    out=ROOT/'tmp/m42202/component';atomic(out/'stdout.txt',cp.stdout,immutable=True);atomic(out/'stderr.txt',cp.stderr,immutable=True)
    if cp.returncode:raise RuntimeError('Clean fixture rejected: '+cp.stderr.decode('utf-8',errors='replace')[-2500:])
    lines=[x.split('=',1)[1] for x in cp.stdout.decode('utf-8').splitlines() if x.startswith('M422_COMPONENT=')];assert len(lines)==1;component=json.loads(lines[0])
    assert component['fake_DMA_MMIO_memory'] and component['timeout_preserves_original_owner'] and component['extra_allocate_or_free_calls']==0 and component['real_array_geometry_bytes']==33484832
    v=dict(status='PASS_M422_ISOLATED_BORROWED_DMA_COMPONENT_ONLY',prior_audit_sha256=e['sha256'],manifest_sha256=sha(pkg/'PACKAGE_MANIFEST.json'),component=component,isolated_Linux_clean_staging=True,python310_syntax=True,return_code=cp.returncode,stdout_sha256=sha(out/'stdout.txt'),stderr_sha256=sha(out/'stderr.txt'),source_sha256={n:sha(HERE/n) for n in ('m422_borrowed_visual.py','test_m422_borrowed_visual.py','m422_component_prepare02.py')},board_run=False,real_capacity_proven=False,numerical_full_request_pass=False,performance_pass=False,
        next_concrete_step='Prepare one integrated fixed-original/candidate video numerical gate using borrowed original seven DMA. Check complete visual features, full logits/KV/counters against saved M420/M421 and safe ownership before performance.')
    p=BASE/'runs/M422-borrowed-component-02/RESULT.json';atomic(p,encoded(v),immutable=True)
    sync('latest_m422_borrowed_DMA_component',dict(status=v['status'],result=p.relative_to(ROOT).as_posix(),sha256=sha(p),manifest_sha256=v['manifest_sha256'],board_run=False,performance_pass=False),f'## M422 原七DMA借用组件（2026-10-06）\n\nSHA {sha(p)}；隔离WSL-I clean staging、实际33484832B普通数组几何，明确fake DMA/MMIO/policy，默认关闭/未seal/语言活动/无事务证明/尺寸身份/包wireSHA/异常缓存清除/活动timeout保留等{len(component["negative_checks"])}负例，0额外allocate/free，两个输出轮换。非真实CMA/PL或完整请求PASS；下一步一次完整接入数值，再性能，不扩层。')
    print('M422_BORROWED_COMPONENT_SYNC',sha(p),len(component['negative_checks']))
if __name__=='__main__':main()
