"""Audit generated constructor, blocking guards, capacity and local closure."""
import ast
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import m351_workflow as w
import m358_collect_capacity as collector

PKG=w.BASE/'candidates/M358-m357-load-only-03'
OUT=w.BASE/'runs/M358-capacity-support-02/RESULT.json'
def main():
    trees={p.stem:ast.parse(p.read_text(encoding='utf-8'),feature_version=(3,10)) for p in PKG.glob('*.py')}
    allowed=set(sys.stdlib_module_names)|{'numpy','pynq','tokenizers','m276_m254_video_server','m276_video_runtime','m222_video_server','m243_video_server','m241_video_language_runtime','m238_prefill_runtime','video_server','board_runtime','reserved_ddr_pool'}
    closure=json.loads((PKG/'SOURCE_CLOSURE.json').read_text(encoding='utf-8'));allowed|=set(closure['modules'])
    missing=[]
    for name,tree in trees.items():
        for node in ast.walk(tree):
            refs=[]
            if isinstance(node,ast.Import):refs=[a.name.split('.')[0] for a in node.names]
            elif isinstance(node,ast.ImportFrom) and node.module:refs=[node.module.split('.')[0]]
            missing.extend((name,r) for r in refs if r not in trees and r not in allowed)
    assert not missing,missing
    tree=trees['m358_load_only_probe'];checks={}
    fn=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='capacity')
    ns={};exec(compile(ast.Module(body=[fn],type_ignores=[]),'<capacity-check>','exec'),ns)
    for c,m,expected in [(64<<20,64<<20,True),((64<<20)-1,64<<20,False),(64<<20,(64<<20)-1,False)]:
        assert ns['capacity']({'system_bytes':dict(CmaFree=c,MemAvailable=m)})['meets_threshold']==expected
    checks['actual_capacity_boundary_cases']=3
    mainfn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
    block=next(n.value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='BLOCKED_BOARD_METHODS' for t in n.targets))
    methods=ast.literal_eval(block);assert set(methods)=={'_execute','_launch_once','_launch_prepacked','_stage','language_family_many','language_family','lm_head'}
    forbid=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='forbid')
    ns={};exec(compile(ast.Module(body=[forbid],type_ignores=[]),'<forbid-check>','exec'),ns)
    for method in methods:
        blocked=[]
        try:ns['forbid'](method,blocked)()
        except RuntimeError:assert blocked==[method]
        else:raise AssertionError('Inference guard accepted')
    checks['actual_forbid_methods']=len(methods)
    owned=next(n for n in ast.walk(mainfn) if isinstance(n,ast.ClassDef) and n.name=='OwnedBoard')
    ctor=next(n for n in owned.body if isinstance(n,ast.FunctionDef) and n.name=='__init__')
    call=next(n for n in ast.walk(ctor) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='__init__')
    assert ast.unparse(call.args[0])=="CANDIDATE / 'overlay/m120_m89x2_t32.bit'"
    assert ast.unparse(call.args[1])=='*a[1:]' and ast.unparse(call.keywords[0].value)=='kw'
    checks['constructor_only_bit_path_replaced']=True
    # Cross-check names against the exact existing hardware helper, not guessed names.
    ns={};exec(compile(trees['m120_board_common'],'<common-check>','exec'),ns)
    assert ns['KERNEL_NAME']=='mage_m120_m89x2_0' and ns['DMA_NAME']=='axi_dma_prefill'
    s=(PKG/'m358_load_only_probe.py').read_text(encoding='utf-8')
    assert "getattr(restored_overlay,KERNEL_NAME),getattr(restored_overlay,DMA_NAME)" in s
    assert not any(isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id in ('materialize_slot','require_capacity','eligibility') for n in ast.walk(mainfn))
    assert not any(isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr in ('stream','forward','prefill','decode','transfer') for n in ast.walk(mainfn))
    checks.update(no_slot_materialization=True,no_model_or_pl_call=True,python310_syntax=True,recursive_python_missing=0,actual_restore_instance_names=True)
    checks['collector_negative_checks']=collector.selftest()
    ps='C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe'
    tested=subprocess.run([ps,'-NoProfile','-File',str(w.HERE/'m358_control.ps1'),'-Mode','SelfTest'],capture_output=True,text=True,encoding='utf-8')
    assert tested.returncode==0 and 'M358_CONTROL_SELFTEST_PASS' in tested.stdout
    checks['controller_failure_collection_selftest']=True
    raw=dict(status='PASS_OFFLINE_M358_SUPPORT_ONLY',build_id='0x4D333537',checks=checks,manifest_sha256=w.sha(PKG/'PACKAGE_MANIFEST.json'),controller_sha256=w.sha(w.HERE/'m358_control.ps1'),collector_sha256=w.sha(w.HERE/'m358_collect_capacity.py'),rejected_preparations=['01 used guessed restore instance names; 02 had missing transitive board_safety.py; both retained and never uploaded'],board_executed=False)
    w.atomic(OUT,w.encoded(raw),immutable=True);digest=w.sha(OUT)
    w.sync('latest_m358_capacity_support',dict(status=raw['status'],sha256=digest,result=OUT.relative_to(w.ROOT).as_posix()),f'## M358 容量支持离线复核完成\n\nBuild0x4D333537；原构造仅替换bit路径、7个实际forward/事务禁用入口、64MiB边界、实例名、Python3.10语法及递归依赖missing=0通过。15项收集负例及控制故意失败始终收集通过。准备01/02分别因实例名及依赖缺失在离线复核被拒绝，全部保留未上传；仅03可用。证据SHA `{digest}`，不证明板端容量。')
    print(json.dumps(raw))

if __name__=='__main__':main()
