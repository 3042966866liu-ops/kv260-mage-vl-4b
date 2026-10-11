"""Freeze one read-only in-owner inspection after CPU capability proof."""
import ast
import copy
import json
import threading
from types import SimpleNamespace as N
from m351_workflow import ROOT,HERE,BASE,sha,atomic,encoded,sync
from m400_live_owner_inspect import inspect_owner


def fixture():
    allocations=[N(nbytes=b,freebuffer=N(state='owned')) for b in [6963200]*4+[389152,2621440,2621440]]
    # Explicit fake memory/MMIO/release wrapper types, never release calls.
    Release=type('OwnedBufferRelease',(),{})
    for i,b in enumerate(allocations):b.address=4096+i*8192;b.freebuffer=Release();b.freebuffer.state='owned'
    class Model:
        grouped_attention_calls=0
        def _family(self):pass
    model=Model()
    rt=N(logical_calls=0,host_calls=0,_m368_closed=False,kernel=None,dma=None,staged_buffers=allocations[:4],
         input_buffer=allocations[4],output_buffer=allocations[5],output_buffer_alt=allocations[6])
    policy=N(active=False,ever=True,completed=True,sealed=True,thread=None,stop_reason=None,safe=lambda:True)
    scope=N(closed=False,retained=True,invoked=True,maps={},identities={},bindings=[],observer=None,
            family_rows=[],result=None,rows=[],original_family=model._family,resident=lambda:True,
            barrier=lambda:None,check_unchanged=lambda:None,
            tail=N(closed=False,retained=False,invoked=False,bindings=[],selected=[]))
    rows=[dict(bytes=b.nbytes,address=b.address) for b in allocations]
    event=threading.Event();event.set()
    return dict(layer_scope=scope,policy=policy,runtime=rt,engine=N(language=model,board=rt),
         result=dict(model_forward_calls=0,fpga_transactions=1,blocked_inference_attempts=[],released_buffers=[],allocated_buffers=rows),
         allocations=allocations,registry=N(entries=[1]),stopped=event,initialized=True,
         base=N(physical_address=lambda b:b.address,transaction_snapshot=lambda *a:dict(EXPLICIT_FAKE_MMIO=True)))


def main():
    pkg=BASE/'candidates/M400-owner-live-inspect-01'
    if pkg.exists():raise RuntimeError('Fresh live inspection package required')
    board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    previous=board['latest_m400_owner_sentinel_board']
    if sha(ROOT/previous['result'])!=previous['sha256'] or previous['status']!='PASS_CPU_SENTINEL_ORIGINAL_OWNER_CLOSE':
        raise RuntimeError('Actual CPU capability proof required')
    ns=fixture();assert inspect_owner(ns)['pristine_source_abort_conditions_passed']
    checks=['actual inspector with explicit fake MMIO/buffers passes pristine case']
    for key,val in [('policy_active',True),('scope_maps',{'unexpected':1}),('tail_selected',[1]),
                    ('logical_calls',1),('buffer_state','released'),('extra_forward',1),('family_changed',True)]:
        ns=fixture()
        if key=='policy_active':ns['policy'].active=val
        elif key=='scope_maps':ns['layer_scope'].maps=val
        elif key=='tail_selected':ns['layer_scope'].tail.selected=val
        elif key=='logical_calls':ns['runtime'].logical_calls=val
        elif key=='buffer_state':ns['allocations'][0].freebuffer.state=val
        elif key=='extra_forward':ns['result']['model_forward_calls']=val
        else:ns['engine'].language._family=lambda:None
        try:inspect_owner(ns)
        except (RuntimeError,AttributeError):checks.append(key+' refuses')
        else:raise RuntimeError('Unsafe live condition accepted')
    audit=json.loads((BASE/'runs/M400-owner-audit-board-01/BOARD_RESULT.json').read_bytes())
    original=BASE/'candidates/M400-tail-layer-01'
    pin=dict(pid=audit['owner']['pid'],start_ticks=audit['owner']['start_ticks'],command=audit['owner']['command'],
             original_package='/home/ubuntu/m400_tail_layer_candidate_01',original_manifest_sha256=sha(original/'PACKAGE_MANIFEST.json'),
             original_raw='/home/ubuntu/m400_tail_layer_01/B1/load-memory.json',
             original_raw_sha256='de7f6e0e144fe03529a414f3983e2e6e515bc8a7d7185400daf5e026bcd549e9')
    pkg.mkdir(parents=True)
    for n in ('m400_live_owner_inspect.py','m400_live_inspect_driver.py','m400_owner_readonly_probe.py'):
        ast.parse((HERE/n).read_bytes(),feature_version=(3,10));atomic(pkg/n,(HERE/n).read_bytes(),immutable=True)
    atomic(pkg/'PIN.json',encoded(pin),immutable=True)
    runner=b'''#!/usr/bin/env bash\nset -euo pipefail\n[[ $EUID == 0 && $# == 1 ]] || exit 65\ntask_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)\nexec /usr/local/share/pynq-venv/bin/python -B "$task_dir/m400_live_inspect_driver.py" --enable-read-only-owner-inspection "$1"\n'''
    atomic(pkg/'run_m400_live_inspect.sh',runner,immutable=True)
    rows=[dict(path=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(pkg.iterdir())]
    atomic(pkg/'PACKAGE_MANIFEST.json',encoded(dict(files=rows,file_count=len(rows),total_bytes=sum(r['bytes'] for r in rows))),immutable=True)
    out=BASE/'runs/M400-owner-live-inspect-preparation-01/RESULT.json'
    value=dict(status='PASS_OFFLINE_LIVE_OWNER_INSPECTION_PREPARATION',manifest_sha256=sha(pkg/'PACKAGE_MANIFEST.json'),
               checks=checks,CPU_sentinel_proof_sha256=previous['sha256'],
               inspector_uses_explicit_fakes_in_offline_tests=True,original_owner_attached=False,
               original_owner_resume_and_stop_planned=True,resources_released=False,new_overlay_loads=0)
    atomic(out,encoded(value),immutable=True);d=sha(out)
    sync('latest_m400_owner_live_inspect_preparation',dict(status=value['status'],result=out.relative_to(ROOT).as_posix(),sha256=d,manifest_sha256=value['manifest_sha256']),
         f'## M400 原owner内部只读检查准备（2026-10-04）\n\nSHA `{d}`；复用板端CPU哨兵能力，原PID/startticks/命令/完整原包与失败raw锁定。8项实际检查器/明确假MMIO和缓冲拒绝检查通过。只在精确原保留循环短暂恢复Python以读取scope/family/线程/七资源身份，再挂起；不调用close、不释放/重载Overlay，不根据寄存器独立释放。尚未执行，原资源保留。')
    print(value['status'],value['manifest_sha256'])


if __name__=='__main__':main()
