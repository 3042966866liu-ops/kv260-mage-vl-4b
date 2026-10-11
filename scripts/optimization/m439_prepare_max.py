"""Prepare one same-version maximum protocol case only after core timing PASS."""
import json, re
from m351_workflow import ROOT, BASE, HERE, atomic, encoded, sha, sync
from m439_prepare_rtl import mac_bindings, monitor

def checked(path, digest=None):
    r=json.loads(path.read_bytes())
    if digest: assert sha(path)==digest
    return r

def main():
    core=BASE/'runs/M439-record-load-core-OOC-closure-01/RESULT.json'
    c=checked(core);assert c['status']=='PASS_M439_SAME_CONSTRAINT_CORE_ROUTED_TIMING'
    b=checked(ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json')
    assert any(isinstance(v,dict) and v.get('sha256')==sha(core) for v in b.values())
    assert all(sha(core) in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    spec=BASE/'runs/M439-record-load-protocol-plan-01/RESULT.json'
    checked(spec,'14a5df661bce227e42d6b71862ddeaf3a2c7b68647d9a2db16689654c907a0dd')
    prior=BASE/'runs/M439-candidate_w4-preparation-02/RESULT.json'
    p=checked(prior)
    fixture=BASE/'runs/M357-max-fifo-preparation-01/RESULT.json'
    f=checked(fixture,'6d16e74640d763803a886bddd3fc85364f6dac51d49cc9fd3d4f9df92b9d16f1')
    source=ROOT/'tmp/m439_candidate_w4_02';oldfixture=ROOT/'tmp/m357_maxfifo_trace'
    out=ROOT/'tmp/m439_max_protocol_01';assert not out.exists(),'Existing attempt: collect only'
    bindings=mac_bindings(ROOT/'tmp/m439_hls_project_02/hls/syn/verilog')
    four={x['parent'].rsplit('.',1)[0] for x in bindings};assert len(four)==1
    parent=four.pop()
    fourfile=ROOT/'tmp/m439_hls_project_02/hls/syn/verilog/m89x_runtime_kernel_m89x_four.v'
    fourtext=fourfile.read_text(encoding='utf-8')
    fifos=['result_num_data_valid']+[f'result_{i}_num_data_valid' for i in (1,2,3)]
    assert all(re.search(r'\b'+name+r'\b',fourtext) for name in fifos)
    # Freeze every copied source before changing only testbench metadata/inputs.
    for row in p['files']:
        src=ROOT/row['path'];assert sha(src)==row['sha256'],src
        rel=src.relative_to(source)
        if rel.parts[0]=='verilog' and src.name not in ('m439_monitor.sv','run.tcl'):
            atomic(out/rel,src.read_bytes(),immutable=True)
    for row in f['files']:
        src=ROOT/row['path'];assert sha(src)==row['sha256'],src
        rel=src.relative_to(oldfixture)
        if rel.parts[0]=='verilog':continue
        raw=src.read_bytes()
        if src.name.endswith('autotvout_ap_return.dat'):
            assert b'0x4d333537' in raw;raw=raw.replace(b'0x4d333537',b'0x4d343339')
        atomic(out/rel,raw,immutable=True)
    (out/'tv/rtldatafile').mkdir(parents=True,exist_ok=True)
    s=monitor(bindings).replace('cyc>500000','cyc>3100000').replace('cyc%50000','cyc%10000')
    s=s.replace('reg [3:0] live=0,old_start=0;',
                'reg [3:0] live=0,old_start=0,old_shard_start=0;\nwire[3:0] shard_start;\nlongint descs[4],fifo_max[4]; longint held=0; wire[13:0] occupancy[4];')
    s=s.replace('active[i]=0;', 'descs[i]=0;fifo_max[i]=0;active[i]=0;')
    extra=''
    for i,bb in enumerate(bindings):
        extra+=f'assign shard_start[{i}]={bb["parent"]}.ap_start;\nassign occupancy[{i}]={parent}.{fifos[i]};\n'
    s=s.replace('always @(posedge `D.ap_clk)begin\n cyc=',extra+'always @(posedge `D.ap_clk)begin\n cyc=')
    anchor='  if(live[i])begin'
    assert s.count(anchor)==1
    s=s.replace(anchor,'  if(shard_start[i]&&!old_shard_start[i])descs[i]=descs[i]+1;\n  if(occupancy[i]>8192)$fatal(1,"M439 FIFO overflow");\n  if(occupancy[i]>fifo_max[i])fifo_max[i]=occupancy[i];\n'+anchor)
    s=s.replace(' old_start=start;', ' old_start=start;old_shard_start=shard_start;\n if(`D.rx_TVALID&&!`D.rx_TREADY)held=held+1;')
    s=s.replace(' if(`D.ap_done)begin', ' if(`D.ap_done)begin\n  $display("M439_MAX_HELD_VALID=%0d",held);\n  for(i=0;i<4;i=i+1)$display("M439_MAX_PROTOCOL shard=%0d descriptors=%0d FIFO_MAX=%0d",i,descs[i],fifo_max[i]);')
    atomic(out/'verilog/m439_monitor.sv',s.encode('utf-8'),immutable=True)
    watchdog=(HERE/'m357_rtl_watchdog.sv').read_text(encoding='utf-8').replace('m357','m439').replace('M357','M439')
    atomic(out/'verilog/m439_rtl_watchdog.sv',watchdog.encode('utf-8'),immutable=True)
    prj=out/'verilog/m439.prj';atomic(prj,prj.read_bytes()+b'\nsv xil_defaultlib "m439_rtl_watchdog.sv"\n')
    corepath=parent.replace('`D','/apatb_m89x_runtime_kernel_top/AESL_inst_m89x_runtime_kernel').replace('.','/')
    tcl=f'''set ready /apatb_m89x_runtime_kernel_top/svtb_top/svr_rx_if/ready
set ar /apatb_m89x_runtime_kernel_top/svtb_top/axi_w0_if/ARREADY
set core {corepath}
add_force $ready 0
add_force $ar 0
run 48us
if {{[get_value -radix unsigned /apatb_m89x_runtime_kernel_top/w0_ARREADY] != 0 || [get_value -radix unsigned /apatb_m89x_runtime_kernel_top/w0_ARVALID] != 1}} {{error "Actual pending AXI hold missing"}}
puts "M439_SHARED_VIP_WEIGHT_AR_HOLD_VERIFIED cycles=10000"
remove_forces $ar
for {{set i 1}} {{$i <= 9}} {{incr i}} {{run 48us; puts "M439_CHUNK_PROGRESS time=[current_time]"}}
if {{[get_value -radix unsigned /apatb_m89x_runtime_kernel_top/rx_TREADY] != 0 || [get_value -radix unsigned /apatb_m89x_runtime_kernel_top/rx_TVALID] != 1}} {{error "Actual held valid output missing"}}
set full 0
foreach name {{{' '.join(fifos)}}} {{
 set occupancy [get_value -radix unsigned $core/$name]
 puts "M439_FIFO_HOLD_SNAPSHOT name=$name occupancy=$occupancy"
 if {{$occupancy > 8192}} {{error "FIFO capacity overflow"}}
 if {{$occupancy == 8192}} {{incr full}}
}}
if {{$full < 1}} {{error "Maximum legal FIFO occupancy not reached before release"}}
puts "M439_SHARED_VIP_OUTPUT_HOLD_VERIFIED cycles=100000"
remove_forces $ready
for {{set i 1}} {{$i <= 300}} {{incr i}} {{
 run 48us
 puts "M439_CHUNK_PROGRESS time=[current_time] words=[get_value -radix unsigned /m439_monitor/words]"
 if {{[get_value -radix unsigned /m439_monitor/words] == 327680 && [get_value -radix unsigned /m439_monitor/lasts] == 1}} {{break}}
}}
if {{[get_value -radix unsigned /m439_monitor/words] != 327680}} {{error "Bounded maximum cycle budget exceeded"}}
run 480ns
quit
'''
    atomic(out/'verilog/max.tcl',tcl.encode('utf-8'),immutable=True)
    atomic(out/'verilog/timeout.tcl',b'run all\nquit\n',immutable=True)
    consumed=set()
    for path in (out/'verilog').rglob('*'):
        if path.suffix in ('.v','.sv','.svh','.vh'):
            consumed.update(re.findall(r'"(\.\./tv/(?:cdatafile|stream_size)/[^"\r\n]+)"',path.read_text(encoding='utf-8-sig')))
    assert consumed
    for rel in consumed:assert (out/'verilog'/rel).resolve().is_file(),rel
    r=dict(status='PREPARED_M439_MAXIMUM_PROTOCOL_NOT_EXECUTED',build_id='0x4D343339',core_sha256=sha(core),protocol_spec_sha256=sha(spec),
           support_sha256=sha(prior),fixture_sha256=sha(fixture),fixture=f,MAC_bindings=bindings,
           expected=dict(descriptors_per_shard=10,MAC_calls_per_shard=2560,iterations_per_shard=40960,weight_words_per_shard=10880,output_words=327680,output_bytes=2621440),
           cycle_budget=3100000,wall_budget_s=1800,compile_wall_budget_s=600,timeout_wall_budget_s=120,
           runner_sha256=sha(HERE/'m439_run_protocol.py'),collector_sha256=sha(HERE/'m439_collect_protocol.py'),
           actual_VIP_filename_closure=len(consumed),debug_metadata_required=True,
           files=[dict(path=x.relative_to(ROOT).as_posix(),sha256=sha(x)) for x in sorted(out.rglob('*')) if x.is_file()],board=False,executed=False)
    ev=BASE/'runs/M439-max-protocol-preparation-01/RESULT.json';atomic(ev,encoded(r),immutable=True)
    sync('latest_m439_max_protocol_preparation',dict(status=r['status'],result=ev.relative_to(ROOT).as_posix(),sha256=sha(ev),build_id=r['build_id'],board=False),
         '## M439 最大协议准备（2026-10-07）\n\nSHA '+sha(ev)+'；核心同约束PASS后才准备，原最大10descriptor/8192FIFO夹具、实际VIP文件闭包、动态层级、debug元数据及独立200周期超时负例，0执行/板端。不更改DUT或加入下一条预取。')
    print(r['status'],sha(ev))

if __name__=='__main__':main()
