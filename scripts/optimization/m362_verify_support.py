"""Numerical policies untouched; test observer transparency and safe lifecycle."""
import ast
import json
from pathlib import Path
import subprocess
import shutil
import sys
import tempfile
import types
import numpy as np
import m351_workflow as w
from m362_observers import observe_call,tokenizer_proxy,retained_inventory,mapping_inventory
from owned_buffer_release import OwnedBufferRelease
from m362_package_identity import verify_frozen_package,sha
import m362_collect_load_comparison as collector

def check():
    pkg=collector.PKG;trees={p.stem:ast.parse(p.read_text(encoding='utf-8'),feature_version=(3,10)) for p in pkg.glob('*.py')}
    closure=json.loads((pkg/'SOURCE_CLOSURE.json').read_text(encoding='utf-8'))
    allowed=set(sys.stdlib_module_names)|set(closure['modules'])|{'numpy','pynq','tokenizers'}
    missing=[]
    for name,tree in trees.items():
        for n in ast.walk(tree):
            refs=[a.name.split('.')[0] for a in n.names] if isinstance(n,ast.Import) else ([n.module.split('.')[0]] if isinstance(n,ast.ImportFrom) and n.module else [])
            missing.extend((name,r) for r in refs if r not in trees and r not in allowed)
    assert not missing,missing
    src=(pkg/'m362_load_only_probe.py').read_text(encoding='utf-8');tree=trees['m362_load_only_probe']
    assert 'Duplicate original-buffer free refused' not in src and 'OwnedBufferRelease(original_free,release_proven' in src
    assert "super().__init__(TARGET/'overlay/m120_m89x2_t32.bit',*a[1:],**kw)" in src
    assert "TARGET=CANDIDATE if is_candidate else STABLE" in src and "TARGET_SHA=CAND_SHA if is_candidate else STABLE_SHA" in src
    assert src.index("result['target_package_identity']=verify_frozen_package")<src.index('inspected = preflight.inspect')
    stable=w.ROOT/'deployment/mage_vl4b/m175_m120_fixed_text_candidate'
    # Repository historical results are outside the stable package whitelist.
    # Test its real pinned payloads from a clean temporary staging directory.
    with tempfile.TemporaryDirectory() as directory:
        clean=Path(directory);manifest=stable/'PACKAGE_MANIFEST.json'
        shutil.copyfile(manifest,clean/manifest.name)
        for row in json.loads(manifest.read_text(encoding='utf-8'))['files']:
            srcfile=stable/row['path'];assert sha(srcfile)==row['sha256']
            target=clean/row['path'];target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(srcfile,target)
        stable_identity=verify_frozen_package(clean,'406dcca340e4604baeb761445795391c43ec26bd99fa06ffae893d597b17414f',legacy_manifest=True)
    candidate_identity=verify_frozen_package(w.BASE/'candidates/M357-private-activation-01','2e9cbd00d0d01edf05e171674f71f86a94ce389a0658ce6c5466cebb77220d18')
    with tempfile.TemporaryDirectory() as directory:
        root=Path(directory);(root/'payload').write_bytes(b'unchanged')
        manifest=root/'PACKAGE_MANIFEST.json'
        manifest.write_text(json.dumps(dict(files=[dict(path='payload',bytes=9,sha256=sha(root/'payload'))],file_count=1,total_bytes=9)),encoding='utf-8')
        expected=sha(manifest);assert verify_frozen_package(root,expected)['computed_total_bytes']==9
        for alter,restore in [(lambda:(root/'extra').write_bytes(b'x'),lambda:(root/'extra').unlink()),(lambda:(root/'payload').write_bytes(b'wrongsize'),lambda:(root/'payload').write_bytes(b'unchanged'))]:
            alter()
            try:verify_frozen_package(root,expected)
            except RuntimeError:pass
            else:raise AssertionError('Package drift accepted')
            restore()
        data=json.loads(manifest.read_text(encoding='utf-8'));data['file_count']=2;manifest.write_text(json.dumps(data),encoding='utf-8')
        try:verify_frozen_package(root,sha(manifest))
        except RuntimeError:pass
        else:raise AssertionError('Wrong modern count accepted')
    assert not any(isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr in ('forward','stream','transfer','prefill','decode','posix_fadvise','madvise') for n in ast.walk(tree))
    fn=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='capacity');namespace={}
    exec(compile(ast.Module(body=[fn],type_ignores=[]),'<actual-capacity>','exec'),namespace)
    for c,m,expected in [(64<<20,64<<20,True),((64<<20)-1,64<<20,False),(64<<20,(64<<20)-1,False)]:assert namespace['capacity']({'system_bytes':dict(CmaFree=c,MemAvailable=m)})['meets_threshold']==expected
    seen=[];events=[];payload=object();arg=object();kw=object()
    def original(a,*,option):seen.append((a,option));return payload
    marks=[];wrapped=observe_call(original,'transparent',lambda x:marks.append(x) or {},events)
    assert wrapped(arg,option=kw) is payload and seen==[(arg,kw)] and len(marks)==2 and len(events)==1
    fault=ValueError('original sentinel');events=[]
    def fail(*a):raise fault
    try:observe_call(fail,'failure',lambda x:{},events)()
    except ValueError as exc:assert exc is fault and events[0]['exception'].endswith('original sentinel')
    else:raise AssertionError('Original exception swallowed')
    class Tokenizer:
        constant=17
        @staticmethod
        def from_file(path):return (path,payload)
    events=[];proxy=tokenizer_proxy(Tokenizer,observe_call(Tokenizer.from_file,'tokenizer',lambda x:{},events))
    value=proxy.from_file('unchanged');assert value==('unchanged',payload) and proxy.constant==17 and len(events)==1
    calls=[];released=OwnedBufferRelease(lambda:calls.append('backend'),lambda:calls.append('MMIO') or True,lambda:calls.append('record'))
    released()
    for _ in range(7):released()
    assert calls==['MMIO','backend','record']
    calls=[];unsafe=OwnedBufferRelease(lambda:calls.append('backend'),lambda:False,lambda:calls.append('record'))
    try:unsafe()
    except RuntimeError:assert unsafe.state=='owned' and not calls
    else:raise AssertionError('Unproven release accepted')
    calls=[]
    def backend_fail():calls.append('backend');raise fault
    unresolved=OwnedBufferRelease(backend_fail,lambda:True,lambda:calls.append('record'))
    for _ in range(2):
        try:unresolved()
        except (RuntimeError,ValueError):pass
        else:raise AssertionError('Backend failure accepted')
    assert calls==['backend'] and unresolved.state=='unresolved'
    arrays=[np.zeros(1,dtype=np.uint8) for _ in range(7)]
    runtime=types.SimpleNamespace(staged_buffers=arrays[:4],input_buffer=arrays[4],output_buffer=arrays[5],output_buffer_alt=arrays[6])
    language=types.SimpleNamespace(embedding=np.zeros((1,2),dtype=np.float16),norms=dict(norm=np.ones(2)),_norm_archive=types.SimpleNamespace(zip=types.SimpleNamespace(filename='fixture')))
    engine=types.SimpleNamespace(board=runtime,language=language,vision=object(),tokenizer=object())
    assert len(retained_inventory(engine,runtime,arrays)['buffers'])==7
    try:retained_inventory(engine,runtime,list(reversed(arrays)))
    except RuntimeError:pass
    else:raise AssertionError('Wrong ownership accepted')
    with tempfile.TemporaryDirectory() as directory:
        path=Path(directory)/'smaps';path.write_text('1000-2000 r--p 0000 00:00 0 /fixture\nSize: 4 kB\nRss: 2 kB\nAnonymous: 0 kB\n2000-3000 rw-p 0000 00:00 0\nSize: 4 kB\nRss: 1 kB\nAnonymous: 1 kB\n',encoding='utf-8')
        rows=mapping_inventory(path)['mappings'];assert rows[0]['mapping']=='/fixture' and rows[0]['bytes']['Rss']==2048
    controls=subprocess.run(['C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe','-NoProfile','-File',str(w.HERE/'m362_control.ps1'),'-Mode','SelfTest'],capture_output=True,text=True,encoding='utf-8')
    assert controls.returncode==0 and 'M362_CONTROL_SELFTEST_PASS' in controls.stdout,controls.stdout+controls.stderr
    shell=subprocess.run(['wsl.exe','-d','Ubuntu-24.04','--','/bin/bash','-n','/mnt/c/Users/30429/Desktop/TeLLMe_FPGA_2026/'+(pkg/'run_m362_load_only.sh').relative_to(w.ROOT).as_posix()],capture_output=True)
    assert shell.returncode==0,repr(shell.stdout+shell.stderr)
    r=dict(status='PASS_OFFLINE_COMMON_LOAD_SUPPORT',manifest_sha256=w.sha(pkg/'PACKAGE_MANIFEST.json'),common_runner_sha256=w.sha(pkg/'m362_load_only_probe.py'),python310_syntax=True,recursive_missing=0,collector_negative_checks=collector.selftest(),observer_argument_return_exception_identity=True,tokenizer_forwarding=True,retained_buffer_identity_check=True,post_release_MMIO_and_backend_calls_zero=True,unsafe_and_unresolved_release_refused=True,capacity_boundary_checks=3,controller_failure_collection_selftest=True,bash_syntax=True,board_executed=False,performance_pass=False,memory_capacity_proven=False,ordered_cases=['A1','B1','B2','A2'],no_cache_eviction=True,actual_stable_legacy_package=stable_identity,actual_candidate_modern_package=candidate_identity,package_drift_negative_checks=3,compatibility_before_large_asset_hashes=True)
    out=w.BASE/'runs/M362-load-comparison-support-01/RESULT.json';w.atomic(out,w.encoded(r),immutable=True);digest=w.sha(out)
    w.sync('latest_m362_common_load_support',dict(status=r['status'],sha256=digest,result=out.relative_to(w.ROOT).as_posix()),f'## M362 共用加载诊断支持通过（2026-10-02）\n\n稳定/候选仅bit路径变化，原35项完整SHA及构造政策保持；逐SHA/7次分配/Overlay/tokenizer和保留映射检查点准备。幂等释放、观察器原参数/返回/异常、递归missing=0、Python3.10、收集负例、故意失败始终收集及bash-n通过。仅离线，未上传/上板，64MiB余量不改，无forward/FPGA事务。证据SHA `{digest}`。下一步同COM3 sudo后按A-B-B-A逐例只加载、回收及三记录同步；非容量错误停止序列，不重跑Q。')
    print(json.dumps(r))

if __name__=='__main__':check()
