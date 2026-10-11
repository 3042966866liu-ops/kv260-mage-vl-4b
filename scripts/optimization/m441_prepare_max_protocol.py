"""Prepare fresh M441 max-descriptor/FIFO protocol inputs; never execute.

Execution remains locked on complete long-chain comparison and routed core.
The saved M357 zero-scale fixture tests protocol, not model numerical quality.
"""
import json
import re
from m351_workflow import ROOT, BASE, HERE, atomic, encoded, sha, sync
from m441_prepare_long_rtl import bindings
from m439_prepare_rtl import monitor


def make_monitor(bs):
    s=monitor(bs).replace('m439_monitor','m441_max_monitor').replace('M439','M441MAX')
    s=s.replace('cyc>500000','cyc>3100000').replace('cyc%50000','cyc%10000')
    s=s.replace('remaining[4][1024]','remaining[4][512]').replace('tail[i]>=1024','tail[i]-head[i]>=512')
    s=s.replace('remaining[i][tail[i]]','remaining[i][tail[i]%512]').replace('remaining[i][head[i]]','remaining[i][head[i]%512]')
    parents={b['queue_parent'].rsplit('.',1)[0] for b in bs};assert len(parents)==1
    four=parents.pop()
    extra='''
wire [3:0] shard_start,qwrite,qread,qfull;
wire [13:0] occupancy[4];wire [6:0] qcount[4];
reg [3:0] old_shard_start=0,old_AR_stall=0;
reg previous_output_stall=0;
reg [63:0] held_output,held_address[4];
reg [7:0] held_keep,held_strb,held_length[4];
reg held_last;reg [2:0] held_size[4];reg [1:0] held_burst[4];
longint descs[4],fifo_max[4],queue_writes[4],queue_reads[4],queue_full_cycles[4];
longint held=0,stable_output_stall_cycles=0,stable_AR_stall_cycles[4];
integer queue_high[4];
initial for(integer j=0;j<4;j=j+1)begin
 descs[j]=0;fifo_max[j]=0;queue_writes[j]=0;queue_reads[j]=0;queue_full_cycles[j]=0;queue_high[j]=0;stable_AR_stall_cycles[j]=0;
end
'''
    for b in bs:
        i=b['shard'];parent=b['queue_parent'];q=parent+'.records_U'
        name='result_num_data_valid' if i==0 else f'result_{i}_num_data_valid'
        extra+=f'''assign shard_start[{i}]={parent}.ap_start;
assign occupancy[{i}]={four}.{name};
assign qwrite[{i}]={q}.if_write && {q}.if_write_ce && {q}.if_full_n;
assign qread[{i}]={q}.if_read && {q}.if_read_ce && {q}.if_empty_n;
assign qfull[{i}]=!{q}.if_full_n;
assign qcount[{i}]={q}.if_num_data_valid;
'''
    anchor='integer cyc=0,i,words=0,lasts=0;';assert s.count(anchor)==1;s=s.replace(anchor,anchor+extra)
    anchor='  if(live[i])begin';assert s.count(anchor)==1
    update='''  if(shard_start[i]&&!old_shard_start[i])descs[i]=descs[i]+1;
  if(occupancy[i]>8192)$fatal(1,"M441MAX output FIFO overflow");
  if(occupancy[i]>fifo_max[i])fifo_max[i]=occupancy[i];
  if(qwrite[i])queue_writes[i]=queue_writes[i]+1;
  if(qread[i])queue_reads[i]=queue_reads[i]+1;
  if(qfull[i])queue_full_cycles[i]=queue_full_cycles[i]+1;
  if(qcount[i]>queue_high[i])queue_high[i]=qcount[i];
  if(qcount[i]>34||queue_reads[i]>queue_writes[i]||queue_writes[i]-queue_reads[i]>34)$fatal(1,"M441MAX record queue bound");
  if(`D.ap_rst_n)begin
   if(old_AR_stall[i])begin
    if(!avalid[i]||addresses[i]!==held_address[i]||lens[i]!==held_length[i]||sizes[i]!==held_size[i]||bursts[i]!==held_burst[i])$fatal(1,"M441MAX unstable stalled AR");
    stable_AR_stall_cycles[i]=stable_AR_stall_cycles[i]+1;
   end
   old_AR_stall[i]=avalid[i]&&!aready[i];
   held_address[i]=addresses[i];held_length[i]=lens[i];held_size[i]=sizes[i];held_burst[i]=bursts[i];
  end else old_AR_stall[i]=0;
'''
    s=s.replace(anchor,update+anchor)
    anchor=' old_start=start;';assert s.count(anchor)==1
    s=s.replace(anchor,anchor+'''
 old_shard_start=shard_start;
 if(`D.rx_TVALID&&!`D.rx_TREADY)held=held+1;
 if(`D.ap_rst_n)begin
  if(previous_output_stall)begin
   if(!`D.rx_TVALID||`D.rx_TDATA!==held_output||`D.rx_TKEEP!==held_keep||`D.rx_TSTRB!==held_strb||`D.rx_TLAST!==held_last)$fatal(1,"M441MAX unstable stalled output");
   stable_output_stall_cycles=stable_output_stall_cycles+1;
  end
  previous_output_stall=`D.rx_TVALID&&!`D.rx_TREADY;
  held_output=`D.rx_TDATA;held_keep=`D.rx_TKEEP;held_strb=`D.rx_TSTRB;held_last=`D.rx_TLAST;
 end else previous_output_stall=0;
''')
    anchor=' if(`D.ap_done)begin';assert s.count(anchor)==1
    s=s.replace(anchor,anchor+'''
  if(words!=327680||lasts!=1)$fatal(1,"M441MAX output count/TLAST");
  $display("M441MAX_HELD_VALID=%0d STABLE_OUTPUT_CYCLES=%0d",held,stable_output_stall_cycles);
  for(integer j=0;j<4;j=j+1)begin
   if(descs[j]!=10||calls[j]!=2560||iterations[j]!=40960||rr[j]!=10880||tail[j]!=head[j]||badlast[j]||badresp[j])$fatal(1,"M441MAX incomplete descriptor/MAC/R protocol");
   if(queue_writes[j]!=10880||queue_reads[j]!=10880||qcount[j]!=0||queue_high[j]!=34||queue_full_cycles[j]==0)$fatal(1,"M441MAX record FIFO incomplete");
   $display("M441MAX_PROTOCOL shard=%0d descriptors=%0d FIFO_MAX=%0d queue_writes=%0d queue_reads=%0d queue_high=%0d queue_full=%0d queue_final=%0d AR_STABLE=%0d",j,descs[j],fifo_max[j],queue_writes[j],queue_reads[j],queue_high[j],queue_full_cycles[j],qcount[j],stable_AR_stall_cycles[j]);
  end
''')
    return s,four


def make_tcl(four):
    path=four.replace('`D','/apatb_m89x_runtime_kernel_top/AESL_inst_m89x_runtime_kernel').replace('.','/')
    names=['result_num_data_valid']+[f'result_{i}_num_data_valid' for i in (1,2,3)]
    return f'''set ready /apatb_m89x_runtime_kernel_top/svtb_top/svr_rx_if/ready
set ar /apatb_m89x_runtime_kernel_top/svtb_top/axi_w0_if/ARREADY
set core {path}
add_force $ready 0
add_force $ar 0
run 48us
if {{[get_value -radix unsigned /apatb_m89x_runtime_kernel_top/w0_ARREADY] != 0 || [get_value -radix unsigned /apatb_m89x_runtime_kernel_top/w0_ARVALID] != 1}} {{error "Actual pending AXI hold missing"}}
puts "M441MAX_SHARED_VIP_WEIGHT_AR_HOLD_VERIFIED cycles=10000"
remove_forces $ar
for {{set i 1}} {{$i <= 9}} {{incr i}} {{run 48us; puts "M441MAX_CHUNK_PROGRESS time=[current_time]"}}
if {{[get_value -radix unsigned /apatb_m89x_runtime_kernel_top/rx_TREADY] != 0 || [get_value -radix unsigned /apatb_m89x_runtime_kernel_top/rx_TVALID] != 1}} {{error "Actual held valid output missing"}}
set full 0
foreach name {{{' '.join(names)}}} {{
 set occupancy [get_value -radix unsigned $core/$name]
 puts "M441MAX_FIFO_HOLD_SNAPSHOT name=$name occupancy=$occupancy"
 if {{$occupancy > 8192}} {{error "FIFO capacity overflow"}}
 if {{$occupancy == 8192}} {{incr full}}
}}
if {{$full < 1}} {{error "Maximum legal FIFO occupancy not reached before release"}}
puts "M441MAX_SHARED_VIP_OUTPUT_HOLD_VERIFIED cycles=100000"
remove_forces $ready
for {{set i 1}} {{$i <= 300}} {{incr i}} {{
 run 48us
 puts "M441MAX_CHUNK_PROGRESS time=[current_time] words=[get_value -radix unsigned /m441_max_monitor/words]"
 if {{[get_value -radix unsigned /m441_max_monitor/words] == 327680 && [get_value -radix unsigned /m441_max_monitor/lasts] == 1}} {{break}}
}}
if {{[get_value -radix unsigned /m441_max_monitor/words] != 327680}} {{error "Bounded maximum cycle budget exceeded"}}
run 480ns
quit
'''


def main():
    numeric=BASE/'runs/M441-full-numeric-csim-01/RESULT.json'
    n=json.loads(numeric.read_bytes());assert n['status']=='PASS_M441_FULL_REAL_WEIGHT_CHAIN_CSIM'
    board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    assert board['latest_m441_full_numeric_csim']['sha256']==sha(numeric)
    assert all(sha(numeric) in (ROOT/x).read_text(encoding='utf-8-sig') for x in ('CURRENT_STATE.md','docsMILESTONES.md'))
    prepared=BASE/'runs/M441-record-pipeline-preparation-02/RESULT.json'
    p=json.loads(prepared.read_bytes());assert p['build_id']=='0x4D343431'
    support=ROOT/'tmp/m438_weight_wait_03'
    support_result=BASE/'runs/M438-weight-wait-preparation-01/RESULT.json'
    supports=json.loads(support_result.read_bytes())['files']
    fixture=BASE/'runs/M357-max-fifo-preparation-01/RESULT.json'
    assert sha(fixture)=='6d16e74640d763803a886bddd3fc85364f6dac51d49cc9fd3d4f9df92b9d16f1'
    f=json.loads(fixture.read_bytes());assert (f['descriptor_count'],f['rows_per_shard'],f['output_words'])==(10,512,327680)
    oldfixture=ROOT/'tmp/m357_maxfifo_trace';syn=ROOT/'tmp/m441_hls_project_02/hls/syn/verilog'
    out=ROOT/'tmp/m441_max_protocol_01';assert not out.exists(),'Existing preparation: read only'
    bs=bindings(syn,'B');observed,four=make_monitor(bs)
    copied=[]
    for row in supports:
        source=ROOT/row['path'];rel=source.relative_to(support)
        if rel.parts[0]=='verilog' and (len(rel.parts)>2 or source.name in ('glbl.v','fifo_para.vh','m89x_runtime_kernel.autotb.v')):
            assert sha(source)==row['sha256'];atomic(out/rel,source.read_bytes(),immutable=True);copied.append(row)
    for model in (support/'verilog/ip/xil_defaultlib').glob('*.vhd'):
        wrapper=model.name[:-7]+'.v';assert sha(syn/wrapper)==sha(support/'verilog'/wrapper),wrapper
    for source in sorted(syn.glob('*.v')):atomic(out/'verilog'/source.name,source.read_bytes(),immutable=True)
    for row in f['files']:
        source=ROOT/row['path'];assert sha(source)==row['sha256']
        rel=source.relative_to(oldfixture)
        if rel.parts[0]=='verilog':continue
        raw=source.read_bytes()
        if source.name.endswith('autotvout_ap_return.dat'):
            assert b'0x4d333537' in raw;raw=raw.replace(b'0x4d333537',b'0x4d343431')
        atomic(out/rel,raw,immutable=True)
    (out/'tv/rtldatafile').mkdir(parents=True,exist_ok=True)
    fourtext=(syn/'m89x_runtime_kernel_m89x_four.v').read_text(encoding='utf-8-sig')
    assert all(name in fourtext for name in ['result_num_data_valid']+[f'result_{i}_num_data_valid' for i in (1,2,3)])
    top=(syn/'m89x_runtime_kernel.v').read_text(encoding='utf-8-sig')
    assert all(re.search(r'\b'+name+r'\b',top) for name in ('rx_TDATA','rx_TKEEP','rx_TSTRB','rx_TLAST','ap_rst_n'))
    atomic(out/'verilog/m441_max_monitor.sv',observed.encode('utf-8'),immutable=True)
    watchdog=(HERE/'m357_rtl_watchdog.sv').read_text(encoding='utf-8-sig').replace('m357','m441').replace('M357','M441MAX')
    atomic(out/'verilog/m441_rtl_watchdog.sv',watchdog.encode('utf-8'),immutable=True)
    vip=[line for line in (support/'verilog/m438.prj').read_text(encoding='utf-8-sig').splitlines() if line.startswith('vhdl ') or any('/'+d+'/' in line for d in ('svr','axivip','svtb','file_agent','m89x_runtime_kernel_subsystem'))]
    prj=vip+['sv xil_defaultlib "glbl.v"','sv xil_defaultlib "m89x_runtime_kernel.autotb.v"']+['sv xil_defaultlib "'+source.name+'"' for source in sorted(syn.glob('*.v'))]+['sv xil_defaultlib "m441_max_monitor.sv"','sv xil_defaultlib "m441_rtl_watchdog.sv"']
    atomic(out/'verilog/m441_max.prj',('\n'.join(prj)+'\n').encode('utf-8'),immutable=True)
    atomic(out/'verilog/max.tcl',make_tcl(four).encode('utf-8'),immutable=True)
    atomic(out/'verilog/timeout.tcl',b'run all\nquit\n',immutable=True)
    consumed=set()
    for path in (out/'verilog').rglob('*'):
        if path.suffix in ('.v','.sv','.svh','.vh'):
            consumed.update(re.findall(r'"(\.\./tv/(?:cdatafile|stream_size)/[^"\r\n]+)"',path.read_text(encoding='utf-8-sig')))
    for rel in consumed:assert (out/'verilog'/rel).resolve().is_file(),rel
    result=dict(status='PREPARED_M441_MAXIMUM_PROTOCOL_NO_EXECUTION',build_id='0x4D343431',numerical_sha256=sha(numeric),
                source_preparation_sha256=sha(prepared),fixture_sha256=sha(fixture),support_sha256=sha(support_result),
                generator_sha256=sha(HERE/'m441_prepare_max_protocol.py'),MAC_bindings=bs,copied_support=copied,
                expected=dict(descriptors_per_shard=10,MAC_calls_per_shard=2560,iterations_per_shard=40960,weight_words_per_shard=10880,
                              output_words=327680,output_bytes=2621440,output_FIFO_capacity=8192,record_FIFO_capacity=34,
                              per_shard_address_coverage='Each word 0..1087 read exactly 10 times; repeated descriptor addresses are legal'),
                virtual_cycle_budget=3100000,address_hold_cycles=10000,output_hold_cycles=100000,
                negative_timeout_cycles_after_start=200,seed=441,
                protocol_oracle='Original nonzero activations/codes with zero scales => all-zero outputs. Does not replace full real-weight numerical/benefit evidence.',
                entry_prerequisites=['PASS_M441_COMPLETE_LONG_CHAIN_RTL_COMPARISON with synchronized SHA',
                                     'Same-constraint M441 routed core resources/timing PASS with synchronized SHA',
                                     'Actual control/collector safety checks before launch'],
                checks=['Exact four generated shard wrapper starts,10 descriptors/MAC work/read totals',
                        'All actual VIP input file consumers/FP wrappers hash-closed',
                        'Shared interface holds and actual pending AR/held-valid observed; at least one output FIFO8192',
                        'All four record FIFO34 actual full/backpressure/drain, no overflow or extra consume',
                        'AR and output payload/keep/strb/TLAST stable throughout stalls',
                        'Full output/Build/last/done/return; burst length/boundary and exact repeated record coverage',
                        'Separate started 200-cycle timeout rejected even if Xsim rc0; same compiled DUT but isolated files'],
                actual_VIP_filename_closure=len(consumed),debug_metadata_required=True,
                files=[dict(path=x.relative_to(ROOT).as_posix(),sha256=sha(x)) for x in sorted(out.rglob('*')) if x.is_file()],
                compiled=False,simulated=False,board=False,full_shell=False,promoted=False,
                next='Only prepare control/collector; do not execute until long-chain comparison and routed-core prerequisites pass.')
    folder=BASE/'runs/M441-max-protocol-preparation-01';ev=folder/'RESULT.json'
    atomic(ev,encoded(result),immutable=True)
    report='# M441 最大描述符、FIFO与背压门禁准备\n\n只准备新RTL输入和观察器，未编译/仿真；不复用旧编译DUT，不改变正在运行的长链。\n\n'
    report+='\n'.join('- '+item for item in result['checks'])+'\n\n'
    report+='固定10descriptor、G1/W4、512 rows/shard；327680个输出字共2621440B。零scale协议夹具不代表真实模型质量或性能。\n\n'
    report+='完整长链周期裁决和同约束核心路由均通过并同步，实际控制/回收检查通过后才可启动；失败停本级，不重跑已通过长链补证据。\n'
    atomic(folder/'PLAN.md',report.encode('utf-8'),immutable=True)
    sync('latest_m441_max_protocol_preparation',dict(status=result['status'],result=ev.relative_to(ROOT).as_posix(),sha256=sha(ev),board=False),
         f'## M441 最大FIFO/背压/超时输入准备（2026-10-07）\n\nSHA {sha(ev)}；独立新M441 RTL/10descriptor原协议夹具，动态绑定实际consumer MAC、shard wrapper和两级FIFO，8192输出/34权重容量及payload/AR稳定检查。0compile/仿真/上板；不改正在运行A/B或M439 FAIL。完整长链周期及同约束核心PASS和收集控制检查后才允许执行。')
    print(result['status'],sha(ev),len(result['files']),len(consumed))


if __name__=='__main__':main()
