"""New candidate full-output RTL/VIP trace; original FP models only if exact wrappers match."""
import json
import re
import shutil
from pathlib import Path
import m351_workflow as w
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'deployment/mage_vl4b/optimization_v1'
ORIGINAL=ROOT/'tmp/m356_stable_q_trace'
OUT=ROOT/'tmp/m357_candidate_q_trace'
SYN=ROOT/'tmp/m357_hls_project_02/hls/syn/verilog'

def main():
    if OUT.exists():raise RuntimeError('Existing candidate trace; inspect only')
    assert json.loads((ROOT/'tmp/m357_activation_banks/m357_exit_02.json').read_text(encoding='utf-8'))['hls_rc']==0
    report=ROOT/'tmp/m357_hls_project_02/hls/syn/report/m89x_runtime_kernel_csynth.rpt'
    four=SYN/'m89x_runtime_kernel_m89x_four.v';text=four.read_text(encoding='utf-8')
    assert 'Block_entry_x_0_rd_proc' not in text
    starts=re.findall(r'assign (m89x_shard\w*_U0_ap_start) = ([^;]+);',text)
    assert len(starts)==4 and all('ap_start' in value and '_ap_done' not in value for _,value in starts)
    checked=[]
    for p in (ORIGINAL/'verilog/ip/xil_defaultlib').glob('*.vhd'):
        wrapper=p.name[:-7]+'.v' # replace _ip.vhd with .v
        assert (SYN/wrapper).is_file(),wrapper
        assert w.sha(SYN/wrapper)==w.sha(ORIGINAL/'verilog'/wrapper),wrapper
        checked.append(dict(wrapper=wrapper,sha256=w.sha(SYN/wrapper),model=p.relative_to(ROOT).as_posix(),model_sha256=w.sha(p)))
    assert len(checked)==6
    out=OUT/'verilog';out.mkdir(parents=True)
    for name in ('svr','axivip','svtb','file_agent','m89x_runtime_kernel_subsystem','ip'):
        shutil.copytree(ORIGINAL/'verilog'/name,out/name)
    for name in ('glbl.v','fifo_para.vh','m89x_runtime_kernel.autotb.v'):
        shutil.copyfile(ORIGINAL/'verilog'/name,out/name)
    for p in SYN.glob('*.v'):shutil.copyfile(p,out/p.name)
    tb=out/'m89x_runtime_kernel.autotb.v';tbtext=tb.read_text(encoding='utf-8')
    for instance in ('deadlock_detector','kernel_monitor_top','U_dataflow_monitor'):
        # Original generated instrumentation references original scheduling hierarchy.
        pattern=r'(?m)^\w+ '+instance+r'\([\s\S]*?\);'
        tbtext,n=re.subn(pattern,'// Old hierarchy-specific monitor replaced by isolated trace monitor.',tbtext)
        assert n==1,instance
    tb.write_text(tbtext,encoding='utf-8')
    shutil.copytree(ORIGINAL/'tv/cdatafile',OUT/'tv/cdatafile')
    shutil.copytree(ORIGINAL/'tv/stream_size',OUT/'tv/stream_size')
    (OUT/'tv/rtldatafile').mkdir()
    p=OUT/'tv/cdatafile/c.m89x_runtime_kernel.autotvout_ap_return.dat'
    p.write_text(p.read_text(encoding='utf-8').replace('0x4d395832','0x4d333537'),encoding='utf-8')
    monitor=(ROOT/'scripts/optimization/m356_trace_monitor.sv').read_text(encoding='utf-8')
    monitor=monitor.replace('grp_m89x_four_fu_313','grp_m89x_four_fu_404').replace('`F.m89x_four_Block_entry_x_0_rd_proc_U0','`F')
    for old,new in [('grp_m89x_shard_fu_156','m89x_shard_U0'),('grp_m89x_shard_1_fu_184','m89x_shard_1_U0'),('grp_m89x_shard_2_fu_208','m89x_shard_2_U0'),('grp_m89x_shard_3_fu_232','m89x_shard_3_U0')]:monitor=monitor.replace(old,new)
    monitor=monitor.replace('m356','m357').replace('M356','M357')
    monitor=monitor.replace('cyc%500000==0)$display','cyc%500000==0)begin $fflush(fileh);$display').replace('cyc,outwords);\n    for','cyc,outwords);end\n    for')
    (out/'m357_trace_monitor.sv').write_text(monitor,encoding='utf-8')
    oldprj=(ORIGINAL/'verilog/m89x_runtime_kernel.prj').read_text(encoding='utf-8').splitlines()
    vip=[line for line in oldprj if any('/'+folder+'/' in line or './'+folder+'/' in line for folder in ('svr','axivip','svtb','file_agent','m89x_runtime_kernel_subsystem'))]
    vhdl=[line for line in oldprj if line.startswith('vhdl ')]
    prj=vhdl+['sv xil_defaultlib "glbl.v"','sv xil_defaultlib "m89x_runtime_kernel.autotb.v"']
    prj+=['sv xil_defaultlib "'+p.name+'"' for p in sorted(SYN.glob('*.v'))]
    prj+=vip+['sv xil_defaultlib "m357_trace_monitor.sv"']
    (out/'m357.prj').write_text('\n'.join(prj)+'\n',encoding='utf-8')
    (out/'m357_run.tcl').write_text('run all\nquit\n',encoding='utf-8')
    result=dict(status='PASS_CANDIDATE_HLS_PREPARED_FULL_Q_RTL',build_id='0x4D333537',hls_rc=0,parallel_start_assignments=starts,
        hls_resources=dict(BRAM18K=156,DSP=1184,FF=96753,LUT=101930,URAM=64),
        resource_capacity=dict(BRAM18K=288,DSP=1248,FF=234240,LUT=117120,URAM=64),timing='HLS estimate 3.500ns; implementation timing NOT tested',
        report=dict(path=report.relative_to(ROOT).as_posix(),sha256=w.sha(report)),four_rtl=dict(path=four.relative_to(ROOT).as_posix(),sha256=w.sha(four)),
        exact_fp_model_reuse=checked,rtl_inputs=[dict(path=p.relative_to(ROOT).as_posix(),sha256=w.sha(p)) for p in sorted(OUT.rglob('*')) if p.is_file()],
        scope='Full M355 frozen 0:q RTL planned, not yet run; UVM VIP keeps original interface drivers, hierarchy-specific monitor replaced',board=False,promoted=False)
    ev=BASE/'runs/M357-activation-bank-hls-01/RESULT.json';w.atomic(ev,w.encoded(result),immutable=True);sha=w.sha(ev)
    w.sync('M357_activation_bank_hls',dict(status=result['status'],sha256=sha,evidence_path=ev.relative_to(ROOT).as_posix(),build_id=result['build_id']),
        'M357 新综合 rc0，四 shard 独立 ap_start，不含串行 read-proc；HLS估计 URAM64/64 DSP1184/1248 LUT101930/117120 BRAM156/288。仅资源估计，非实现时序/RTL/板端收益。六个FP wrapper同SHA才复用原仿真模型，隔离完整0:q RTL输入已准备。下一步候选完整输出/FIFO/握手。证据 '+sha)
    print(json.dumps(dict(status=result['status'],sha256=sha,fp_model_count=len(checked)),ensure_ascii=True))

if __name__=='__main__':main()
