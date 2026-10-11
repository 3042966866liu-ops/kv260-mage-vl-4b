"""Prepare separately bounded stress inputs only; no simulator invocation."""
import json
import re
from m351_workflow import ROOT, BASE, HERE, atomic, encoded, sha, sync
from m441_observer03 import EXTRA, GUARD, instrument_latency

def transform_monitor(s):
    assert s.count('module m441_max_monitor;')==1
    s=s.replace('module m441_max_monitor;', 'module m441_max_monitor;'+EXTRA)
    assert s.count('cyc>3100000')==1
    s=s.replace('cyc>3100000','cyc>4000000')
    s=re.sub(r'(\$fatal\(1,[^;]+\);)',r'begin progress_snapshot(2);\1 end',s)
    anchor=' old_start=start;';assert s.count(anchor)==1
    s=s.replace(anchor,GUARD+'\n'+anchor)
    hb='if(cyc%10000==0)$display("M441MAX_HEARTBEAT cycle=%0d output=%0d",cyc,words);'
    assert s.count(hb)==1
    s=s.replace(hb,'if(cyc%10000==0)begin progress_snapshot(0);$display("M441MAX_HEARTBEAT cycle=%0d output=%0d",cyc,words);end')
    s=s.replace(' if(`D.ap_done)begin',' if(`D.ap_done)begin\n progress_snapshot(1);\n if(tail_hold_valid_cycles!=128||!tail_released)begin progress_snapshot(2);$fatal(1,"M441 boundary final TLAST hold unproven");end')
    tail=r'''
integer tail_hold_valid_cycles=0;
bit tail_armed=0,tail_released=0;
// Shared VIP ready, not a forced DUT datapath signal. Arm before last transfer.
always @(negedge `D.ap_clk)begin
 if(!tail_armed && words==327679)begin
  force apatb_m89x_runtime_kernel_top.svtb_top.svr_rx_if.ready=0;
  tail_armed=1;
 end else if(tail_armed && !tail_released && `D.rx_TVALID && `D.rx_TLAST)begin
  if(`D.rx_TREADY)begin progress_snapshot(2);$fatal(1,"M441 final hold ready not low");end
  tail_hold_valid_cycles=tail_hold_valid_cycles+1;
  if(tail_hold_valid_cycles==128)begin
   release apatb_m89x_runtime_kernel_top.svtb_top.svr_rx_if.ready;
   tail_released=1;
   $display("M441_BOUNDARY_LAST_HOLD valid_cycles=%0d accepted_before=%0d",tail_hold_valid_cycles,words);
  end
 end
end
'''
    assert s.count('endmodule')==1
    return s.replace('endmodule',tail+'\nendmodule')

def main():
    prep=BASE/'runs/M441-max-protocol-preparation-01/RESULT.json'
    p=json.loads(prep.read_bytes())
    assert sha(prep)=='9ccb91847207d4a002bc61c1581b94ad600f943b5483bb8d24c29205e8bc8e02'
    old=ROOT/'tmp/m441_max_protocol_01';out=ROOT/'tmp/m441_boundary_protocol_05'
    assert not out.exists()
    for f in p['files']:assert sha(ROOT/f['path'])==f['sha256']
    changed=[]
    for f in p['files']:
        source=ROOT/f['path'];rel=source.relative_to(old);raw=source.read_bytes()
        if source.name=='m441_max_monitor.sv':raw=transform_monitor(raw.decode('utf-8-sig')).encode('utf-8')
        elif source.name=='m89x_runtime_kernel_env.sv':
            s=raw.decode('utf-8-sig');assert s.count('256')==s.count('[0:256]')+s.count('256:=1')
            s=s.replace('256','8');raw=instrument_latency(s).encode('utf-8')
            assert s.count('std::randomize')==source.read_text(encoding='utf-8-sig').count('std::randomize')
        elif source.name=='max.tcl':
            s=raw.decode('utf-8-sig');assert s.count('$i <= 300')==1
            raw=s.replace('$i <= 300','$i <= 390').encode('utf-8')
        atomic(out/rel,raw,immutable=True)
        if sha(out/rel)!=f['sha256']:changed.append(rel.as_posix())
    assert changed==sorted(changed)
    (out/'tv/rtldatafile').mkdir(parents=True)
    r=dict(status='PREPARED_M441_SEPARATE_BOUNDED_BOUNDARY_INPUTS_ONLY',build_id=p['build_id'],
        original_preparation_sha256=sha(prep),expected=p['expected'],
        virtual_cycle_budget=4000000,tool_wall_budget_s=14400,seed=441,
        random_delay_range=[0,8],address_hold_cycles=10000,output_hold_cycles=100000,final_TLAST_valid_hold_cycles=128,
        unchanged_fixture_and_DUT=True,changed_files=changed,
        protocol_scope='10 full descriptors and original327680 outputs preserve FIFO8192 and recordFIFO34 occupancy; zero-scale oracle is protocol only.',
        checks_still_required=['Actual burst split at4KiB','Descriptor switching','All four shard counts/merge','FIFO8192 full and FIFO34 full/backpressure/drain','AR and output stalled payload stable','Final TLAST128valid hold/release','Complete bytes/Build/ap_done','Same compiled snapshot200cycle timeout rejection'],
        execution_prerequisites=['Saved full gate_up Zero A/B reused with same DUT SHA','Full mlp_down Zero A/B PASS and synchronized SHA','Actual new observer component and collector fault checks PASS'],
        readiness='CONTROL_AND_COLLECTOR_NOT_IMPLEMENTED; no compile or execution authorized by this preparation alone',
        files=[dict(path=q.relative_to(ROOT).as_posix(),sha256=sha(q)) for q in sorted(out.rglob('*')) if q.is_file()],
        original_random02_FAIL_preserved=True,original_random03_interruption_preserved=True,
        original_six_random_groups_completed=False,board=False,compiled=False,simulated=False,performance=False)
    result=BASE/'runs/M441-bounded-boundary-preparation-04/RESULT.json'
    atomic(result,encoded(r),immutable=True)
    sync('latest_m441_bounded_boundary_preparation04',dict(status=r['status'],sha256=sha(result),result=result.relative_to(ROOT).as_posix(),board=False),
        '## M441 独立有界边界输入准备04（2026-10-09）\n\nSHA '+sha(result)+'；保留10descriptor/327680输出/FIFO8192及34规模与DUT，随机范围0..8、AR10000/输出100000/最后TLAST128有效周期停顿；固定4M/4h。仅准备，实际observer组件及收集控制尚缺，0编译/仿真/板端；W4完整Zero及新增组件闭合后才可执行，不称原六组Random完成。')
    print(r['status'],sha(result),changed)

if __name__=='__main__':main()
