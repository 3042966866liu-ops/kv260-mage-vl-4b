"""Prepare/collect one CPU-only owner recovery capability test; no board access."""
import ast
import base64
import hashlib
import importlib.util
import json
import re
import sys
import tempfile
from unittest.mock import patch
from m351_workflow import ROOT,HERE,BASE,sha,atomic,encoded,sync

PKG=BASE/'candidates/M400-owner-sentinel-01'


def prepare():
    if PKG.exists():raise RuntimeError('Fresh sentinel staging required')
    spec=importlib.util.spec_from_file_location('sentinel_test',HERE/'m400_gdb_cpu_sentinel.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    checks=[]
    with tempfile.TemporaryDirectory(dir=ROOT/'tmp/m400') as tmp:
        # Real release wrapper and worker; only replace the infinite fixture loop.
        tree=ast.parse(m.SENTINEL)
        fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
        assert isinstance(fn.body[-1],ast.While)
        fn.body[-1]=ast.Return(value=ast.Name(id='owner',ctx=ast.Load()))
        tree.body.pop()  # no automatic main invocation
        ast.fix_missing_locations(tree)
        ns={'__file__':str(ROOT/'tmp/m400'/tmp/'cpu_sentinel.py')}
        exec(compile(tree,'cpu_fixture','exec'),ns)
        owner=ns['main']();owner.close();owner.close()
        assert owner.closed and owner.counts==[1]*7 and owner.releases==list(range(6,-1,-1))
        checks.append('actual CPU worker drain and seven actual release wrappers exactly once')
        stage=ROOT/'tmp/m400'/tmp
        names=('m400_gdb_cpu_sentinel.py','owned_buffer_release.py')
        for name in names:atomic(stage/name,(HERE/name).read_bytes())
        runner=b'''#!/usr/bin/env bash\nset -euo pipefail\n[[ $EUID == 0 && $# == 1 ]] || exit 65\ntask_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)\nexec /usr/local/share/pynq-venv/bin/python -B "$task_dir/m400_gdb_cpu_sentinel.py" --enable-cpu-sentinel "$1"\n'''
        atomic(stage/'run_m400_cpu_sentinel.sh',runner)
        files=[dict(path=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(stage.iterdir()) if p.suffix!='.ready']
        # Fixture readiness is outside package closure.
        ready=stage/'cpu_sentinel.ready'
        if ready.exists():ready.unlink()
        files=[f for f in files if f['path']!='cpu_sentinel.ready']
        manifest=dict(schema='M400-CPU-sentinel-only-v1',files=files,file_count=len(files),total_bytes=sum(f['bytes'] for f in files))
        atomic(stage/'PACKAGE_MANIFEST.json',encoded(manifest))
        with patch.object(m,'HERE',stage):
            m.verify(sha(stage/'PACKAGE_MANIFEST.json'));checks.append('exact manifest whitelist bytes and SHA')
            for name in ('m400_gdb_cpu_sentinel.py','owned_buffer_release.py'):
                p=stage/name;old=p.read_bytes();p.write_bytes(old+b'\n')
                try:m.verify(sha(stage/'PACKAGE_MANIFEST.json'))
                except RuntimeError:checks.append('payload drift refused '+name)
                else:raise AssertionError('Drift accepted')
                p.write_bytes(old)
            try:m.verify('0'*64)
            except RuntimeError:checks.append('manifest drift refused')
            else:raise AssertionError('Manifest accepted')
        PKG.mkdir(parents=True)
        for p in stage.iterdir():atomic(PKG/p.name,p.read_bytes(),immutable=True)
    for name in ('m400_gdb_cpu_sentinel.py','owned_buffer_release.py'):
        ast.parse((PKG/name).read_bytes(),feature_version=(3,10))
    value=dict(status='PASS_OFFLINE_CPU_SENTINEL_PREPARATION_ONLY',checks=checks,
               manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),gdb_tested=False,
               original_owner_attached=False,resources_recovered=False,new_overlay_loads=0,new_DMA_allocations=0,
               source_sha256=sha(HERE/'m400_cpu_sentinel_workflow.py'))
    out=BASE/'runs/M400-owner-sentinel-preparation-01/RESULT.json'
    atomic(out,encoded(value),immutable=True);d=sha(out)
    sync('latest_m400_owner_sentinel_preparation',dict(status=value['status'],result=out.relative_to(ROOT).as_posix(),sha256=d,manifest_sha256=value['manifest_sha256']),
         f'## M400 CPU哨兵回收能力包准备（2026-10-04）\n\nSHA `{d}`；独立普通CPU worker与七个真实释放包装器幂等检查、manifest/载荷拒绝检查通过，3.10仅语法。只准备独立GDB能力试验，不附加原PID22715、不加载Overlay或DMA。原owner/七DMA仍挂起；哨兵通过并同步后才评估原进程受控入口，不能据此回收板端资源。')
    print(json.dumps(value))


def decode(text):
    hs=re.findall(r'(?m)^M400_SENTINEL_SHA256=([0-9a-f]{64})\s*$',text)
    cs=re.findall(r'(?m)^M400_SENTINEL_CHUNK=(\d+)/(\d+):([A-Za-z0-9+/=]+)\s*$',text)
    if len(hs)!=1 or not cs or len(cs)!=int(cs[0][1]):raise RuntimeError('Incomplete/duplicate sentinel export')
    parts=[]
    for i,(n,total,b64) in enumerate(cs):
        p=base64.b64decode(b64,validate=True)
        if int(n)!=i or int(total)!=len(cs) or not 0<len(p)<=900:raise RuntimeError('Chunk order/size differs')
        parts.append(p)
    raw=b''.join(parts);d=hashlib.sha256(raw).hexdigest()
    if d!=hs[0]:raise RuntimeError('Raw SHA differs')
    return raw,d,json.loads(raw)


def collect():
    log=ROOT/'tmp/m400/sentinel_run.log'
    text=log.read_text(encoding='utf-8-sig');raw,d,r=decode(text)
    if r['manifest_sha256']!=sha(PKG/'PACKAGE_MANIFEST.json') or not r['CPU_sentinel_only']:
        raise RuntimeError('Sentinel identity differs')
    if any(r[k] for k in ('original_board_owner_attached','new_overlay_loads','new_DMA_allocations')):
        raise RuntimeError('Sentinel scope exceeded')
    if r['status']=='PASS_CPU_SENTINEL_ORIGINAL_OWNER_CLOSE':
        if r['gate_return_code'] or r['gdb_return_code'] or r['proof']!=dict(pid=r['sentinel_pid'],closed=True,counts=[1]*7,releases=list(range(6,-1,-1)),thread='MainThread'):
            raise RuntimeError('Sentinel PASS evidence differs')
    elif r['status']!='FAIL_CPU_SENTINEL_GDB' or r['gate_return_code']!=1 or not r.get('traceback'):
        raise RuntimeError('Unknown sentinel status')
    if '__M400_SENTINEL_RUN_RC_'+str(r['gate_return_code'])+'__' not in text:
        raise RuntimeError('Original sentinel return code absent')
    out=BASE/'runs/M400-owner-sentinel-board-01/BOARD_RESULT.json'
    atomic(out,raw,immutable=True);atomic(out.parent/'UART.log',log.read_bytes(),immutable=True)
    sync('latest_m400_owner_sentinel_board',dict(status=r['status'],result=out.relative_to(ROOT).as_posix(),sha256=d,
         original_owner_recovered=False,stable_overlay_restored=False),
         f'## M400 独立CPU哨兵板端结果（2026-10-04）\n\nSHA `{d}`，原rc{r["gate_return_code"]}，{r["status"]}；仅自有CPU子进程，原PID22715未附加、七DMA未释放、稳定Overlay未恢复。原失败及旧性能保持。哨兵PASS只证明此CPU试验的GDB/main-thread/worker/release路径；FAIL不能扩大到原owner，保留资源并记录阻塞。')
    print(json.dumps(r,ensure_ascii=False))


if __name__=='__main__':
    {'Prepare':prepare,'Collect':collect}[sys.argv[1]]()
