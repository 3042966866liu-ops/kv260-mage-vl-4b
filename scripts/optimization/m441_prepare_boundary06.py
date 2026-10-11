"""Freeze independently bounded pressure inputs; no tool execution."""
import json
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync

def main():
    old=ROOT/'tmp/m441_boundary_protocol_05';out=ROOT/'tmp/m441_boundary_protocol_06'
    previous=BASE/'runs/M441-bounded-boundary-preparation-04/RESULT.json'
    assert sha(previous)=='095dd95a8ee27be8e92b564b64155d7ee749c99b72b217b61afa928454dbf72c'
    p=json.loads(previous.read_bytes());assert not out.exists()
    changed=[]
    for row in p['files']:
        src=ROOT/row['path'];assert sha(src)==row['sha256'];rel=src.relative_to(old);raw=src.read_bytes()
        if src.name=='m441_max_monitor.sv':
            text=raw.decode('utf-8-sig');decl='integer tail_hold_valid_cycles=0;\nbit tail_armed=0,tail_released=0;'
            assert text.count(decl)==1
            text=text.replace(decl,'').replace('module m441_max_monitor;','module m441_max_monitor;\n'+decl)
            raw=text.encode('utf-8')
        elif src.name=='m441_rtl_watchdog.sv':
            text=raw.decode('utf-8-sig');anchor='$display("M441MAX_RTL_TIMEOUT_TRIGGERED ap_done=0 budget_cycles=200");'
            assert text.count(anchor)==1
            text=text.replace(anchor,'$display("M441_BOUNDARY_TIMEOUT_SNAPSHOT requested0=%0d received0=%0d output_stalls=%0d",requested[0],received[0],output_stalls);\n        '+anchor)
            raw=text.encode('utf-8')
        atomic(out/rel,raw,immutable=True)
        if sha(out/rel)!=row['sha256']:changed.append(rel.as_posix())
    (out/'tv/rtldatafile').mkdir(parents=True)
    r=dict(p,status='PREPARED_M441_BOUNDED_BOUNDARY06',previous_preparation_sha256=sha(previous),
        changed_from05=changed,repair='Move declarations before use; export watchdog failure counters. Tail and delay algorithms unchanged.',
        expected=dict(p['expected'],weight_beats_per_shard=10880),readiness='Control policy required before tools',
        files=[dict(path=q.relative_to(ROOT).as_posix(),sha256=sha(q)) for q in sorted(out.rglob('*')) if q.is_file()])
    dest=BASE/'runs/M441-bounded-boundary-preparation-06/RESULT.json';atomic(dest,encoded(r),immutable=True)
    sync('latest_m441_bounded_boundary_preparation06',dict(status=r['status'],result=dest.relative_to(ROOT).as_posix(),sha256=sha(dest),board=False),
         f'## M441 独立有界压力输入06（2026-10-09）\n\nSHA {sha(dest)}；同DUT/最大fixture，声明移到使用前，timeout原生计数；算法不改。旧05保留，4M/4h一次，0工具/板端。')
    print(r['status'],sha(dest),changed,flush=True)

if __name__=='__main__':main()
