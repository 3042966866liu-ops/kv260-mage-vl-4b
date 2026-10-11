"""Default-disabled local max-FIFO/timeout controller. No board entry points."""
import argparse
import json
import shutil
import subprocess
import time
from m351_workflow import ROOT, BASE, HERE, atomic, encoded, sha
from m441_supervisor04 import boot,process,classify,log_snapshot

PREP=BASE/'runs/M441-bounded-boundary-preparation-07/RESULT.json'
OUT=ROOT/'tmp/m441_boundary_protocol_07'
NEG=ROOT/'tmp/m441_boundary_timeout_07'

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
    refs={'latest_m441_full_numeric_csim': ('PASS_M441_FULL_REAL_WEIGHT_CHAIN_CSIM', 'a2b19009642bc956a3a18cd01a09fb3d65bb187ea1672ce2a4bd853bb1256c46'), 'latest_m441_long_A_gate_up_zero02': ('PASS_M441_COMPLETE_CHAIN_RTL_NUMERIC_AND_PROTOCOL', '3116961c34d729e37f32a79b4e914c1e16d4a978c988e41ddc51814298fd16f4'), 'latest_m441_long_B_gate_up_zero02': ('PASS_M441_COMPLETE_CHAIN_RTL_NUMERIC_AND_PROTOCOL', '74bafec070d975c0ef967205f7b3232e49efd75a5436f6db2223a2142220647c'), 'latest_m441_W4_zero05_result': ('PASS_M441_W4_MLPDOWN_FULL_ZERO04', '3db32e9edcd326c35247fc0b487f1ba33488b73275361aa7fa2126c0f90b0e54'), 'latest_m441_vip_tail_component13': ('PASS_M441_ACTUAL_VIP_RELEASE_DIAGNOSIS_COMPONENT', 'cc64a9e27602d4f581bf953545423a0417f3575aacb69e609c214c52348bfe1e'), 'latest_m441_boundary_collector_checks06': ('PASS_M441_BOUNDED_BOUNDARY_COLLECTOR_COMPONENT_ONLY', 'a35ae4d4187f747a10317c944102ac67b3320fc024c0009ba6fa424e5405ae0b')}
    result={}
    b=json.loads((ROOT/"deployment/mage_vl4b/BOARD_GATE_RESULT.json").read_bytes())
    for key,(status,digest) in refs.items():
        path=ROOT/b[key]["result"];r=synchronized(path,status,key)
        assert sha(path)==digest
        result[key]=digest
    assert len(json.loads((ROOT/b["latest_m441_boundary_collector_checks06"]["result"]).read_bytes())["rejected_cases"])==26
    return result


def verified_prep():
    p=json.loads(PREP.read_bytes());assert p['status']=='PREPARED_M441_BOUNDED_BOUNDARY07'
    for row in p['files']:assert sha(ROOT/row['path'])==row['sha256'],row['path']
    return p


def require_validation(mode):
    names={'compile':('M441-boundary-compile-07','PASS_M441_BOUNDARY_COMPILED'),
           'max':('M441-boundary-rtl-07','PASS_M441_BOUNDARY_RTL')}
    name,status=names[mode];path=BASE/'runs'/name/'RESULT.json'
    synchronized(path,status,'latest_m441_boundary07_'+mode)
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
    policy=BASE/'runs/M441-boundary-control-preparation-07/RESULT.json';pol=json.loads(policy.read_bytes())
    assert pol['status']=='PREPARED_M441_BOUNDARY_CONTROL07'
    for row in pol['files']:assert sha(ROOT/row['path'])==row['sha256'],row['path']
    synchronized(policy,'PREPARED_M441_BOUNDARY_CONTROL07','latest_m441_boundary_control07')
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
             '-Oenable_linking_all_libraries','-prj','m441_max.prj','-debug','typical','-v','2']
        for lib in ('smartconnect_v1_0','axi_protocol_checker_v1_1_12','axi_protocol_checker_v1_1_13','axis_protocol_checker_v1_1_11','axis_protocol_checker_v1_1_12','xil_defaultlib','unisims_ver','xpm','floating_point_v7_1_22','floating_point_v7_0_27','uvm'):cmd+=['-L',lib]
        cmd+=['-relax']
        for inc in ('svr','axivip','svtb','file_agent','m89x_runtime_kernel_subsystem'):cmd+=['-i','./'+inc]
        cmd+=['-s','m441_max_trace','-log','compile.log'];budget=3600
    else:
        args='-testplusarg UVM_VERBOSITY=UVM_NONE\n-testplusarg UVM_TESTNAME=m89x_runtime_kernel_test_lib\n-testplusarg UVM_TIMEOUT=20000000000000\n-sv_seed 441\n--noieeewarnings\n'
        if stem=='timeout':args+='-testplusarg M441MAX_EXPECT_TIMEOUT\n'
        args+='-tclbatch '+stem+'.tcl\n-log '+stem+'.log\n';atomic(sim/(stem+'.args'),args.encode('utf-8'),immutable=True)
        cmd=['D:/AMDDesignTools/2026.1/Vivado/bin/xsim.bat','m441_max_trace','-f',stem+'.args'];budget=4*3600 if stem=='max' else 600
    wall=False;started=time.monotonic();rc=None;start_boot=boot();next_live=0
    with (sim/(stem+'_console.log')).open('xb') as stream:
        proc=subprocess.Popen(cmd,cwd=sim,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
        print('M441_PROTOCOL_LOCAL_STARTED '+stem+' pid='+str(proc.pid),flush=True)
        identity=process(proc.pid);born=identity.get("creation_FILETIME")
        while proc.poll() is None:
            if time.monotonic()>=next_live:
                state=process(proc.pid,born);current=boot()
                atomic(sim/(stem+"_LIVE.json"),encoded(dict(status=classify(start_boot,current,state),process=state,boot=current,start_boot=start_boot,elapsed_s=time.monotonic()-started,log=log_snapshot(sim/(stem+".log")))))
                next_live=time.monotonic()+30
            if time.monotonic()-started>budget:wall=True;break
            time.sleep(1)
        if not wall:rc=proc.returncode
    log=(sim/(stem+'.log')).read_text(encoding='utf-8-sig',errors='replace') if (sim/(stem+'.log')).exists() else ''
    observed=stem=='timeout' and 'M441MAX_RTL_TIMEOUT_TRIGGERED ap_done=0 budget_cycles=200' in log and 'M441MAX bounded timeout expired before ap_done' in log
    gate=1 if wall or observed or rc else 0
    receipt=dict(original_rc=rc,gate_rc=gate,timeout_observed=observed,software_wall_budget_exceeded=wall,
                 elapsed_s=time.monotonic()-started,process_pid=proc.pid,process_retained=wall,process_killed=False,start_boot=start_boot,process_creation_FILETIME=born,
                 preparation_sha256=sha(PREP),control_preparation_sha256=sha(policy),prerequisites=refs)
    if stem=='compile' and rc==0 and not wall:receipt['snapshot_files']=snapshot_files(sim/'xsim.dir')
    atomic(sim/(stem+'_exit.json'),encoded(receipt),immutable=True)
    if stem=='max' and not wall:
        saved=sim/'max_result';assert not saved.exists();saved.mkdir()
        for source in (OUT/'tv/rtldatafile').glob('*.dat'):shutil.copyfile(source,saved/source.name)
    print(json.dumps(receipt),flush=True)
    raise SystemExit(gate)


if __name__=='__main__':main()
