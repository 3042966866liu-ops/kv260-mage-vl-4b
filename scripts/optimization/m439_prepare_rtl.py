"""Fresh small DUT/VIP traces; original W2 evidence is reused, not rerun."""
import re,json,struct,importlib.util,sys
import numpy as np
from m351_workflow import ROOT,BASE,atomic,encoded,sha,sync
from m438_prepare import tv,values,PREFIX
from m355_reference import full_reference

def mac_bindings(syn):
    top=(syn/'m89x_runtime_kernel.v').read_text(encoding='utf-8')
    four=re.findall(r'm89x_runtime_kernel_m89x_four\s+(grp_m89x_four_fu_\d+)\s*\(',top)
    assert len(four)==1,four
    bindings=[]
    for i in range(4):
        suffix='' if i==0 else '_'+str(i)
        p=syn/f'm89x_runtime_kernel_m89x_shard{suffix}.v';t=p.read_text(encoding='utf-8')
        hits=[]
        for module,inst in re.findall(r'(m89x_runtime_kernel_m89x_shard\w*_Pipeline_\w+)\s+(grp_\w+_fu_\d+)\s*\(',t):
            ct=(syn/(module+'.v')).read_text(encoding='utf-8')
            cmp=re.findall(r"assign (icmp_ln\w+_p2) = \(\(ap_sig_allocacmp_token_pair_\d+ == 5'd16\)",ct)
            if cmp:
                assert len(cmp)==1
                assert 'ap_enable_reg_pp0_iter0' in ct and 'ap_block_pp0_stage0_subdone' in ct
                hits.append(dict(instance=inst,module=module,compare=cmp[0]))
        assert len(hits)==1,(p,hits)
        bindings.append(dict(shard=i,parent=f'`D.{four[0]}.m89x_shard{suffix}_U0',**hits[0]))
    return bindings

def monitor(bindings):
    s='''`timescale 1ns/1ps
`define D apatb_m89x_runtime_kernel_top.AESL_inst_m89x_runtime_kernel
module m439_monitor;
integer cyc=0,i,words=0,lasts=0;
longint active[4],mac_busy[4],calls[4],iterations[4],ar[4],rr[4],gap[4],rstall[4],arstall[4],ar_mac[4],r_mac[4];
integer head[4],tail[4],remaining[4][1024],badlast[4],badresp[4];
reg [3:0] live=0,old_start=0;
wire [3:0] start,iter,busy,arok,rok,rdvalid,rdready,avalid,aready,rlast;
wire [7:0] lens[4];wire [63:0] addresses[4];wire [2:0] sizes[4];wire [1:0] bursts[4],resp[4];
initial for(i=0;i<4;i=i+1)begin
 active[i]=0;mac_busy[i]=0;calls[i]=0;iterations[i]=0;ar[i]=0;rr[i]=0;gap[i]=0;rstall[i]=0;arstall[i]=0;ar_mac[i]=0;r_mac[i]=0;head[i]=0;tail[i]=0;badlast[i]=0;badresp[i]=0;
end
'''
    for b in bindings:
        i=b['shard'];q=b['parent'];child=q+'.'+b['instance']
        s+=f'''assign start[{i}]={q}.{b['instance']}_ap_start;
assign iter[{i}]={child}.ap_enable_reg_pp0_iter0 && !{child}.{b['compare']} && !{child}.ap_block_pp0_stage0_subdone;
assign busy[{i}]=!{child}.ap_idle;
assign arok[{i}]=`D.m_axi_w{i}_ARVALID && `D.m_axi_w{i}_ARREADY;
assign rok[{i}]=`D.m_axi_w{i}_RVALID && `D.m_axi_w{i}_RREADY;
assign lens[{i}]=`D.m_axi_w{i}_ARLEN; assign addresses[{i}]=`D.m_axi_w{i}_ARADDR;
assign sizes[{i}]=`D.m_axi_w{i}_ARSIZE;assign bursts[{i}]=`D.m_axi_w{i}_ARBURST;
assign rdvalid[{i}]=`D.m_axi_w{i}_RVALID;assign rdready[{i}]=`D.m_axi_w{i}_RREADY;
assign avalid[{i}]=`D.m_axi_w{i}_ARVALID;assign aready[{i}]=`D.m_axi_w{i}_ARREADY;
assign rlast[{i}]=`D.m_axi_w{i}_RLAST;assign resp[{i}]=`D.m_axi_w{i}_RRESP;
always @(posedge `D.ap_clk)begin if({q}.ap_start)live[{i}]=1;if({q}.ap_done)live[{i}]=0;end
'''
    s+='''always @(posedge `D.ap_clk)begin
 cyc=cyc+1;if(cyc>500000)$fatal(1,"M439 bounded RTL cycle budget exceeded");
 for(i=0;i<4;i=i+1)begin
  if(live[i])begin active[i]=active[i]+1;if(busy[i])mac_busy[i]=mac_busy[i]+1;end
  if(start[i]&&!old_start[i])calls[i]=calls[i]+1;
  if(iter[i])iterations[i]=iterations[i]+1;
  if(tail[i]>head[i]&&rdready[i]&&!rdvalid[i])gap[i]=gap[i]+1;
  if(rdvalid[i]&&!rdready[i])rstall[i]=rstall[i]+1;
  if(avalid[i]&&!aready[i])arstall[i]=arstall[i]+1;
  if(arok[i])begin
   if(tail[i]>=1024)$fatal(1,"M439 address queue budget exceeded");
   remaining[i][tail[i]]=lens[i]+1;tail[i]=tail[i]+1;ar[i]=ar[i]+1;
   if(busy[i]&&live[i])ar_mac[i]=ar_mac[i]+1;
   $display("M439_AR shard=%0d address=%0h len=%0d size=%0d burst=%0d",i,addresses[i],lens[i],sizes[i],bursts[i]);
  end
  if(rok[i])begin
   if(head[i]>=tail[i])$fatal(1,"M439 return without recorded address");
   if(rlast[i]!=(remaining[i][head[i]]==1))badlast[i]=badlast[i]+1;
   if(resp[i]!=0)badresp[i]=badresp[i]+1;
   remaining[i][head[i]]=remaining[i][head[i]]-1;if(remaining[i][head[i]]==0)head[i]=head[i]+1;
   rr[i]=rr[i]+1;if(busy[i]&&live[i])r_mac[i]=r_mac[i]+1;
  end
 end
 old_start=start;
 if(`D.rx_TVALID&&`D.rx_TREADY)begin words=words+1;if(`D.rx_TLAST)lasts=lasts+1;end
 if(cyc%50000==0)$display("M439_HEARTBEAT cycle=%0d output=%0d",cyc,words);
 if(`D.ap_done)begin
  $display("M439_DONE cycles=%0d output=%0d tlast=%0d",cyc,words,lasts);
  for(i=0;i<4;i=i+1)$display("M439_METRIC shard=%0d active=%0d mac_busy=%0d mac_calls=%0d iterations=%0d AR=%0d R=%0d return_gap=%0d RSTALL=%0d ARSTALL=%0d AR_during_MAC=%0d R_during_MAC=%0d pending=%0d bad_RLAST=%0d bad_RRESP=%0d",i,active[i],mac_busy[i],calls[i],iterations[i],ar[i],rr[i],gap[i],rstall[i],arstall[i],ar_mac[i],r_mac[i],tail[i]-head[i],badlast[i],badresp[i]);
 end
end
endmodule
'''
    return s

def w4_fixture():
    p=ROOT/'deployment/mage_vl4b/m120_text4b_runtime/m120_fixture.py'
    spec=importlib.util.spec_from_file_location('m439_original_fixture',p);m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
    asset=ROOT/'deployment/mage_vl4b/artifacts/m128_m120_real_record_csim_fixture.bin'
    assert sha(asset)=='f384f45eea4bc14110a7add49dd0944f0a025403aecc3360369ec999e28257d9'
    case=m.load_fixture(asset)[1];assert (case.bits,case.groups,case.family)==(4,40,5)
    f=m.build_case(case,1)
    chain=dict(groups=40,bits=4,descriptors=[dict(rows_per_shard=8,encoded_u64=hex((8<<32)|(4<<42)))],output_bytes=4096)
    golden=full_reference(chain,f['weights'],0,f['packet'])
    g=np.frombuffer(f['expected'],dtype='<u2').copy();mask=((g&0x7c00)==0)&((g&0x3ff)!=0);g[mask]&=np.uint16(0x8000)
    assert golden==g.tobytes(),'Two independently organized frozen references differ'
    return f,golden,dict(ordinal=1,family=5,bits=4,groups=40,tokens=32,descriptors=1,rows_per_shard=8,fixture_sha256=sha(asset),reference_source_sha256=sha(p),reference2_source_sha256=sha(ROOT/'scripts/optimization/m355_reference.py'))

def main():
    tag=sys.argv[1];assert tag in ('candidate_w2','baseline_w4','candidate_w4')
    ev=BASE/'runs/M439-record-load-hls-02/RESULT.json';r=json.loads(ev.read_bytes());assert r['status']=='PASS_M439_HLS_RESOURCE_REPORT'
    guard=BASE/'runs/M439-record-load-schedule-guard-02/RESULT.json';assert json.loads(guard.read_bytes())['status']=='PASS_M439_ORIGINAL_MAC_SCHEDULE_RETAINED'
    out=ROOT/('tmp/m439_'+tag+'_01');assert not out.exists(),'Existing trace: collect only'
    support=ROOT/'tmp/m438_weight_wait_03'
    syn=ROOT/('tmp/m357_hls_project_02/hls/syn/verilog' if tag=='baseline_w4' else 'tmp/m439_hls_project_02/hls/syn/verilog')
    build='0x4D333537' if tag=='baseline_w4' else '0x4D343339'
    # Only hash-verified TB/VIP/model support, plus exact fresh synthesis design.
    support_p=BASE/'runs/M438-weight-wait-preparation-01/RESULT.json';support_rows=json.loads(support_p.read_bytes())['files']
    rows=[]
    for row in support_rows:
        p=ROOT/row['path'];rel=p.relative_to(support)
        if not rel.parts or rel.parts[0]!='verilog':continue
        wanted=len(rel.parts)>2 or p.name in ('glbl.v','fifo_para.vh','m89x_runtime_kernel.autotb.v')
        if wanted:
            assert sha(p)==row['sha256'],p
            atomic(out/rel,p.read_bytes(),immutable=True);rows.append(dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p)))
    for model in (support/'verilog/ip/xil_defaultlib').glob('*.vhd'):
        wrapper=model.name[:-7]+'.v';assert sha(syn/wrapper)==sha(support/'verilog'/wrapper),wrapper
    bindings=mac_bindings(syn)
    if tag!='baseline_w4':
        for row in r['rtl_inputs']:assert sha(ROOT/row['path'])==row['sha256']
    for p in syn.glob('*.v'):atomic(out/'verilog'/p.name,p.read_bytes(),immutable=True)
    atomic(out/'verilog/m439_monitor.sv',monitor(bindings).encode('utf-8'),immutable=True)
    if tag=='candidate_w2':
        f=json.loads(support_p.read_bytes())['fixture']
        for root in ('cdatafile','stream_size'):
            for p in (support/'tv'/root).iterdir():atomic(out/'tv'/root/p.name,p.read_bytes(),immutable=True)
        p=out/'tv/cdatafile'/f'{PREFIX}autotvout_ap_return.dat';s=p.read_text(encoding='utf-8');assert '0x4d333537' in s;atomic(p,s.replace('0x4d333537','0x4d343339').encode('utf-8'))
        atomic(out/'golden.bin',(support/'golden.bin').read_bytes(),immutable=True)
    else:
        d,golden,f=w4_fixture();data=out/'tv/cdatafile';ss=out/'tv/stream_size'
        for direction,port,payload,width in [('in','tx',d['packet'],16),('out','rx',golden,8)]:
            vals=[int.from_bytes(payload[i:i+width],'little') for i in range(0,len(payload),width)]
            for field in ('data','keep','strb','last'):
                v=vals if field=='data' else ([int(j==len(vals)-1) for j in range(len(vals))] if field=='last' else [(1<<width)-1]*len(vals))
                tv(data/(PREFIX+f'autotv{direction}_{port}_V_{field}_V.dat'),['0x'+format(x,'x') for x in v]);tv(ss/f'stream_size_{direction}_{port}_V_{field}_V.dat',[len(v)])
        for i,raw in enumerate(d['weights']):
            # Original VIP memory loader uses big-endian binary words.
            be=b''.join(raw[j:j+16][::-1] for j in range(0,len(raw),16))
            atomic(data/(PREFIX+f'autotvin_w{i}.dat'),struct.pack('>Q',len(raw)//16)+be+bytes.fromhex('5a5aa5a50f0ff0f0'),immutable=True)
        tv(data/(PREFIX+'autotvin_config_r.dat'),['0x'+format(d['config'],'x')]);tv(data/(PREFIX+'autotvout_ap_return.dat'),[build.lower()]);atomic(out/'golden.bin',golden,immutable=True)
    (out/'tv/rtldatafile').mkdir(parents=True)
    vip=[x for x in (support/'verilog/m438.prj').read_text(encoding='utf-8').splitlines() if x.startswith('vhdl ') or any('/'+d+'/' in x for d in ('svr','axivip','svtb','file_agent','m89x_runtime_kernel_subsystem'))]
    prj=vip+['sv xil_defaultlib "glbl.v"','sv xil_defaultlib "m89x_runtime_kernel.autotb.v"']+['sv xil_defaultlib "'+p.name+'"' for p in sorted(syn.glob('*.v'))]+['sv xil_defaultlib "m439_monitor.sv"']
    atomic(out/'verilog/m439.prj',('\n'.join(prj)+'\n').encode('utf-8'),immutable=True);atomic(out/'verilog/run.tcl',b'run all\nquit\n',immutable=True)
    result=dict(status='PREPARED_M439_NARROW_RTL',tag=tag,build_id=build,hls_sha256=sha(ev),schedule_guard_sha256=sha(guard),support_sha256=sha(support_p),unchanged_support=rows,
      fixture=f,MAC_bindings=bindings,expected=dict(mac_calls_per_shard=160,iterations_per_shard=2560,weight_beats_per_shard=360 if tag=='candidate_w2' else 680,output_words=512),
      modes=['Random','Zero'],seed=356,cycle_budget=500000,board=False,
      files=[dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p)) for p in sorted(out.rglob('*')) if p.is_file()])
    ev=BASE/f'runs/M439-{tag}-preparation-01/RESULT.json';atomic(ev,encoded(result),immutable=True)
    sync('latest_m439_'+tag+'_preparation',dict(status=result['status'],result=ev.relative_to(ROOT).as_posix(),sha256=sha(ev),build_id=build,board=False),
      f'## M439 {tag}窄RTL准备（2026-10-07）\n\nSHA {sha(ev)}；原数据/原参考、同seed356随机与零附加延迟，实际MAC层级由生成RTL唯一解析。全输出/ARLEN/覆盖地址/字数/RLAST/迭代计数门禁，500000周期预算；未模拟/上板。原W2 A直接复用M438不重跑，W4 A-B只本小片段，不全模型。')
    print('M439_RTL_PREPARED',tag,sha(ev))

if __name__=='__main__':main()
