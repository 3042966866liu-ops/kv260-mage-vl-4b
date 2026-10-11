"""Actual new SV tail/latency snippets with explicit fake signals, no M441 DUT."""
import argparse
import json
import re
import subprocess
import time
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync

WORK=ROOT/'tmp/m441_boundary_component_08'
RESULT=BASE/'runs/M441-boundary-component-08/RESULT.json'


def prepare():
    assert not WORK.exists() and not RESULT.exists()
    source=ROOT/'tmp/m441_boundary_protocol_05/verilog/m441_max_monitor.sv'
    monitor=source.read_text(encoding='utf-8-sig')
    tail=monitor[monitor.index('integer tail_hold_valid_cycles=0;'):monitor.rindex('endmodule')]
    env=ROOT/'tmp/m441_boundary_protocol_05/verilog/m89x_runtime_kernel_subsystem/m89x_runtime_kernel_env.sv'
    text=env.read_text(encoding='utf-8-sig')
    classes=re.findall(r'class (?:svr_latency_(?:tx|rx)|axi_latency_w[0-3]) extends[^;]+;.*?endclass',text,re.S)
    assert len(classes)==6
    classes=[re.sub(r'\s*`uvm_object_utils_(?:begin\([^)]*\)|end)','',c) for c in classes]
    code=r'''
`timescale 1ns/1ps
`define D apatb_m89x_runtime_kernel_top
module ready_fake; reg ready=1; endmodule
module svtb_fake; ready_fake svr_rx_if(); endmodule
class svr_latency; function new(string name="");endfunction endclass
class axi_latency; function new(string name="");endfunction endclass
'''+'\n'.join(classes)+r'''
module apatb_m89x_runtime_kernel_top;
svtb_fake svtb_top();
reg ap_clk=0;always #1 ap_clk=~ap_clk;
reg rx_TVALID=0,rx_TLAST=0;
integer words=327677,cycles=0,held_posedges=0;string test_case;
wire rx_TREADY=(test_case=="ready_error")?1'b1:svtb_top.svr_rx_if.ready;
task automatic progress_snapshot(input integer kind);
 $display("M441_COMPONENT_SNAPSHOT terminal=%0d",kind);
endtask
svr_latency_tx tx;svr_latency_rx rx;
axi_latency_w0 w0;axi_latency_w1 w1;axi_latency_w2 w2;axi_latency_w3 w3;
integer v;
initial begin
 if(!$value$plusargs("CASE=%s",test_case))$fatal(1,"CASE required");
 if(test_case=="latency")begin
  tx=new();rx=new();w0=new();w1=new();w2=new();w3=new();
  for(integer j=0;j<8192;j=j+1)begin
   v=tx.get_transfer_lat();if(v<0||v>8)$fatal(1,"tx range");
   v=rx.get_transfer_lat();if(v<0||v>8)$fatal(1,"rx range");
   v=w0.get_rctrl_lat();if(v<0||v>8)$fatal(1,"w0 AR range");
   v=w0.get_rdata_lat();if(v<0||v>8)$fatal(1,"w0 R range");
   v=w1.get_rctrl_lat();if(v<0||v>8)$fatal(1,"w1 AR range");
   v=w1.get_rdata_lat();if(v<0||v>8)$fatal(1,"w1 R range");
   v=w2.get_rctrl_lat();if(v<0||v>8)$fatal(1,"w2 AR range");
   v=w2.get_rdata_lat();if(v<0||v>8)$fatal(1,"w2 R range");
   v=w3.get_rctrl_lat();if(v<0||v>8)$fatal(1,"w3 AR range");
   v=w3.get_rdata_lat();if(v<0||v>8)$fatal(1,"w3 R range");
  end
  $display("M441_COMPONENT_LATENCY_DONE draws=81920");$finish;
 end
end
always @(posedge ap_clk)begin
 cycles=cycles+1;
 if(rx_TVALID&&rx_TLAST&&!rx_TREADY)held_posedges=held_posedges+1;
 if(rx_TVALID&&rx_TREADY)begin
  words=words+1;
  if(rx_TLAST)begin
   if(words!=327680||held_posedges!=128||tail_hold_valid_cycles!=128||!tail_released)$fatal(1,"tail count");
   $display("M441_COMPONENT_TAIL_DONE held_posedges=%0d",held_posedges);$finish;
  end
 end
 if(cycles>1000)$fatal(1,"component budget");
end
// Drive after the observer's negedge, avoiding a fabricated scheduling race.
always @(negedge ap_clk)begin
 #0.1;
 rx_TVALID=(test_case!="tail_gaps"||cycles%3!=0);
 rx_TLAST=(words==327679);
end
''' + tail + '\nendmodule\n'
    code=code.replace(tail,'').replace('integer v;','integer v;\n'+tail)
    atomic(WORK/'component.sv',code.encode('utf-8'),immutable=True)
    atomic(WORK/'component.prj',b'sv xil_defaultlib "component.sv"\n',immutable=True)
    atomic(WORK/'run.tcl',b'run all\nquit\n',immutable=True)
    atomic(WORK/'INPUT.json',encoded(dict(source_sha256=sha(source),env_sha256=sha(env),tail_exact=True,
        latency_methods_exact_except_UVM_registration=True,explicit_fake_signals=True,M441_DUT=False)),immutable=True)


def run():
    assert WORK.is_dir() and not RESULT.exists()
    tools='D:/AMDDesignTools/2026.1/Vivado/bin/'
    rows=[]
    def tool(name,cmd):
        assert not (WORK/(name+'_console.log')).exists()
        start=time.monotonic()
        with (WORK/(name+'_console.log')).open('xb') as f:
            p=subprocess.Popen(cmd,cwd=WORK,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
            while p.poll() is None:
                if time.monotonic()-start>300:
                    atomic(WORK/(name+'_exit.json'),encoded(dict(tool_rc=None,retained=True,pid=p.pid)),immutable=True)
                    raise RuntimeError('Component wall budget; retained child')
                time.sleep(.2)
        rc=p.returncode;atomic(WORK/(name+'_exit.json'),encoded(dict(tool_rc=rc)),immutable=True)
        rows.append(dict(name=name,tool_rc=rc));return rc
    assert tool('compile',[tools+'xelab.bat','xil_defaultlib.apatb_m89x_runtime_kernel_top','-prj','component.prj','-s','m441_boundary_component','-debug','typical','-v','2','-log','compile.log'])==0
    for case in ('tail','tail_gaps','ready_error','latency'):
        args=f'-testplusarg CASE={case}\n-sv_seed 441\n-tclbatch run.tcl\n-log {case}.log\n'
        atomic(WORK/(case+'.args'),args.encode('utf-8'),immutable=True)
        rc=tool(case,[tools+'xsim.bat','m441_boundary_component','-f',case+'.args'])
        log=(WORK/(case+'.log')).read_text(encoding='utf-8-sig',errors='replace')
        fatal=re.findall(r'^Fatal: ([^\r\n]+)',log,re.M)
        if case=='ready_error':assert len(fatal)==1 and 'ready not low' in fatal[0] and 'terminal=2' in log
        elif case=='latency':
            assert rc==0 and not fatal and 'M441_COMPONENT_LATENCY_DONE draws=81920' in log
            samples=re.findall(r'^M441_DELAY channel=(\w+) count=(\d+) sum=(\d+)\s*$',log,re.M)
            assert len(samples)==20 and len({x[0] for x in samples})==10
            assert all(0<int(total)<=8*int(count) for _,count,total in samples)
        else:assert rc==0 and not fatal and log.count('M441_COMPONENT_TAIL_DONE held_posedges=128')==1
        rows[-1]['gate_rc']=1 if fatal else rc
    result=dict(status='PASS_M441_BOUNDARY_ACTUAL_SV_COMPONENT_ONLY',cases=rows,explicit_fake_signals=True,
        M441_DUT=False,board=False,performance=False,source_sha256=sha(HERE/'m441_boundary_component08.py'),
        evidence=[dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p)) for p in sorted(WORK.glob('*')) if p.is_file()])
    atomic(RESULT,encoded(result),immutable=True)
    sync('latest_m441_boundary_component08',dict(status=result['status'],result=RESULT.relative_to(ROOT).as_posix(),sha256=sha(RESULT),board=False),
        f'## M441 有界边界实际SV组件08（2026-10-09）\n\nSHA {sha(RESULT)}；相同尾TLAST逻辑连续/间断VALID各128实际停顿通过，错误READY触发原fatal且gate拒绝；十个实际延迟函数81920抽样均0..8。明确fake接口/非M441 DUT，仅组件；未执行最大压力或板端。')
    print(result['status'],sha(RESULT),rows,flush=True)


if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('mode',choices=['Prepare','Run']);a.add_argument('--enable',action='store_true');args=a.parse_args()
    if args.mode=='Prepare':prepare()
    else:assert args.enable,'Default disabled';run()
