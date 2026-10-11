"""Versioned diagnostic topology repair; original board failure stays immutable."""
import ast,json,subprocess,sys
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
OLD=BASE/'candidates/M426-all-FP32-MLP-software-01'
NEW=BASE/'candidates/M426-all-FP32-MLP-software-02'
STAGE=ROOT/'tmp/m42603/topology_stage'

PREFIX='''def prefix_evidence(vision, progress_cls, boundary_cls, linear_cls, torch):
    rows = {}
    for index in (0, 1):
        outer = vision.encoder.layers[index]
        if type(outer) is not progress_cls or outer.index != index:
            raise RuntimeError('Original BF16 progress identity differs')
        inner = outer.layer
        if type(inner) is boundary_cls or type(inner).__name__ != 'MageVLVisionEncoderLayer':
            raise RuntimeError('Original BF16 prefix must have no conversion wrapper')
        for name in ('layer_norm1', 'layer_norm2'):
            if getattr(inner, name).weight.dtype != torch.bfloat16:
                raise RuntimeError('Original BF16 prefix norm precision differs')
        for part, shape in (('fc1', (1024, 4096)), ('fc2', (4096, 1024))):
            mod = getattr(inner.mlp, part)
            if type(mod) is not linear_cls or mod.name != f'encoder.layers.{index}.mlp.{part}' or (mod.in_features, mod.out_features) != shape or mod.output_dtype != torch.bfloat16 or mod.bias is None or mod.bias.dtype != torch.bfloat16:
                raise RuntimeError('Original BF16 prefix Linear identity/precision differs')
        rows[str(index)] = dict(progress=type(outer).__name__, encoder=type(inner).__name__,
            conversion_wrapper=False, target_dtype='torch.bfloat16', output_dtype='torch.bfloat16')
    return rows


'''

def prepare():
    b=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    fail=b['latest_m426_range_software_board'];r=json.loads((ROOT/fail['result']).read_bytes())
    assert sha(ROOT/fail['result'])==fail['sha256'] and all(fail['sha256'] in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    assert r['status']=='FAIL_M426_SOFTWARE_RANGE' and r['visual_forward_calls']==0 and r['visual_owner_closed'] and r['bindings_restored']
    assert r['errors'][0]['message']=='Frozen two-layer BF16 prefix/boundary differs'
    prior=(OLD/'m426_range.py').read_text(encoding='utf-8')
    updated=prior.replace('def resolve(',PREFIX+'def resolve(',1)
    updated=updated.replace('    targets = {}; evidence = {}','    prefix_evidence(vision, progress_cls, boundary_cls, linear_cls, torch)\n    targets = {}; evidence = {}',1)
    before="""        boundary = outer.layer
        wanted = torch.bfloat16 if index < 2 else torch.float32
"""
    after="""        if index < 2:
            continue
        boundary = outer.layer
        wanted = torch.float32
"""
    assert before in updated;updated=updated.replace(before,after,1)
    # All streaming, arithmetic, retry and restoration statements remain exact.
    cls=lambda t:ast.dump(next(n for n in ast.parse(t).body if isinstance(n,ast.ClassDef) and n.name=='RangeScope'),include_attributes=False)
    assert cls(prior)==cls(updated)
    atomic(HERE/'m426_range02.py',updated.encode('utf-8'),immutable=True)
    STAGE.mkdir(parents=True,exist_ok=False)
    atomic(STAGE/'m426_range02.py',updated.encode('utf-8'),immutable=True)
    atomic(STAGE/'test_m426_topology.py',(HERE/'test_m426_topology.py').read_bytes(),immutable=True)
    entry="""import sys,json
from pathlib import Path
assert sys.flags.isolated
root=Path('/mnt/c/Users/30429/Desktop/TeLLMe_FPGA_2026')
stage=root/'tmp/m42603/topology_stage'
ref=root/'deployment/mage_vl4b/optimization_v1/candidates/M417-layer13-saved-reference-02'
sys.path[:0]=[str(stage),str(ref)]
from test_m426_topology import component
print('M426_TOPOLOGY_COMPONENT='+json.dumps(component(root)),flush=True)
"""
    atomic(STAGE/'entry.py',entry.encode('utf-8'),immutable=True)
    p=ROOT/'tmp/m227_runtime_base/m227_runtime_base_patch/ps_vision_runtime.py'
    source=p.read_text(encoding='utf-8');assert 'if target_dtype == self.compute_dtype:\n                continue' in source
    record=dict(status='CONFIRMED_M426_DIAGNOSTIC_PREFIX_TOPOLOGY_ERROR',original_failed_raw_sha256=fail['sha256'],
        constructor_source_sha256=sha(p),source_path=p.relative_to(ROOT).as_posix(),
        cause='M90 compute BF16: native BF16 layers0-1 skip precision wrapper; M426 erroneously required a conversion wrapper for every layer.',
        visual_forward_calls_before_failure=0,PS_owner_closed=True,no_DMA_or_PL=True,
        streaming_RangeScope_AST_unchanged=True,original_packet_sha256=sha(OLD/'PACKAGE_MANIFEST.json'),
        feature_thresholds_unchanged=True,oracle_unchanged=True,repaired_selector_sha256=sha(HERE/'m426_range02.py'),board_retry_started=False)
    out=BASE/'runs/M426-topology-repair-audit-01/RESULT.json';atomic(out,encoded(record),immutable=True)
    sync('latest_m426_topology_repair',dict(status=record['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out)),
        f'## M426 入口结构拒绝原因确认（2026-10-06）\n\nSHA {sha(out)}；原失败 {fail["sha256"]}保留，0视觉forward/DMA/PL，PS owner已关闭。冻结M90 compute BF16对同精度层跳过包装，因此0–1层没有M196包装；诊断此前错误要求全24层都有包装。修正版仅分支检查原BF16两层直连及FP32其余22层，原RangeScope AST/精确算术/阈值不变，先做真实冻结包装构造组件，尚未重试。')
    print('M426_TOPOLOGY_REPAIR_STAGE_READY',sha(out))

def package():
    folder=ROOT/'tmp/m42603/topology_component02'
    if folder.exists():raise RuntimeError('Component byte logs already exist')
    cp=subprocess.run(['wsl.exe','-d','Ubuntu-24.04','--','/home/lyy/projects/qwen_baseline/.venv/bin/python','-I','-B','/mnt/c/Users/30429/Desktop/TeLLMe_FPGA_2026/tmp/m42603/topology_stage/entry.py'],capture_output=True,timeout=60)
    atomic(folder/'stdout.bin',cp.stdout,immutable=True);atomic(folder/'stderr.bin',cp.stderr,immutable=True)
    if cp.returncode:raise RuntimeError('Topology component failed; original byte logs preserved')
    lines=[x.split('=',1)[1] for x in cp.stdout.decode('utf-8').splitlines() if x.startswith('M426_TOPOLOGY_COMPONENT=')];assert len(lines)==1
    value=json.loads(lines[0]);assert value['selected_layers']==list(range(2,24)) and len(value['negative_checks'])==8
    b=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    plan=json.loads((OLD/'PLAN.json').read_bytes())
    oldfail=b['latest_m426_range_software_board'];plan['prerequisites'].append(dict(path='/home/ubuntu/m426_range_software_01/BOARD_RESULT.json',sha256=oldfail['sha256']))
    plan['diagnostic_topology_repair']='Native BF16 prefix0-1 has no precision wrapper; remaining22 must have exact FP32-to-BF16 wrappers. No math/selection/threshold changes.'
    NEW.mkdir(exist_ok=False)
    gate=(OLD/'m426_gate.py').read_text(encoding='utf-8').replace('/home/ubuntu/m426_range_software_01/','/home/ubuntu/m426_range_software_02/').replace('from m426_range import resolve,RangeScope,SELECTED','from m426_range02 import resolve,RangeScope,SELECTED,prefix_evidence')
    needle="targets,result['targets']=resolve(runtime.vision,M206ProgressLayer,M196PrecisionBoundary,M207FP32GemmW4Linear,torch)"
    assert needle in gate;gate=gate.replace(needle,"result['prefix_topology']=prefix_evidence(runtime.vision,M206ProgressLayer,M196PrecisionBoundary,M207FP32GemmW4Linear,torch)\n        "+needle)
    for n,t in [('m426_gate.py',gate),('m426_range02.py',(HERE/'m426_range02.py').read_text(encoding='utf-8')),('m426_export.py',(OLD/'m426_export.py').read_text(encoding='utf-8').replace('/home/ubuntu/m426_range_software_01/','/home/ubuntu/m426_range_software_02/'))]:
        ast.parse(t,feature_version=(3,10));atomic(NEW/n,t.encode('utf-8'),immutable=True)
    for n in ('EXPECTED_VISUAL.json','SOURCE_IDENTITIES.json'):atomic(NEW/n,(OLD/n).read_bytes(),immutable=True)
    atomic(NEW/'PLAN.json',encoded(plan),immutable=True)
    runner=(OLD/'run_m426.sh').read_text(encoding='utf-8').replace('/home/ubuntu/m426_range_software_01','/home/ubuntu/m426_range_software_02')
    atomic(NEW/'run_m426.sh',runner.encode('utf-8'),immutable=True)
    atomic(NEW/'SHA256SUMS',''.join(f'{sha(p)}  {p.name}\n' for p in sorted(NEW.iterdir())).encode('ascii'),immutable=True)
    files=sorted(NEW.iterdir());manifest=dict(file_count=len(files),total_bytes=sum(p.stat().st_size for p in files),files=[dict(path=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in files]);atomic(NEW/'PACKAGE_MANIFEST.json',encoded(manifest),immutable=True)
    workflow=(HERE/'m426_workflow02.py').read_text(encoding='utf-8').replace('M426-all-FP32-MLP-software-01','M426-all-FP32-MLP-software-02').replace('M426-range-software-board-01','M426-range-software-board-02').replace('M426-range-transfer-01','M426-range-transfer-02').replace('tmp/m42602','tmp/m42603')
    needle="        for i in range(2,24):"
    assert needle in workflow
    workflow=workflow.replace(needle,"        if set(r['prefix_topology'])!={'0','1'} or any(x['conversion_wrapper'] is not False or x['encoder']!='MageVLVisionEncoderLayer' or x['target_dtype']!='torch.bfloat16' or x['output_dtype']!='torch.bfloat16' for x in r['prefix_topology'].values()):raise ValueError('Native BF16 prefix evidence differs')\n"+needle,1)
    atomic(HERE/'m426_workflow03.py',workflow.encode('utf-8'),immutable=True)
    control=(HERE/'m426_control02.ps1').read_text(encoding='utf-8').replace('M426-all-FP32-MLP-software-01','M426-all-FP32-MLP-software-02').replace('m426_range_software_candidate_01','m426_range_software_candidate_02').replace('M426-range-software-board-01','M426-range-software-board-02').replace('m42602','m42603').replace('m426_workflow02.py','m426_workflow03.py')
    atomic(HERE/'m426_control03.ps1',control.encode('utf-8'),immutable=True)
    record=dict(status='PREPARED_M426_NATIVE_BF16_PREFIX_REPAIR',component=value,manifest_sha256=sha(NEW/'PACKAGE_MANIFEST.json'),
        original_failed_raw_sha256=oldfail['sha256'],original_numeric_component_reused=b['latest_m426_range_component']['sha256'],
        source_sha256={n:sha(HERE/n) for n in ('m426_control03.ps1','m426_workflow03.py','m426_range02.py','test_m426_topology.py')},
        component_stdout_sha256=sha(folder/'stdout.bin'),component_stderr_sha256=sha(folder/'stderr.bin'),board_run=False,performance_pass=False)
    out=BASE/'runs/M426-topology-repair-preparation-01/RESULT.json';atomic(out,encoded(record),immutable=True)
    sync('latest_m426_range_preparation',dict(status=record['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out),manifest_sha256=record['manifest_sha256'],board_run=False,performance_pass=False),
        f'## M426 原BF16直连包装修复包（2026-10-06）\n\nSHA {sha(out)}；实际冻结M90包装循环/M206/M196/M207组件及8项拓扑负例通过，原572算术/流式组件复用不重跑。02包/03控制使用独立结果和日志，保留01失败；原选层、A8/FP16/FTZ数学及feature阈值不变。修复仅诊断拓扑，尚未上板重试。')
    print('M426_REPAIRED_PACKAGE_READY',sha(out),record['manifest_sha256'])

def support():
    old=(HERE/'m426_support.py').read_text(encoding='utf-8')
    text=old.replace('import m426_workflow as w','import m426_workflow03 as w').replace('m426_control.ps1','m426_control03.ps1').replace('m426_workflow.py','m426_workflow03.py').replace('m426_support.py','m426_support03.py').replace('tmp/m42601','tmp/m42603').replace('M426-range-support-01','M426-range-support-02')
    text=text.replace("    for i in range(2,24):", "    r['prefix_topology']={str(i):dict(conversion_wrapper=False,encoder='MageVLVisionEncoderLayer',target_dtype='torch.bfloat16',output_dtype='torch.bfloat16') for i in (0,1)}\n    for i in range(2,24):",1)
    text=text.replace("'bad-original-SHA'):","'bad-original-SHA','missing-prefix','wrapped-prefix'):",1)
    text=text.replace("        else:bad['original_visual']['sha256']='0'*64", "        elif label=='missing-prefix':bad['prefix_topology'].pop('0')\n        elif label=='wrapped-prefix':bad['prefix_topology']['1']['conversion_wrapper']=True\n        else:bad['original_visual']['sha256']='0'*64",1)
    text=text.replace("for n in ('m426_control03.ps1','m426_workflow03.py','m426_support03.py')", "for n in ('m426_control03.ps1','m426_workflow03.py','m426_support03.py','m426_range02.py','test_m426_topology.py')")
    atomic(HERE/'m426_support03.py',text.encode('utf-8'),immutable=True)
    # The sole runner difference is a fresh immutable result directory.
    oldrunner=(OLD/'run_m426.sh').read_text(encoding='utf-8');newrunner=(NEW/'run_m426.sh').read_text(encoding='utf-8')
    assert newrunner.replace('m426_range_software_02','m426_range_software_01')==oldrunner
    cp=subprocess.run(['wsl.exe','-d','Ubuntu-24.04','--','/bin/bash','-n','/mnt/c/Users/30429/Desktop/TeLLMe_FPGA_2026/'+(NEW/'run_m426.sh').relative_to(ROOT).as_posix()],capture_output=True)
    atomic(ROOT/'tmp/m42603/bash.stdout.bin',cp.stdout,immutable=True);atomic(ROOT/'tmp/m42603/bash.stderr.bin',cp.stderr,immutable=True)
    if cp.returncode:raise RuntimeError('Repaired runner syntax rejected')
    cp=subprocess.run([sys.executable,'-X','utf8','-B',str(HERE/'m426_support03.py')],capture_output=True)
    atomic(ROOT/'tmp/m42603/support.stdout.bin',cp.stdout,immutable=True);atomic(ROOT/'tmp/m42603/support.stderr.bin',cp.stderr,immutable=True)
    if cp.returncode:raise RuntimeError('Repaired collector support refused; inspect original byte logs')
    print(cp.stdout.decode('utf-8').strip())

if __name__=='__main__':
    {'prepare':prepare,'package':package,'support':support}[sys.argv[1]]()
