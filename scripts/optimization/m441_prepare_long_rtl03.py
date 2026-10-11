"""Complete real long-chain RTL inputs and actual-hierarchy observer, no run."""
import json
import re
import struct
import sys
from m351_workflow import ROOT, BASE, atomic, encoded, sha, sync
from m438_prepare import PREFIX, tv, values
from m439_prepare_rtl import monitor as old_monitor
from m441_observer03 import instrument, instrument_latency, selftest


def bindings(syn, variant):
    top=(syn/'m89x_runtime_kernel.v').read_text(encoding='utf-8-sig')
    four=re.findall(r'm89x_runtime_kernel_m89x_four\s+(grp_m89x_four_fu_\d+)\s*\(',top)
    assert len(four)==1
    text=(syn/'m89x_runtime_kernel_m89x_four.v').read_text(encoding='utf-8-sig')
    parents=re.findall(r'(m89x_runtime_kernel_m89x_shard\w*)\s+(m89x_shard\w*_U0)\s*\(',text)
    assert len(parents)==4
    result=[]
    for i,(parent_module,parent_instance) in enumerate(parents):
        parent=f'`D.{four[0]}.{parent_instance}'
        s=(syn/(parent_module+'.v')).read_text(encoding='utf-8-sig')
        queue_parent=parent
        if variant=='B':
            consumers=re.findall(r'(m89x_runtime_kernel_m441_compute\w*)\s+(m441_compute\w*_U0)\s*\(',s)
            assert len(consumers)==1
            module,instance=consumers[0];parent+='.'+instance
            s=(syn/(module+'.v')).read_text(encoding='utf-8-sig')
        hits=[]
        for module,instance in re.findall(r'(m89x_runtime_kernel_\w+_Pipeline_\w+)\s+(\w+_fu_\d+)\s*\(',s):
            child=(syn/(module+'.v')).read_text(encoding='utf-8-sig')
            cmp=re.findall(r"assign (icmp_ln\w+_p2) = \(\(ap_sig_allocacmp_token_pair_\d+ == 5'd16\)",child)
            if cmp:
                assert len(cmp)==1 and 'ap_enable_reg_pp0_iter0' in child and 'ap_block_pp0_stage0_subdone' in child
                hits.append(dict(instance=instance,module=module,compare=cmp[0]))
        assert len(hits)==1,(parent,hits)
        result.append(dict(shard=i,parent=parent,queue_parent=queue_parent,**hits[0]))
    return result


def observer(bs, chain, base, variant):
    # Existing accepted-MAC/AXI observer; only queues and complete address
    # membership are added. Large AXI address counts use a bounded ring.
    s=old_monitor(bs).replace('M439','M441').replace('m439_monitor','m441_monitor')
    s=s.replace('remaining[4][1024]','remaining[4][512]')
    s=s.replace('cyc>500000','cyc>30000000')
    s=s.replace('tail[i]>=1024','tail[i]-head[i]>=512')
    s=s.replace('remaining[i][tail[i]]','remaining[i][tail[i]%512]').replace('remaining[i][head[i]]','remaining[i][head[i]%512]')
    address_print='   $display("M441_AR shard=%0d address=%0h len=%0d size=%0d burst=%0d",i,addresses[i],lens[i],sizes[i],bursts[i]);'
    assert s.count(address_print)==1
    cover='''   if(sizes[i]!=4||bursts[i]!=1||addresses[i][3:0]!=0)$fatal(1,"M441 bad address geometry");
   for(integer k=0;k<=lens[i];k=k+1)begin
    longint word_index;
    word_index=(addresses[i]>>4)+k;
    if(word_index>=524288||!allowed_word(word_index))$fatal(1,"M441 unexpected record address");
    if(seen[i][word_index])$fatal(1,"M441 duplicate record address");
    seen[i][word_index]=1;
   end'''
    s=s.replace(address_print,cover)
    header='integer cyc=0,i,words=0,lasts=0;'
    allow=[]
    expected_beats=0
    for d in chain['descriptors']:
        first=(int(d['encoded_u64'],16)&0xffffffff)-base
        count=d['record_bytes_per_shard']//16
        allow.append(f'(index>={first} && index<{first+count})')
        expected_beats+=count
    calls=chain['groups']*sum(d['rows_per_shard']//8 for d in chain['descriptors'])*4
    extra='''
bit [524287:0] seen[4];
longint queue_writes[4],queue_reads[4],queue_full_cycles[4];
longint R_during_accepted_MAC[4];
longint ar_histogram[4][65];
integer queue_high[4];
wire [3:0] qwrite,qread,qfull;
wire [6:0] qcount[4];
function automatic bit allowed_word(input longint index);
 allowed_word='''+' || '.join(allow)+''';
endfunction
initial for(integer j=0;j<4;j=j+1)begin
 seen[j]='0;queue_writes[j]=0;queue_reads[j]=0;queue_full_cycles[j]=0;queue_high[j]=0;R_during_accepted_MAC[j]=0;
 for(integer k=0;k<65;k=k+1)ar_histogram[j][k]=0;
end
'''
    for b in bs:
        i=b['shard'];q=b['queue_parent']+'.records_U'
        if variant=='B':
            extra+=f'''assign qwrite[{i}]={q}.if_write && {q}.if_write_ce && {q}.if_full_n;
assign qread[{i}]={q}.if_read && {q}.if_read_ce && {q}.if_empty_n;
assign qfull[{i}]=!{q}.if_full_n;
assign qcount[{i}]={q}.if_num_data_valid;
'''
        else: extra+=f"assign qwrite[{i}]=0;assign qread[{i}]=0;assign qfull[{i}]=0;assign qcount[{i}]=0;\n"
    s=s.replace(header,header+'\n'+extra)
    ar_anchor='   if(sizes[i]!=4||bursts[i]!=1||addresses[i][3:0]!=0)'
    ar_add='''   if(lens[i]>63||(addresses[i][11:0]+(lens[i]+1)*16)>4096)$fatal(1,"M441 burst length/boundary");
   ar_histogram[i][lens[i]+1]=ar_histogram[i][lens[i]+1]+1;
   if(sizes[i]!=4||bursts[i]!=1||addresses[i][3:0]!=0)'''
    assert s.count(ar_anchor)==1;s=s.replace(ar_anchor,ar_add)
    anchor=' for(i=0;i<4;i=i+1)begin\n  if(live[i])'
    update=''' for(i=0;i<4;i=i+1)begin
  if(qwrite[i])queue_writes[i]=queue_writes[i]+1;
  if(qread[i])queue_reads[i]=queue_reads[i]+1;
  if(qfull[i])queue_full_cycles[i]=queue_full_cycles[i]+1;
  if(rok[i]&&iter[i])R_during_accepted_MAC[i]=R_during_accepted_MAC[i]+1;
  if(qcount[i]>queue_high[i])queue_high[i]=qcount[i];
  if(qcount[i]>34||queue_reads[i]>queue_writes[i]||queue_writes[i]-queue_reads[i]>34)$fatal(1,"M441 queue bound");
  if(live[i])'''
    assert s.count(anchor)==1;s=s.replace(anchor,update)
    anchor=' if(`D.ap_done)begin'
    finish=f''' if(`D.ap_done)begin
  if(words!={chain['output_words64']}||lasts!=1)$fatal(1,"M441 full output count/TLAST");
  for(integer j=0;j<4;j=j+1)begin
   if($countones(seen[j])!={expected_beats}||rr[j]!={expected_beats}||tail[j]!=head[j]||badlast[j]||badresp[j])$fatal(1,"M441 incomplete full address/R proof");
   if(calls[j]!={calls}||iterations[j]!={calls*16})$fatal(1,"M441 changed full MAC work");
   $display("M441_QUEUE shard=%0d writes=%0d reads=%0d high=%0d full_cycles=%0d final=%0d covered=%0d R_accepted_MAC=%0d",j,queue_writes[j],queue_reads[j],queue_high[j],queue_full_cycles[j],qcount[j],$countones(seen[j]),R_during_accepted_MAC[j]);
   for(integer k=1;k<65;k=k+1)if(ar_histogram[j][k])$display("M441_ARLEN shard=%0d beats=%0d requests=%0d",j,k,ar_histogram[j][k]);
'''
    if variant=='B':
        finish+=f'''   if(queue_writes[j]!={expected_beats}||queue_reads[j]!={expected_beats}||qcount[j]!=0||queue_high[j]!=34||queue_full_cycles[j]==0||r_mac[j]==0||R_during_accepted_MAC[j]==0)$fatal(1,"M441 no bounded load/compute overlap proof");
'''
    finish+='  end\n'
    assert s.count(anchor)==1;s=s.replace(anchor,finish)
    s=instrument(s)
    return s,dict(mac_calls_per_shard=calls,iterations_per_shard=calls*16,weight_beats_per_shard=expected_beats,output_words=chain['output_words64'])


def main():
    variant, family=sys.argv[1:]
    assert variant in ('A','B') and family in ('gate_up','mlp_down','q')
    completed=BASE/'runs/M441-full-numeric-csim-01/RESULT.json'
    assert json.loads(completed.read_bytes())['status']=='PASS_M441_FULL_REAL_WEIGHT_CHAIN_CSIM'
    static=BASE/'runs/M441-actual-schedule-queue-guard-01/RESULT.json'
    assert json.loads(static.read_bytes())['status']=='PASS_M441_ACTUAL_MAC_AND_BOUNDED_QUEUE_STATIC_GUARD'
    board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    assert board['latest_m441_full_numeric_csim']['sha256']==sha(completed)
    assert all(sha(completed) in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    p=BASE/'runs/M441-full-numeric-preparation-01/RESULT.json';pr=json.loads(p.read_bytes())
    case=next(c for c in pr['cases'] if c['family']==family);raw=(ROOT/case['fixture_path']).read_bytes()
    assert sha(ROOT/case['fixture_path'])==case['fixture_sha256'] and raw[:8]==b'M441FUL1'
    config,dc,inp,outp,window=struct.unpack('<5I',raw[8:28]);cursor=28
    packet=raw[cursor:cursor+inp];cursor+=inp;weights=[]
    for i in range(4):weights.append(raw[cursor:cursor+window]);cursor+=window
    golden=raw[cursor:];assert len(golden)==outp
    chain=case['chain'];base=chain['staged_base_words']
    out=ROOT/f'tmp/m441_long_{variant}_{family}_03';assert not out.exists()
    support=ROOT/'tmp/m438_weight_wait_03'
    support_p=BASE/'runs/M438-weight-wait-preparation-01/RESULT.json'
    support_rows=json.loads(support_p.read_bytes())['files']
    syn=ROOT/('tmp/m357_hls_project_02/hls/syn/verilog' if variant=='A' else 'tmp/m441_hls_project_02/hls/syn/verilog')
    build='0x4D333537' if variant=='A' else '0x4D343431'
    unchanged=[]
    for row in support_rows:
        path=ROOT/row['path'];rel=path.relative_to(support)
        if rel.parts[0]=='verilog' and (len(rel.parts)>2 or path.name in ('glbl.v','fifo_para.vh','m89x_runtime_kernel.autotb.v')):
            assert sha(path)==row['sha256'];atomic(out/rel,path.read_bytes(),immutable=True)
            unchanged.append(dict(path=row['path'],sha256=row['sha256']))
    for model in (support/'verilog/ip/xil_defaultlib').glob('*.vhd'):
        wrapper=model.name[:-7]+'.v';assert sha(syn/wrapper)==sha(support/'verilog'/wrapper),wrapper
    bs=bindings(syn,variant)
    s,expected=observer(bs,chain,base,variant)
    for path in syn.glob('*.v'):atomic(out/'verilog'/path.name,path.read_bytes(),immutable=True)
    atomic(out/'verilog/m441_monitor.sv',s.encode('utf-8'),immutable=True)
    support_map={row['path']:row['sha256'] for row in support_rows}
    for i in range(4):
        path=support/'tv/cdatafile'/(PREFIX+f'autotvin_s{i}.dat')
        assert sha(path)==support_map[path.relative_to(ROOT).as_posix()] and values(path)==[0]
        atomic(out/'tv/cdatafile'/path.name,path.read_bytes(),immutable=True)
    data=out/'tv/cdatafile';ss=out/'tv/stream_size'
    for direction,port,payload,width in [('in','tx',packet,16),('out','rx',golden,8)]:
        vals=[int.from_bytes(payload[j:j+width],'little') for j in range(0,len(payload),width)]
        for field in ('data','keep','strb','last'):
            v=vals if field=='data' else ([int(j==len(vals)-1) for j in range(len(vals))] if field=='last' else [(1<<width)-1]*len(vals))
            tv(data/(PREFIX+f'autotv{direction}_{port}_V_{field}_V.dat'),['0x'+format(x,'x') for x in v])
            tv(ss/f'stream_size_{direction}_{port}_V_{field}_V.dat',[len(v)])
    for i,raw in enumerate(weights):
        be=b''.join(raw[j:j+16][::-1] for j in range(0,len(raw),16))
        atomic(data/(PREFIX+f'autotvin_w{i}.dat'),struct.pack('>Q',len(raw)//16)+be+bytes.fromhex('5a5aa5a50f0ff0f0'),immutable=True)
    tv(data/(PREFIX+'autotvin_config_r.dat'),[hex(config)]);tv(data/(PREFIX+'autotvout_ap_return.dat'),[build.lower()])
    atomic(out/'golden.bin',golden,immutable=True);(out/'tv/rtldatafile').mkdir(parents=True)
    consumed=set()
    for path in (out/'verilog').rglob('*'):
        if path.suffix in ('.v','.sv','.svh','.vh'):
            consumed.update(re.findall(r'"(\.\./tv/(?:cdatafile|stream_size)/[^"\r\n]+)"',path.read_text(encoding='utf-8-sig')))
    for rel in consumed:assert (out/'verilog'/rel).resolve().is_file(),rel
    assert selftest()==15
    latency_path=out/'verilog/m89x_runtime_kernel_subsystem/m89x_runtime_kernel_env.sv'
    original_latency_sha=sha(latency_path)
    atomic(latency_path,instrument_latency(latency_path.read_text(encoding='utf-8-sig')).encode('utf-8'))
    vip=[line for line in (support/'verilog/m438.prj').read_text(encoding='utf-8').splitlines() if line.startswith('vhdl ') or any('/'+d+'/' in line for d in ('svr','axivip','svtb','file_agent','m89x_runtime_kernel_subsystem'))]
    project=vip+['sv xil_defaultlib "glbl.v"','sv xil_defaultlib "m89x_runtime_kernel.autotb.v"']+['sv xil_defaultlib "'+path.name+'"' for path in sorted(syn.glob('*.v'))]+['sv xil_defaultlib "m441_monitor.sv"']
    atomic(out/'verilog/m441.prj',('\n'.join(project)+'\n').encode('utf-8'),immutable=True)
    atomic(out/'verilog/run.tcl',b'run all\nquit\n',immutable=True)
    r=dict(original_latency_model_sha256=original_latency_sha,observer_helper_sha256=sha(ROOT/'scripts/optimization/m441_observer03.py'), observer_fault_checks=15, status='PREPARED_M441_COMPLETE_LONG_CHAIN_RTL',variant=variant,family=family,build_id=build,
           full_numeric_sha256=sha(completed),static_guard_sha256=sha(static),fixture_sha256=case['fixture_sha256'],
           support_sha256=sha(support_p),unchanged_support=unchanged,chain=chain,bindings=bs,expected=expected,
           cycle_budget=80000000,modes=['Zero','Random'],seed=356,
           observation='Circular AXI queue512, exact allowed-record membership and duplicate rejection, full R count/RLAST, unchanged MAC work, full output and bounded FIFO34 fill/backpressure/drain and R during MAC.',
           files=[dict(path=path.relative_to(ROOT).as_posix(),sha256=sha(path)) for path in sorted(out.rglob('*')) if path.is_file()],
           ARLEN_histogram_recorded=True,observer_revision='03',generator_sha256=sha(ROOT/'scripts/optimization/m441_prepare_long_rtl03.py'),
           prior_observer_compile_only='Revision01 had no exported ARLEN histogram; no simulation was run. Preserve its frozen inputs and compile.',
           RTL_run=False,board=False,performance=False,promoted=False)
    ev=BASE/f'runs/M441-long-{variant}-{family}-RTL-preparation-03/RESULT.json';atomic(ev,encoded(r),immutable=True)
    sync('latest_m441_long_'+variant+'_'+family+'_RTL_preparation03',dict(status=r['status'],result=ev.relative_to(ROOT).as_posix(),sha256=sha(ev),build_id=build,board=False),
         f'## M441 {variant}/{family} 完整长链RTL准备（2026-10-07）\n\nSHA {sha(ev)}；原完整真实权重/输入/参考，实际层级绑定MAC与候选FIFO34，精确记录地址集合/环形在途队列/字数/TLAST及队列满背压排空、MAC读算重叠。固定Zero/seed356Random/80M周期，新增周期及Fatal末态快照/生成延迟统计，全局1M无进度检测；尚未compile/RTL或板端，非性能。下一步独立编译及裁决，不能从小W4外推。')
    print(r['status'],sha(ev),variant,family)


if __name__=='__main__': main()
