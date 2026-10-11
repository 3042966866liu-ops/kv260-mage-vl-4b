"""Finite, default-disabled local simulation controller; freeze before launch."""
import argparse
import json
import shutil
import subprocess
import time
import traceback
from m351_workflow import ROOT, BASE, HERE, encoded, sha, sync
from m441_host_io08 import atomic
from m441_supervisor04 import boot, process, classify, log_snapshot
from m441_sim_evidence20 import collect, collect_timeout, fault_checks

RUN=BASE/'runs/M441-W2-W4-simulation-coverage-19'
PREP=RUN/'PREPARATION.json'
OUT=ROOT/'tmp/m441_sim_coverage_19'
RUNTIME={'TempBreakPointFile.txt','xsim_script.tcl','xsim.covinfo','xsim.crvsdump','xsimcrash.log','xsimkernel.log'}


def progress(stage,**extra):
    atomic(RUN/'PROGRESS.json',encoded(dict(stage=stage,updated_epoch=time.time(),**extra)))


def snapshot(folder):
    rows=[dict(path=p.relative_to(folder).as_posix(),sha256=sha(p),runtime=p.name in RUNTIME) for p in sorted(folder.rglob('*')) if p.is_file()]
    assert any(r['path'].endswith('xsimk.exe') and not r['runtime'] for r in rows)
    return rows


def verify_snapshot(folder,rows):
    assert rows
    for row in rows:
        assert row['runtime']==((folder/row['path']).name in RUNTIME)
        if not row['runtime']:assert sha(folder/row['path'])==row['sha256'],row['path']


def tool(cmd,sim,stem,budget,global_deadline):
    # Existing attempt is never relaunched. Receipt only permits saved collection.
    receipt_path=sim/(stem+'_exit.json')
    if receipt_path.exists():return json.loads(receipt_path.read_bytes())
    assert not (sim/(stem+'.log')).exists() and not (sim/(stem+'_console.log')).exists(),'Existing incomplete attempt: observe/collect only'
    started=time.monotonic();start_boot=boot();wall=False;rc=None;next_live=0
    with (sim/(stem+'_console.log')).open('xb') as stream:
        proc=subprocess.Popen(cmd,cwd=sim,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
        identity=process(proc.pid);born=identity.get('creation_FILETIME')
        progress('RUNNING_'+stem,tool_pid=proc.pid,tool_creation_FILETIME=born,path=sim.relative_to(ROOT).as_posix())
        while proc.poll() is None:
            if time.monotonic()>=next_live:
                state=process(proc.pid,born);current=boot()
                live=dict(status=classify(start_boot,current,state),process=state,boot=current,start_boot=start_boot,
                          elapsed_s=time.monotonic()-started,log=log_snapshot(sim/(stem+'.log')))
                atomic(sim/(stem+'_LIVE.json'),encoded(live));next_live=time.monotonic()+30
            if time.monotonic()-started>budget or time.monotonic()>global_deadline:wall=True;break
            time.sleep(1)
        if not wall:rc=proc.returncode
    log=(sim/(stem+'.log')).read_text(encoding='utf-8-sig',errors='replace') if (sim/(stem+'.log')).is_file() else ''
    observed=stem=='timeout' and 'M441MAX_RTL_TIMEOUT_TRIGGERED ap_done=0 budget_cycles=200' in log and 'M441MAX bounded timeout expired before ap_done' in log
    gate=1 if wall or observed or rc else 0
    if stem=='pressure' and (log.count('M441MAX_DONE cycles=')!=1 or 'Fatal:' in log or 'ERROR:' in log):gate=1
    r=dict(original_rc=rc,gate_rc=gate,timeout_observed=observed,software_wall_budget_exceeded=wall,
           elapsed_s=time.monotonic()-started,process_pid=proc.pid,process_creation_FILETIME=born,
           process_retained=wall,process_killed=False,preparation_sha256=sha(PREP),command=cmd)
    atomic(receipt_path,encoded(r),immutable=True)
    print(stem,rc,gate,r['elapsed_s'],flush=True)
    if wall:raise RuntimeError('Fixed budget exceeded; original simulator retained; no next case')
    return r


def compile_once(p,deadline):
    sim=OUT/'W2_max/verilog'
    saved=RUN/'COMPILE.json'
    if saved.exists():
        r=json.loads(saved.read_bytes());assert r['status']=='PASS_M441_SUPPLEMENTAL_COMPILE19'
        verify_snapshot(sim/'xsim.dir',r['snapshot']);return r
    cmd=['D:/AMDDesignTools/2026.1/Vivado/bin/xelab.bat','xil_defaultlib.apatb_m89x_runtime_kernel_top','xil_defaultlib.glbl','xil_defaultlib.m441_max_monitor','xil_defaultlib.m441_rtl_watchdog',
         '-Oenable_linking_all_libraries','-prj','m441_max.prj','-debug','typical','-v','2']
    for lib in ('smartconnect_v1_0','axi_protocol_checker_v1_1_12','axi_protocol_checker_v1_1_13','axis_protocol_checker_v1_1_11','axis_protocol_checker_v1_1_12','xil_defaultlib','unisims_ver','xpm','floating_point_v7_1_22','floating_point_v7_0_27','uvm'):cmd+=['-L',lib]
    cmd+=['-relax']
    for inc in ('svr','axivip','svtb','file_agent','m89x_runtime_kernel_subsystem'):cmd+=['-i','./'+inc]
    cmd+=['-s','m441_coverage19','-log','compile.log']
    receipt=tool(cmd,sim,'compile',p['compile_wall_budget_s'],deadline)
    log=(sim/'compile_console.log').read_text(encoding='utf-8-sig',errors='replace')
    ok=receipt['original_rc']==0 and 'Built simulation snapshot m441_coverage19' in log and 'ERROR:' not in log
    rows=snapshot(sim/'xsim.dir') if ok else []
    r=dict(status='PASS_M441_SUPPLEMENTAL_COMPILE19' if ok else 'FAIL_M441_SUPPLEMENTAL_COMPILE19',receipt=receipt,snapshot=rows,
           preparation_sha256=sha(PREP),board=False,evidence=[dict(path=q.relative_to(ROOT).as_posix(),sha256=sha(q)) for q in (sim/'compile_exit.json',sim/'compile_console.log',sim/'compile.log')])
    atomic(saved,encoded(r),immutable=True)
    sync('latest_m441_simulation19_compile',dict(status=r['status'],result=saved.relative_to(ROOT).as_posix(),sha256=sha(saved),board=False),
         f'## M441补充仿真19编译（2026-10-10）\n\nSHA {sha(saved)}；{r["status"]}，冻结同原DUT/实际VIP，新参数化观察器只覆盖缺口，不重综合/布线。snapshot SHA固定，未称数值/协议通过。')
    assert ok,r['status'];return r


def run_case(p,case,compiled,deadline,negative=False):
    original=OUT/'W2_max/verilog/xsim.dir';rows=compiled['snapshot'];digest=sha(RUN/'COMPILE.json')
    name='timeout' if negative else case['name'];folder=OUT/'timeout' if negative else ROOT/case['path'];sim=folder/'verilog'
    if negative and not folder.exists():
        source=OUT/'W2_max'
        for row in case['files']:
            src=ROOT/row['path'];rel=src.relative_to(source);atomic(folder/rel,src.read_bytes(),immutable=True)
        (folder/'tv/rtldatafile').mkdir(parents=True)
    if name!='W2_max' and not (sim/'xsim.dir').exists():
        verify_snapshot(original,rows);shutil.copytree(original,sim/'xsim.dir')
    verify_snapshot(sim/'xsim.dir',rows)
    for row in case['files']:assert sha(ROOT/row['path'])==row['sha256']
    stem='timeout' if negative else 'pressure';e=case['expected']
    args='-testplusarg UVM_VERBOSITY=UVM_NONE\n-testplusarg UVM_TESTNAME=m89x_runtime_kernel_test_lib\n-testplusarg UVM_TIMEOUT=20000000000000\n-sv_seed 441\n--noieeewarnings\n'
    for key,value in [('WORDS',e['output_words']),('READS',e['weight_beats_per_shard']),('CALLS',e['mac_calls_per_shard']),('DESCS',e['descriptors']),('CYCLES',case['cycle_budget'])]:args+='-testplusarg '+key+'='+str(value)+'\n'
    if negative:args+='-testplusarg M441MAX_EXPECT_TIMEOUT\n'
    args+='-tclbatch '+('timeout.tcl' if negative else 'pressure.tcl')+'\n-log '+stem+'.log\n'
    atomic(sim/(stem+'.args'),args.encode('utf-8'),immutable=True)
    receipt=tool(['D:/AMDDesignTools/2026.1/Vivado/bin/xsim.bat','m441_coverage19','-f',stem+'.args'],sim,stem,600 if negative else case['wall_budget_s'],deadline)
    verify_snapshot(sim/'xsim.dir',rows)
    if negative:return collect_timeout(receipt,digest)
    saved=sim/'pressure_result'
    if not saved.exists():
        saved.mkdir()
        for source in (folder/'tv/rtldatafile').glob('*.dat'):shutil.copyfile(source,saved/source.name)
    return collect(case,receipt,digest)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run',action='store_true');a=ap.parse_args()
    assert a.run,'Default disabled: explicit --run required'
    p=json.loads(PREP.read_bytes())
    for field in ('controller','collector','generator'):assert sha(ROOT/p[field]['path'])==p[field]['sha256']
    policy=json.loads((RUN/'CONTROL_POLICY20.json').read_bytes())
    assert policy['preparation_sha256']==sha(PREP)
    for row in policy['files']:assert sha(ROOT/row['path'])==row['sha256']
    for c in p['cases']:
        for row in c['files']:assert sha(ROOT/row['path'])==row['sha256']
    assert not (RUN/'START.json').exists(),'Already started: observe/collect only'
    now=boot();deadline=time.monotonic()+p['global_wall_budget_s']
    atomic(RUN/'START.json',encoded(dict(start_epoch=time.time(),boot=now,preparation_sha256=sha(PREP))),immutable=True)
    results=[]
    try:
        fault_checks();compiled=compile_once(p,deadline)
        for name in p['order']:
            negative=name=='timeout';case=next(c for c in p['cases'] if c['name']==('W2_max' if negative else name))
            progress('STARTING_CASE',case=name)
            r=run_case(p,case,compiled,deadline,negative);results.append(dict(case=name,status=r['status'],sha256=sha(RUN/(name+'_RESULT.json'))))
            assert r['status'].startswith('PASS_'),r['status']
            progress('CASE_CLOSED',case=name,results=results)
        r=dict(status='PASS_M441_W2_W4_SUPPLEMENTAL_SIMULATION_CLOSED19',build_id=p['build_id'],results=results,
               preparation_sha256=sha(PREP),board=False,performance=False,production_changed=False)
        atomic(RUN/'RESULT.json',encoded(r),immutable=True)
        sync('latest_m441_simulation19_closed',dict(status=r['status'],result=(RUN/'RESULT.json').relative_to(ROOT).as_posix(),sha256=sha(RUN/'RESULT.json'),board=False),
             '## M441 W2/W4缺口仿真闭合19（2026-10-10）\n\nSHA '+sha(RUN/'RESULT.json')+'；四新隔离缺口及W2timeout全部按原字节核对PASS。完整真实Q/两W4全输出及有界背压结束协议，W2最大10descriptor/FIFO8192/34/四端口4KiB/尾TLAST128已补齐。旧证据不改，未新增板端或性能样本，稳定服务/回滚保持。')
        progress('COMPLETE',result=r);print(r['status'],flush=True)
    except BaseException as exc:
        r=dict(status='STOP_M441_SUPPLEMENTAL_SIMULATION19_AT_CURRENT_LEVEL',results=results,error=repr(exc),traceback=traceback.format_exc(),
               preparation_sha256=sha(PREP),original_attempts_preserved=True,board=False,production_changed=False)
        atomic(RUN/'STOP.json',encoded(r),immutable=True)
        sync('latest_m441_simulation19_stop',dict(status=r['status'],result=(RUN/'STOP.json').relative_to(ROOT).as_posix(),sha256=sha(RUN/'STOP.json'),board=False),
             '## M441补充仿真19本级停止（2026-10-10）\n\nSHA '+sha(RUN/'STOP.json')+'；仅本级诊断，原工具/收集/完整traceback保存，不覆盖旧PASS/FAIL，不扩大后级，不自动重跑。0板端/生产修改。')
        progress('STOP',result=r);raise


if __name__=='__main__':main()
