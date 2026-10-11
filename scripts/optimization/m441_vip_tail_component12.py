"""Actual unchanged vendor receiver task + explicit fake producer; no M441 DUT."""
import argparse,json,re,subprocess,time
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
WORK=ROOT/'tmp/m441_vip_tail_component_12'
RESULT=BASE/'runs/M441-vip-tail-component-12/RESULT.json'
TAIL=r'''
always @(negedge rx_clk)begin
 if(!tail_armed && words==327679)begin
  tail_block=1;tail_armed=1;
 end else if(tail_armed&&!tail_released&&rx_valid&&rx_last)begin
  if(rx_ready)$fatal(1,"held last ready not low");
  tail_hold_valid_cycles++;
  if(tail_hold_valid_cycles==128)begin
   tail_block=0;tail_released=1;
   $display("M441_BOUNDARY_LAST_HOLD valid_cycles=%0d accepted_before=%0d",tail_hold_valid_cycles,words);
  end
 end
end
'''

def prepare():
    assert not WORK.exists() and not RESULT.exists()
    original=ROOT/'tmp/m441_boundary_protocol_06/verilog/svr'
    files=['svr_if.sv','svr_object_global.svh','svr_config.sv','svr_transfer.sv','svr_slave_driver.sv']
    for n in files:atomic(WORK/'svr'/n,(original/n).read_bytes(),immutable=True)
    package='package svr_pkg;\nimport uvm_pkg::*;\n`include "uvm_macros.svh"\n'+''.join('`include "'+n+'"\n' for n in files[1:])+'endpackage\n'
    atomic(WORK/'actual_receiver.sv',package.encode(),immutable=True)
    old=ROOT/'tmp/m441_boundary_protocol_06/verilog/m441_max_monitor.sv'
    text=old.read_text(encoding='utf-8-sig');old_tail=text[text.index('// Shared VIP ready'):text.rindex('endmodule')]
    old_tail=old_tail.replace('always @(negedge `D.ap_clk)','always @(negedge rx_clk)').replace('`D.rx_TVALID','rx_valid').replace('`D.rx_TLAST','rx_last').replace('`D.rx_TREADY','rx_ready').replace('apatb_m89x_runtime_kernel_top.svtb_top.svr_rx_if.ready','sink.ready')
    code=r'''
`timescale 1ns/1ps
module actual_vip_tail;
import uvm_pkg::*;import svr_pkg::*;
reg rx_clk=0;always #1 rx_clk=~rx_clk;
svr_if #(64) sink(rx_clk,1'b1);
string scenario;
bit tail_block=0,tail_armed=0,tail_released=0;
reg rx_valid=0,rx_last=0;
wire rx_ready=sink.ready && !(scenario!="old_release"&&tail_block);
assign sink.valid=rx_valid && !(scenario!="old_release"&&tail_block);
assign sink.data=64'b0;
integer words=327677,cycles=0,held_edges=0,accepted=0;
integer tail_hold_valid_cycles=0;
svr_slave_driver #(64) driver;
svr_transfer #(64) item;
task automatic progress_snapshot(input integer kind);$display("VIP_SNAPSHOT kind=%0d",kind);endtask
initial begin
 if(!$value$plusargs("CASE=%s",scenario))$fatal(1,"case missing");
 sink.ready=0;
 driver=new("actual_vendor_driver",null);driver.vif=sink;driver.cfg=new();
 driver.cfg.prt_type=AXIS;driver.cfg.reset_level=RESET_LEVEL_LOW;
 for(integer k=0;k<3;k++)begin
  item=new();item.delay=(scenario=="delay8")?8:0;
  driver.get_and_drive(item);accepted++;
 end
 #0.2;
 if(words!=327680||held_edges<128||tail_hold_valid_cycles!=128||!tail_released||accepted!=3)$fatal(1,"actual VIP incomplete or hold");
 $display("M441_ACTUAL_VIP_TAIL_PASS words=%0d held_edges=%0d accepted=%0d",words,held_edges,accepted);$finish;
end
always @(posedge rx_clk)begin
 cycles++;
 if(rx_valid&&rx_last&&!rx_ready)held_edges++;
 if(rx_valid&&rx_ready)words++;
 if(cycles>1000)begin
  if(scenario=="old_release"&&words==327679&&tail_hold_valid_cycles==128&&tail_released&&sink.ready==0)begin
   $display("M441_ACTUAL_VIP_OLD_RELEASE_STUCK words=%0d ready=%0d held=%0d",words,sink.ready,tail_hold_valid_cycles);$finish;
  end
  $fatal(1,"actual receiver component budget");
 end
end
always @(negedge rx_clk)begin #0.1;rx_valid=1;rx_last=(words==327679);end
generate if(1)begin:tail_hook
''' + 'if(1)begin:fixed\n'+TAIL+'end\nend endgenerate\nendmodule\n'
    # One snapshot tests both original force/release and the interposer.
    code=code.replace('if(1)begin:fixed\n'+TAIL,
        'always @(negedge rx_clk)begin end\n'+
        old_tail.replace('if(!tail_armed','if(scenario=="old_release"&&!tail_armed').replace('else if(tail_armed','else if(scenario=="old_release"&&tail_armed')+
        '\n'+TAIL.replace('if(!tail_armed','if(scenario!="old_release"&&!tail_armed').replace('else if(tail_armed','else if(scenario!="old_release"&&tail_armed'))
    # Remove the old named block terminator after replacing its wrapper.
    code=code.replace('end\nend endgenerate\nendmodule','end endgenerate\nendmodule')
    atomic(WORK/'component.sv',code.encode(),immutable=True)
    atomic(WORK/'component.prj',b'sv xil_defaultlib "svr/svr_if.sv"\nsv xil_defaultlib "actual_receiver.sv"\nsv xil_defaultlib "component.sv"\n',immutable=True)
    atomic(WORK/'run.tcl',b'run all\nquit\n',immutable=True)
    atomic(WORK/'INPUT.json',encoded(dict(actual_vendor_files=[dict(path=(original/n).relative_to(ROOT).as_posix(),sha256=sha(original/n)) for n in files],
        original_monitor_sha256=sha(old),actual_vendor_receiver_unchanged=True,explicit_fake_producer=True,M441_DUT=False)),immutable=True)

def run():
    assert not RESULT.exists();tools='D:/AMDDesignTools/2026.1/Vivado/bin/';rows=[];errors=[]
    def call(name,args):
        assert not (WORK/(name+'_exit.json')).exists()
        start=time.monotonic()
        with (WORK/(name+'_console.log')).open('xb') as stream:
            p=subprocess.Popen(args,cwd=WORK,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
            while p.poll() is None:
                if time.monotonic()-start>300:raise RuntimeError('Component wall budget, retained PID '+str(p.pid))
                time.sleep(.2)
        rc=p.returncode;atomic(WORK/(name+'_exit.json'),encoded(dict(original_rc=rc)),immutable=True);return rc
    try:
        rc=call('compile',[tools+'xelab.bat','xil_defaultlib.actual_vip_tail','-prj','component.prj','-i','svr','-L','uvm','-s','m441_actual_vip_tail','-debug','typical','-v','2','-log','compile.log']);assert rc==0
        for case in ['old_release','fixed','delay8']:
            atomic(WORK/(case+'.args'),f'-testplusarg CASE={case}\n-sv_seed 441\n-tclbatch run.tcl\n-log {case}.log\n'.encode(),immutable=True)
            rc=call(case,[tools+'xsim.bat','m441_actual_vip_tail','-f',case+'.args'])
            text=(WORK/(case+'.log')).read_text(encoding='utf-8-sig',errors='replace')
            marker='M441_ACTUAL_VIP_OLD_RELEASE_STUCK' if case=='old_release' else 'M441_ACTUAL_VIP_TAIL_PASS'
            assert rc==0 and re.search(r'^'+marker+' ',text,re.M) and not re.search(r'^Fatal:|^ERROR:',text,re.M)
            rows.append(dict(case=case,original_rc=rc,marker=marker))
    except Exception as exc:errors.append(repr(exc))
    r=dict(status='PASS_M441_ACTUAL_VIP_RELEASE_DIAGNOSIS_COMPONENT' if not errors else 'FAIL_M441_ACTUAL_VIP_COMPONENT',errors=errors,cases=rows,
        actual_vendor_receiver_unchanged=True,explicit_fake_producer=True,DUT=False,board=False,performance=False,
        source_sha256=sha(HERE/'m441_vip_tail_component12.py'),evidence=[dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p)) for p in sorted(WORK.rglob('*')) if p.is_file() and 'xsim.dir' not in p.parts])
    atomic(RESULT,encoded(r),immutable=True)
    sync('latest_m441_vip_tail_component12',dict(status=r['status'],sha256=sha(RESULT),result=RESULT.relative_to(ROOT).as_posix(),board=False),
         f'## M441 实际VIP尾停顿组件12（2026-10-09）\n\nSHA {sha(RESULT)}；{r["status"]}，实际原vendor接收driver与明确fake producer。原force/release及独立valid/ready interposer对照；0M441 DUT/板端，错误{errors}。')
    print(r['status'],sha(RESULT),errors,rows,flush=True)
    return 1 if errors else 0

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('mode',choices=['Prepare','Run']);a.add_argument('--enable',action='store_true');args=a.parse_args()
    if args.mode=='Prepare':prepare()
    else:assert args.enable,'Default disabled';raise SystemExit(run())
