"""Default-disabled local max-FIFO/timeout controller. No board entry points."""
import argparse
import json
import shutil
import subprocess
import time
from m351_workflow import ROOT, BASE, HERE, atomic, encoded, sha

PREP=BASE/'runs/M441-max-protocol-preparation-01/RESULT.json'
OUT=ROOT/'tmp/m441_max_protocol_01'
NEG=ROOT/'tmp/m441_timeout_negative_01'

# XSIM rewrites these runtime bookkeeping files. Executable/model files remain
# strict SHA evidence; every copied file is checked before starting the child.
RUNTIME_NAMES={'TempBreakPointFile.txt','xsim_script.tcl','xsim.covinfo',
               'xsim.crvsdump','xsimcrash.log','xsimkernel.log'}

def snapshot_files(directory):
    rows=[dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p),
               runtime_bookkeeping=p.name in RUNTIME_NAMES)
          for p in sorted(directory.rglob('*')) if p.is_file()]
    assert rows and any(x['path'].endswith('/xsimk.exe') for x in rows)
    return rows

def verify_compiled_snapshot():
    proof=require_validation('compile');r=json.loads(proof.read_bytes())
    rows=r['details']['snapshot_files'];assert rows
    assert any(x['path'].endswith('/xsimk.exe') and not x['runtime_bookkeeping'] for x in rows)
    for row in rows:
        assert row['runtime_bookkeeping']==((ROOT/row['path']).name in RUNTIME_NAMES)
        if not row['runtime_bookkeeping']:assert sha(ROOT/row['path'])==row['sha256']
    return proof


def synchronized(path,status,board_key):
    if not path.is_file():raise RuntimeError('Missing prerequisite: '+path.relative_to(ROOT).as_posix())
    r=json.loads(path.read_bytes());assert r['status']==status,r['status']
    assert r.get('board') is False
    digest=sha(path)
    for doc in ('CURRENT_STATE.md','docsMILESTONES.md'):assert digest in (ROOT/doc).read_text(encoding='utf-8-sig')
    b=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    assert b[board_key]['sha256']==digest
    return r


def prerequisites():
    full=BASE/'runs/M441-offline-continuation-01/RESULT.json'
    r=synchronized(full,'PASS_M441_COMPLETE_LONG_CHAIN_RTL_COMPARISON','latest_m441_offline_continuation_result')
    assert not r['errors'] and r['comparisons'] and len(r['comparisons'])==6
    assert {(x['family'],x['mode']) for x in r['comparisons']}=={(family,mode) for family in ('gate_up','mlp_down','q') for mode in ('zero','random')}
    assert all(x['pass_gate'] is True for x in r['comparisons'])
    core=BASE/'runs/M441-record-pipeline-core-OOC-closure-01/RESULT.json'
    c=synchronized(core,'PASS_M441_SAME_CONSTRAINT_CORE_ROUTED_TIMING','latest_m441_record_pipeline_core_OOC')
    assert c['build_id']=='0x4D343431' and c['original_rc']==0 and c['core_only'] is True and c['full_shell'] is False
    required=('original_rc','actual_reports','same_clock_XDC','target_period','XML_timing_met','resources_fit','setup_hold_pulse','route_clean')
    assert all(c['checks'][k] is True for k in required)
    assert float(c['timing']['TargetClockPeriod'])==4.8
    assert c['timing_summary']['WNS_ns']>=0 and c['timing_summary']['WHS_ns']>=0 and c['timing_summary']['WPWS_ns']>=0
    assert c['evidence']
    for row in c['evidence']:
        assert row['path'].startswith('tmp/m441_') and sha(ROOT/row['path'])==row['sha256'],row['path']
    xdc=[row for row in c['evidence'] if row['path'].endswith('m89x_runtime_kernel.xdc')]
    assert len(xdc)==1 and xdc[0]['sha256']=='63ea420c7cd5b85ab6b683b1f04e1509facc1a68929ecc2c9896eeb8b79288b4'
    checks=BASE/'runs/M441-protocol-evidence-support-checks-02/RESULT.json'
    t=synchronized(checks,'PASS_M441_PROTOCOL_COLLECTOR_FAULT_CHECKS_ONLY','latest_m441_protocol_collector_checks')
    assert len(t['rejected_cases'])==31 and t['source_sha256']==sha(HERE/'m441_protocol_evidence.py')
    return dict(full_chain_sha256=sha(full),core_sha256=sha(core),collector_checks_sha256=sha(checks))


def verified_prep():
    p=json.loads(PREP.read_bytes());assert p['status']=='PREPARED_M441_MAXIMUM_PROTOCOL_NO_EXECUTION'
    for row in p['files']:assert sha(ROOT/row['path'])==row['sha256'],row['path']
    return p


def require_validation(mode):
    names={'compile':('M441-max-protocol-compile-01','PASS_M441_MAXIMUM_PROTOCOL_COMPILED'),
           'max':('M441-max-protocol-rtl-01','PASS_M441_MAXIMUM_PROTOCOL_RTL')}
    name,status=names[mode];path=BASE/'runs'/name/'RESULT.json'
    synchronized(path,status,'latest_m441_max_protocol_'+mode)
    return path


def main():
    ap=argparse.ArgumentParser();ap.add_argument('mode',choices=('check','compile','max','timeout'));ap.add_argument('--run',action='store_true');a=ap.parse_args()
    p=verified_prep()
    if a.mode=='check':
        try:refs=prerequisites();print(json.dumps(dict(status='READY_FOR_LOCAL_PROTOCOL',refs=refs)))
        except (AssertionError,RuntimeError,KeyError,OSError) as exc:print(json.dumps(dict(status='BLOCKED_BEFORE_ANY_TOOL_OR_BOARD',reason=str(exc))))
        return
    assert a.run,'Default disabled: explicit --run required'
    refs=prerequisites()
    policy=BASE/'runs/M441-protocol-control-preparation-01/RESULT.json';pol=json.loads(policy.read_bytes())
    assert pol['status']=='PREPARED_M441_PROTOCOL_CONTROL_COLLECTOR_GUARDS'
    for row in pol['files']:assert sha(ROOT/row['path'])==row['sha256'],row['path']
    synchronized(policy,'PREPARED_M441_PROTOCOL_CONTROL_COLLECTOR_GUARDS','latest_m441_protocol_control_preparation')
    sim=OUT/'verilog'
    if a.mode!='compile':verify_compiled_snapshot()
    if a.mode=='timeout':
        maximum=require_validation('max');assert not NEG.exists(),'Existing timeout: collect only'
        for row in p['files']:
            source=ROOT/row['path'];relative=source.relative_to(OUT)
            if relative.parts[:2]==('tv','rtldatafile'):continue
            atomic(NEG/relative,source.read_bytes(),immutable=True)
        (NEG/'tv/rtldatafile').mkdir(parents=True,exist_ok=True)
        shutil.copytree(sim/'xsim.dir',NEG/'verilog/xsim.dir')
        snapshots=[]
        for source in sorted((sim/'xsim.dir').rglob('*')):
            if source.is_file():
                target=NEG/'verilog/xsim.dir'/source.relative_to(sim/'xsim.dir');assert sha(source)==sha(target)
                snapshots.append(dict(source=source.relative_to(ROOT).as_posix(),copy=target.relative_to(ROOT).as_posix(),sha256=sha(source),
                                      runtime_bookkeeping=source.name in RUNTIME_NAMES))
        atomic(NEG/'PREREQUISITE.json',encoded(dict(max_result_sha256=sha(maximum),same_compiled_candidate_snapshot=True,
                                                snapshot_files=snapshots,source_preparation_sha256=sha(PREP))),immutable=True)
        sim=NEG/'verilog'
    stem=a.mode
    assert not (sim/(stem+'.log')).exists() and not (sim/(stem+'_exit.json')).exists(),'Existing attempt: collect only'
    if stem=='compile':
        cmd=['D:/AMDDesignTools/2026.1/Vivado/bin/xelab.bat','xil_defaultlib.apatb_m89x_runtime_kernel_top','xil_defaultlib.glbl','xil_defaultlib.m441_max_monitor','xil_defaultlib.m441_rtl_watchdog',
             '-Oenable_linking_all_libraries','-prj','m441_max.prj','-debug','typical']
        for lib in ('smartconnect_v1_0','axi_protocol_checker_v1_1_12','axi_protocol_checker_v1_1_13','axis_protocol_checker_v1_1_11','axis_protocol_checker_v1_1_12','xil_defaultlib','unisims_ver','xpm','floating_point_v7_1_22','floating_point_v7_0_27','uvm'):cmd+=['-L',lib]
        cmd+=['-relax']
        for inc in ('svr','axivip','svtb','file_agent','m89x_runtime_kernel_subsystem'):cmd+=['-i','./'+inc]
        cmd+=['-s','m441_max_trace','-log','compile.log'];budget=3600
    else:
        args='-testplusarg UVM_VERBOSITY=UVM_NONE\n-testplusarg UVM_TESTNAME=m89x_runtime_kernel_test_lib\n-testplusarg UVM_TIMEOUT=20000000000000\n-testplusarg M438_ZERO_EXTRA_LATENCY\n-sv_seed 441\n--noieeewarnings\n'
        if stem=='timeout':args+='-testplusarg M441MAX_EXPECT_TIMEOUT\n'
        args+='-tclbatch '+stem+'.tcl\n-log '+stem+'.log\n';atomic(sim/(stem+'.args'),args.encode('utf-8'),immutable=True)
        cmd=['D:/AMDDesignTools/2026.1/Vivado/bin/xsim.bat','m441_max_trace','-f',stem+'.args'];budget=8*3600 if stem=='max' else 600
    wall=False;started=time.monotonic();rc=None
    with (sim/(stem+'_console.log')).open('xb') as stream:
        proc=subprocess.Popen(cmd,cwd=sim,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
        print('M441_PROTOCOL_LOCAL_STARTED '+stem+' pid='+str(proc.pid),flush=True)
        while proc.poll() is None:
            if time.monotonic()-started>budget:wall=True;break
            time.sleep(1)
        if not wall:rc=proc.returncode
    log=(sim/(stem+'.log')).read_text(encoding='utf-8-sig',errors='replace') if (sim/(stem+'.log')).exists() else ''
    observed=stem=='timeout' and 'M441MAX_RTL_TIMEOUT_TRIGGERED ap_done=0 budget_cycles=200' in log and 'M441MAX bounded timeout expired before ap_done' in log
    gate=1 if wall or observed or rc else 0
    receipt=dict(original_rc=rc,gate_rc=gate,timeout_observed=observed,software_wall_budget_exceeded=wall,
                 elapsed_s=time.monotonic()-started,process_pid=proc.pid,process_retained=wall,process_killed=False,
                 preparation_sha256=sha(PREP),control_preparation_sha256=sha(policy),prerequisites=refs)
    if stem=='compile' and rc==0 and not wall:receipt['snapshot_files']=snapshot_files(sim/'xsim.dir')
    atomic(sim/(stem+'_exit.json'),encoded(receipt),immutable=True)
    if stem=='max' and not wall:
        saved=sim/'max_result';assert not saved.exists();saved.mkdir()
        for source in (OUT/'tv/rtldatafile').glob('*.dat'):shutil.copyfile(source,saved/source.name)
    print(json.dumps(receipt),flush=True)
    raise SystemExit(gate)


if __name__=='__main__':main()
