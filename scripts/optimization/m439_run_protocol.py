"""Fixed offline candidate protocol runner; preserve original tool exit codes."""
import argparse,json,shutil,subprocess,time
from pathlib import Path
from m351_workflow import ROOT,BASE,atomic,encoded,sha

ap=argparse.ArgumentParser();ap.add_argument('mode',choices=('compile','max','timeout'));ap.add_argument('--run',action='store_true');a=ap.parse_args()
assert a.run,'Default disabled'
prep=BASE/'runs/M439-max-protocol-preparation-01/RESULT.json';p=json.loads(prep.read_bytes())
assert p['status']=='PREPARED_M439_MAXIMUM_PROTOCOL_NOT_EXECUTED'
assert sha(Path(__file__))==p['runner_sha256']
for row in p['files']:assert sha(ROOT/row['path'])==row['sha256'],row['path']
assert all(sha(prep) in (ROOT/n).read_text(encoding='utf-8') for n in ('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'))
out=ROOT/'tmp/m439_max_protocol_01';sim=out/'verilog'
if a.mode=='timeout':
    prior=BASE/'runs/M439-max-protocol-rtl-01/RESULT.json';r=json.loads(prior.read_bytes())
    assert r['status']=='PASS_M439_MAXIMUM_PROTOCOL_RTL'
    assert all(sha(prior) in (ROOT/n).read_text(encoding='utf-8') for n in ('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'))
    target=ROOT/'tmp/m439_timeout_negative_01';assert not target.exists(),'Existing negative: collect only'
    target.mkdir();shutil.copytree(out/'tv',target/'tv');(target/'verilog').mkdir()
    shutil.copytree(sim/'xsim.dir',target/'verilog/xsim.dir')
    snapshots=[]
    for x in sorted((sim/'xsim.dir').rglob('*')):
        if x.is_file():
            y=target/'verilog/xsim.dir'/x.relative_to(sim/'xsim.dir')
            digest=sha(x);assert sha(y)==digest
            snapshots.append(dict(source=x.relative_to(ROOT).as_posix(),copy=y.relative_to(ROOT).as_posix(),sha256=digest))
    assert snapshots
    # UVM error-visibility audit reads the actual source, not the compiled binary.
    for name in ('m89x_runtime_kernel_subsystem','svtb','file_agent','svr','axivip'):
        shutil.copytree(sim/name,target/'verilog'/name)
    shutil.copyfile(sim/'timeout.tcl',target/'verilog/timeout.tcl')
    atomic(target/'PREREQUISITE.json',encoded(dict(max_result_sha256=sha(prior),same_compiled_candidate_snapshot=True,snapshot_files=snapshots,source_preparation_sha256=sha(prep))),immutable=True)
    sim=target/'verilog'
stem=a.mode
assert not (sim/(stem+'.log')).exists() and not (sim/(stem+'_exit.json')).exists(),'Existing attempt: collect only'
if a.mode=='compile':
    cmd=['D:/AMDDesignTools/2026.1/Vivado/bin/xelab.bat','xil_defaultlib.apatb_m89x_runtime_kernel_top','xil_defaultlib.glbl','xil_defaultlib.m439_monitor','xil_defaultlib.m439_rtl_watchdog',
         '-Oenable_linking_all_libraries','-prj','m439.prj','-debug','typical']
    for lib in ('smartconnect_v1_0','axi_protocol_checker_v1_1_12','axi_protocol_checker_v1_1_13','axis_protocol_checker_v1_1_11','axis_protocol_checker_v1_1_12','xil_defaultlib','unisims_ver','xpm','floating_point_v7_1_22','floating_point_v7_0_27','uvm'):
        cmd+=['-L',lib]
    cmd+=['-relax']
    for inc in ('svr','axivip','svtb','file_agent','m89x_runtime_kernel_subsystem'):cmd+=['-i','./'+inc]
    cmd+=['-s','m439_max_trace','-log','compile.log'];budget=p['compile_wall_budget_s']
else:
    assert (out/'verilog/compile_validated.json').exists(),'Compile not adjudicated'
    args='-testplusarg UVM_VERBOSITY=UVM_NONE\n-testplusarg UVM_TESTNAME=m89x_runtime_kernel_test_lib\n-testplusarg UVM_TIMEOUT=20000000000000\n-testplusarg M438_ZERO_EXTRA_LATENCY\n-sv_seed 439\n--noieeewarnings\n'
    if a.mode=='timeout':args+='-testplusarg M439_EXPECT_TIMEOUT\n'
    args+='-tclbatch '+stem+'.tcl\n-log '+stem+'.log\n'
    atomic(sim/(stem+'.args'),args.encode('utf-8'),immutable=True)
    cmd=['D:/AMDDesignTools/2026.1/Vivado/bin/xsim.bat','m439_max_trace','-f',stem+'.args']
    budget=p['wall_budget_s'] if a.mode=='max' else p['timeout_wall_budget_s']
start=time.monotonic();wall=False
with (sim/(stem+'_console.log')).open('wb') as f:
    proc=subprocess.Popen(cmd,cwd=sim,stdout=f,stderr=subprocess.STDOUT)
    print('M439_OFFLINE_PROTOCOL_STARTED mode='+stem+' wrapper_pid='+str(proc.pid),flush=True)
    try:rc=proc.wait(timeout=budget)
    except subprocess.TimeoutExpired:
        wall=True
        stopped=subprocess.run(['taskkill.exe','/PID',str(proc.pid),'/T','/F'],capture_output=True,text=True)
        assert stopped.returncode==0,'Offline simulator tree stop failed'
        rc=proc.wait(timeout=10)
        atomic(sim/(stem+'_wall_stop.json'),encoded(dict(software_only=True,board=False,budget_s=budget,elapsed_s=time.monotonic()-start)),immutable=True)
observed=False
if a.mode=='timeout':
    text=(sim/'timeout.log').read_text(encoding='utf-8-sig',errors='replace') if (sim/'timeout.log').exists() else ''
    observed='M439_RTL_TIMEOUT_TRIGGERED ap_done=0 budget_cycles=200' in text and 'M439 bounded timeout expired before ap_done' in text
gate=1 if wall or observed or rc else 0
atomic(sim/(stem+'_exit.json'),encoded(dict(original_rc=rc,gate_rc=gate,timeout_observed=observed,software_wall_budget_exceeded=wall,elapsed_s=time.monotonic()-start,preparation_sha256=sha(prep))),immutable=True)
if a.mode=='max':
    saved=sim/'max_result';assert not saved.exists();saved.mkdir()
    for x in (out/'tv/rtldatafile').glob('*.dat'):shutil.copyfile(x,saved/x.name)
print(json.dumps(dict(mode=stem,original_rc=rc,gate_rc=gate,wall=wall,timeout_observed=observed)))
raise SystemExit(gate)
