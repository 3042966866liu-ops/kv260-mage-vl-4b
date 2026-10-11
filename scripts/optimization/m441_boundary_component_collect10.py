"""Collect saved tail cases and execute only the not-yet-run latency case."""
import json
import re
import subprocess
import time
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync


def main():
    work=ROOT/'tmp/m441_boundary_component_09'
    fail=BASE/'runs/M441-boundary-component-09/RESULT.json'
    if not fail.exists():
        r=dict(status='FAIL_M441_COMPONENT_EXPECTED_FATAL_MATCH',board=False,M441_DUT=False,
            original_rc=0,gate_rc=1,errors=['ready_error correctly fails earlier at premature tail acceptance; old check expected later READY fatal'],
            evidence=[dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p)) for p in [work/'ready_error.log',work/'ready_error_exit.json',HERE/'m441_boundary_component09.py']])
        atomic(fail,encoded(r),immutable=True)
        sync('latest_m441_boundary_component09',dict(status=r['status'],sha256=sha(fail),result=fail.relative_to(ROOT).as_posix(),board=False),
             f'## M441 边界组件09负例匹配拒绝（2026-10-09）\n\nSHA {sha(fail)}；连续/间断尾128检查通过，错误READY在更早的tail count检查正确失败；旧收集器误要求后续READY fatal。只修证据匹配并复用原字节，不重跑三项；latency项尚未执行。非M441 DUT/板端。')
    result=BASE/'runs/M441-boundary-component-10/RESULT.json';assert not result.exists()
    cases=[]
    for name in ['compile','tail','tail_gaps','ready_error']:
        rc=json.loads((work/(name+'_exit.json')).read_bytes())['tool_rc']
        log=(work/(name+'.log')).read_text(encoding='utf-8-sig',errors='replace')
        fatal=re.findall(r'^Fatal: ([^\r\n]+)',log,re.M)
        if name=='compile':assert rc==0 and 'Built simulation snapshot m441_boundary_component' in log
        elif name=='ready_error':assert fatal==['tail count'] and 'M441_COMPONENT_TAIL_DONE' not in log and 'M441_BOUNDARY_LAST_HOLD' not in log
        else:assert rc==0 and not fatal and log.count('M441_COMPONENT_TAIL_DONE held_posedges=128')==1
        cases.append(dict(name=name,tool_rc=rc,gate_rc=1 if fatal else rc,original_saved_log_reused=True))
    name='latency';assert not (work/(name+'.log')).exists() and not (work/(name+'_exit.json')).exists()
    atomic(work/'latency.args',b'-testplusarg CASE=latency\n-sv_seed 441\n-tclbatch run.tcl\n-log latency.log\n',immutable=True)
    started=time.monotonic()
    with (work/'latency_console.log').open('xb') as stream:
        p=subprocess.Popen(['D:/AMDDesignTools/2026.1/Vivado/bin/xsim.bat','m441_boundary_component','-f','latency.args'],cwd=work,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
        while p.poll() is None:
            if time.monotonic()-started>300:
                atomic(work/'latency_exit.json',encoded(dict(tool_rc=None,retained=True,pid=p.pid)),immutable=True)
                raise RuntimeError('Retained latency process at wall budget')
            time.sleep(.2)
    atomic(work/'latency_exit.json',encoded(dict(tool_rc=p.returncode)),immutable=True)
    log=(work/'latency.log').read_text(encoding='utf-8-sig',errors='replace')
    assert p.returncode==0 and not re.search(r'(?m)^Fatal:|^ERROR:',log) and 'M441_COMPONENT_LATENCY_DONE draws=81920' in log
    samples=re.findall(r'^M441_DELAY channel=(\w+) count=(\d+) sum=(\d+)\s*$',log,re.M)
    assert len(samples)==20 and len({x[0] for x in samples})==10 and all(0<int(total)<=8*int(count) for _,count,total in samples)
    cases.append(dict(name='latency',tool_rc=p.returncode,gate_rc=0))
    r=dict(status='PASS_M441_BOUNDARY_ACTUAL_SV_COMPONENT_ONLY',cases=cases,explicit_fake_signals=True,M441_DUT=False,board=False,performance=False,
        tail_source_reposition_only=True,latency_methods_preserved=True,latency_samples=samples,original_cases_not_rerun=True,
        evidence=[dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p)) for p in sorted(work.glob('*')) if p.is_file()],
        script_sha256=sha(HERE/'m441_boundary_component_collect10.py'))
    atomic(result,encoded(r),immutable=True)
    sync('latest_m441_boundary_component10',dict(status=r['status'],sha256=sha(result),result=result.relative_to(ROOT).as_posix(),board=False),
         f'## M441 有界边界实际SV组件10（2026-10-09）\n\nSHA {sha(result)}；连续/间断VALID均实际停顿128拍后恢复，错误READY提前接受被拒绝，原字节复用无重跑；十个原延迟函数81920抽样0..8。明确fake信号/非DUT，仅组件；下一步实际收集负例及同规模压力。')
    print(r['status'],sha(result),cases,flush=True)


if __name__=='__main__':main()
