"""Unchanged M357 RTL, one real-weight Q block, observational counters only."""
import hashlib,json,re,shutil,struct
from pathlib import Path
from m351_workflow import ROOT,BASE,atomic,encoded,sha,sync

SRC=ROOT/'tmp/m357_candidate_q_trace'
OUT=ROOT/'tmp/m438_weight_wait_01'
PREFIX='c.m89x_runtime_kernel.'

def values(p):
    s=p.read_text(encoding='utf-8-sig')
    return [int(x,16) for x in re.findall(r'(?m)^0x([0-9a-fA-F]+)\s*$',s)]

def tv(p,v):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text('[[[runtime]]]\n[[transaction]] 0\n'+'\n'.join(map(str,v))+'\n[[/transaction]]\n[[[/runtime]]]\n',encoding='utf-8')

def monitor():
    s='''`timescale 1ns/1ps
`define D apatb_m89x_runtime_kernel_top.AESL_inst_m89x_runtime_kernel
module m438_monitor;
integer cyc=0,i,words=0,lasts=0;
longint active[4],addr_phase[4],data_phase[4],addr_wait[4],data_wait[4],mac_phase[4],other[4];
longint calls[4],iterations[4],ar[4],rr[4],burst[4],ar_mac[4],r_mac[4],internal_ar_mac[4];
reg [3:0] live=0,old_start=0;
wire [3:0] start,done,iter;
wire [3:0] adr,dat,mp,aw,dw,arok,rok,iar;
wire [7:0] lens[4];
initial for(i=0;i<4;i=i+1)begin
 active[i]=0;addr_phase[i]=0;data_phase[i]=0;addr_wait[i]=0;data_wait[i]=0;mac_phase[i]=0;other[i]=0;
 calls[i]=0;iterations[i]=0;ar[i]=0;rr[i]=0;burst[i]=0;ar_mac[i]=0;r_mac[i]=0;internal_ar_mac[i]=0;
end
'''
    for i in range(4):
        suffix='' if i==0 else '_'+str(i)
        q=f'`D.grp_m89x_four_fu_404.m89x_shard{suffix}_U0'
        rtl=(SRC/'verilog'/f'm89x_runtime_kernel_m89x_shard{suffix}.v').read_text(encoding='utf-8')
        inst=re.findall(r'\b(m89x_shard\w*_Pipeline_VITIS_LOOP_80_6_fu_\d+) \(',rtl)
        assert len(inst)==1,inst
        child=q+'.'+inst[0]
        child_text=(SRC/'verilog'/f'm89x_runtime_kernel_m89x_shard{suffix}_Pipeline_VITIS_LOOP_80_6.v').read_text(encoding='utf-8')
        cmp=re.findall(r'assign (icmp_ln80_\w+_p2) = \(\(ap_sig_allocacmp_token_pair_1 == 5\x27d16\)',child_text)
        assert len(cmp)==1,cmp
        for name,nums in [('adr',(11,21,22,31,32)),('dat',(19,29,30,39,40))]:
            s+=f'assign {name}[{i}] = '+' | '.join(q+f'.ap_CS_fsm_state{n}' for n in nums)+';\n'
        s+=f'''assign mp[{i}]={q}.ap_CS_fsm_state54;
assign aw[{i}]=adr[{i}] && !{q}.m_axi_w{i}_0_ARREADY;
assign dw[{i}]=dat[{i}] && !{q}.m_axi_w{i}_0_RVALID;
assign start[{i}]={q}.grp_{inst[0]}_ap_start;
assign done[{i}]={q}.ap_done;
assign iter[{i}]={child}.ap_enable_reg_pp0_iter0 && !{child}.{cmp[0]} && !{child}.ap_block_pp0_stage0_subdone;
assign arok[{i}]=`D.m_axi_w{i}_ARVALID && `D.m_axi_w{i}_ARREADY;
assign rok[{i}]=`D.m_axi_w{i}_RVALID && `D.m_axi_w{i}_RREADY;
assign iar[{i}]={q}.m_axi_w{i}_0_ARVALID && {q}.m_axi_w{i}_0_ARREADY;
assign lens[{i}]=`D.m_axi_w{i}_ARLEN;
'''
        # Use the outer shard start, not the MAC start, for active lifetime.
        s+=f'always @(posedge `D.ap_clk)begin if({q}.ap_start)live[{i}]=1; if({q}.ap_done)live[{i}]=0; end\n'
    s+='''always @(posedge `D.ap_clk)begin
 cyc=cyc+1;
 if(cyc>500000)$fatal(1,"M438 bounded RTL cycle budget exceeded");
 for(i=0;i<4;i=i+1)begin
  if(live[i])begin
   active[i]=active[i]+1;
   if(adr[i])addr_phase[i]=addr_phase[i]+1;
   else if(dat[i])data_phase[i]=data_phase[i]+1;
   else if(mp[i])mac_phase[i]=mac_phase[i]+1;
   else other[i]=other[i]+1;
   if(aw[i])addr_wait[i]=addr_wait[i]+1;
   if(dw[i])data_wait[i]=data_wait[i]+1;
  end
  if(start[i]&&!old_start[i])calls[i]=calls[i]+1;
  if(iter[i])iterations[i]=iterations[i]+1;
  if(arok[i])begin ar[i]=ar[i]+1;if(lens[i]!=0)burst[i]=burst[i]+1;if(mp[i])ar_mac[i]=ar_mac[i]+1;end
  if(rok[i])begin rr[i]=rr[i]+1;if(mp[i])r_mac[i]=r_mac[i]+1;end
  if(iar[i]&&mp[i])internal_ar_mac[i]=internal_ar_mac[i]+1;
 end
 old_start=start;
 if(`D.rx_TVALID&&`D.rx_TREADY)begin words=words+1;if(`D.rx_TLAST)lasts=lasts+1;end
 if(cyc%50000==0)$display("M438_HEARTBEAT cycle=%0d output=%0d",cyc,words);
 if(`D.ap_done)begin
  $display("M438_DONE cycles=%0d output=%0d tlast=%0d return=%0h",cyc,words,lasts,`D.ap_return);
  for(i=0;i<4;i=i+1)$display("M438_METRIC shard=%0d active=%0d address_phase=%0d data_phase=%0d address_wait=%0d data_wait=%0d mac_phase=%0d other=%0d mac_calls=%0d iterations=%0d AR=%0d R=%0d multi_beat=%0d AR_during_MAC=%0d R_during_MAC=%0d internal_AR_during_MAC=%0d",i,active[i],addr_phase[i],data_phase[i],addr_wait[i],data_wait[i],mac_phase[i],other[i],calls[i],iterations[i],ar[i],rr[i],burst[i],ar_mac[i],r_mac[i],internal_ar_mac[i]);
 end
end
endmodule
'''
    return s

def main():
    assert not OUT.exists(),'Immutable attempt exists; inspect/collect only'
    prep=json.loads((BASE/'runs/M357-activation-bank-hls-01/RESULT.json').read_bytes())
    checked=[]
    for row in prep['rtl_inputs']:
        p=ROOT/row['path']
        if p.is_relative_to(SRC/'verilog') and p.suffix in ('.v','.sv','.svh','.vh','.vhd','.mem'):
            assert sha(p)==row['sha256'],p
            if p.name=='m357_trace_monitor.sv':continue
            target=OUT/'verilog'/p.relative_to(SRC/'verilog');target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
            checked.append(dict(path=row['path'],sha256=row['sha256'],copy=target.relative_to(ROOT).as_posix()))
    assert len(checked)>70
    shutil.copytree(SRC/'tv/cdatafile',OUT/'tv/cdatafile');shutil.copytree(SRC/'tv/stream_size',OUT/'tv/stream_size')
    (OUT/'tv/rtldatafile').mkdir()
    data=OUT/'tv/cdatafile';src=SRC/'tv/cdatafile'
    weights=[]
    for i in range(4):
        p=src/(PREFIX+f'autotvin_w{i}.dat');raw=p.read_bytes()
        assert len(raw)==737296 and struct.unpack('>Q',raw[:8])[0]==46080 and raw[-8:]==bytes.fromhex('5a5aa5a50f0ff0f0')
        selected=b''.join(raw[8+g*64*9*16:8+(g*64*9+9)*16] for g in range(40))
        assert len(selected)==5760
        (data/p.name).write_bytes(struct.pack('>Q',360)+selected+raw[-8:])
        weights.append(dict(source_sha256=sha(p),selected_sha256=hashlib.sha256(selected).hexdigest(),groups=40,record_words=9,source_blocks=64,selected_block=0))
    packet=values(src/(PREFIX+'autotvin_tx_V_data_V.dat'));assert len(packet)==6402
    packet=[(packet[0]&~(1023<<32))|(8<<32)]+packet[2:];assert len(packet)==6401
    expected=values(src/(PREFIX+'autotvout_rx_V_data_V.dat'))[:512];assert len(expected)==512
    for direction,port,vals,width in [('in','tx',packet,16),('out','rx',expected,8)]:
        for field in ('data','keep','strb','last'):
            v=vals if field=='data' else ([int(j==len(vals)-1) for j in range(len(vals))] if field=='last' else [(1<<width)-1]*len(vals))
            tv(data/(PREFIX+f'autotv{direction}_{port}_V_{field}_V.dat'),['0x'+format(x,'x') for x in v])
            tv(OUT/'tv/stream_size'/f'stream_size_{direction}_{port}_V_{field}_V.dat',[len(vals)])
    tv(data/(PREFIX+'autotvin_config_r.dat'),['0x00010228'])
    tv(data/(PREFIX+'autotvout_ap_return.dat'),['0x4d333537'])
    golden=b''.join(x.to_bytes(8,'little') for x in expected);(OUT/'golden.bin').write_bytes(golden)
    mon=monitor();(OUT/'verilog/m438_monitor.sv').write_text(mon,encoding='utf-8')
    env=OUT/'verilog/m89x_runtime_kernel_subsystem/m89x_runtime_kernel_env.sv';text=env.read_text(encoding='utf-8')
    text,n=re.subn(r'(virtual function int get_\w+\(\);)\s*(int delay;)',r'\1\n            \2\n            if ($test$plusargs("M438_ZERO_EXTRA_LATENCY")) return 0;',text);assert n==27
    env.write_text(text,encoding='utf-8')
    prj=(SRC/'verilog/m357.prj').read_text(encoding='utf-8').replace('m357_trace_monitor.sv','m438_monitor.sv')
    (OUT/'verilog/m438.prj').write_text(prj,encoding='utf-8');(OUT/'verilog/m438_run.tcl').write_text('run all\nquit\n',encoding='utf-8')
    result=dict(status='PREPARED_M438_UNCHANGED_RTL_WEIGHT_WAIT_OBSERVER',build_id='0x4D333537',board=False,dut_changed=False,old_evidence_unchanged=True,
      fixture=dict(family='layer0 Q W2',groups=40,rows_per_shard=8,descriptors=1,tokens=32,input_words128=6401,output_words64=512,weights=weights,golden_sha256=sha(OUT/'golden.bin'),activation='Original M355 deterministic frozen representative activation; not captured video activation'),
      unchanged_rtl=checked,latency_modes=['original random 0..256 seed356','zero added VIP latency seed356'],monitor_sha256=sha(OUT/'verilog/m438_monitor.sv'),
      scope='Partition parent shard active cycles into address/data/MAC/other; actual blocked states and MAC loop accepted iterations. Counts are per shard, not additive board wall time. Read/compute concurrency is observed, not guessed from interface settings.',
      expected=dict(mac_calls_per_shard=160,accepted_token_pair_iterations_per_shard=2560,weight_beats_per_shard=360),cycle_budget=500000,
      files=[dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p)) for p in sorted(OUT.rglob('*')) if p.is_file()])
    out=BASE/'runs/M438-weight-wait-preparation-01/RESULT.json';atomic(out,encoded(result),immutable=True)
    sync('latest_m438_weight_wait_preparation',dict(status=result['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out),build_id=result['build_id'],board=False),
      f'## M438 权重读等待窄RTL观察准备（2026-10-07）\n\nSHA {sha(out)}；未改M357 DUT/服务，原真实Q权重首块40组、原冻结确定性激活（非视频捕获），完整512输出参考；静态FSM54执行MAC、11/21/22/31/32地址及19/29/30/39/40返回等待相分离。准备原随机/零额外延迟两模型、500000周期预算与逐shard MAC有效迭代/读等待计数；0板端/新性能，旧M437收益保持。下一步只离线编译及这两固定窄仿真，不借仿真宣称板端DDR瓶颈。')
    print('M438_PREPARED',sha(out),len(checked))
if __name__=='__main__':main()
