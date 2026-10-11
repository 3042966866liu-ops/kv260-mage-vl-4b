"""Freeze new M443 DUT with proven actual VIP and independent full inputs."""
import ast
import json
from pathlib import Path
import re
from m441_host_io08 import atomic
from m351_workflow import ROOT,BASE,HERE,encoded,sha,sync
from m441_sim_coverage19 import write_full_fixture,write_max_W2,pressure_tcl

OUT=ROOT/'tmp/m443_sim_coverage_03'
RUN=BASE/'runs/M443-W2-W4-pair-pipeline-RTL-03'
PREP=RUN/'PREPARATION.json'
OLD=ROOT/'tmp/m441_sim_coverage_21/W2_max'
SYN=ROOT/'tmp/m443_hls_project_03/hls/syn/verilog'

def evidence(path):
    return dict(path=path.relative_to(ROOT).as_posix(),sha256=sha(path),bytes=path.stat().st_size)

def main():
    numeric=BASE/'runs/M443-full-numeric-csim-03/RESULT.json'
    n=json.loads(numeric.read_bytes());assert n['status']=='PASS_M443_FULL_REAL_WEIGHT_CHAIN_CSIM03' and all(n['checks'].values())
    assert all(sha(numeric) in (ROOT/name).read_text(encoding='utf-8-sig') for name in ('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'))
    assert not OUT.exists() and not PREP.exists()
    oldprep=BASE/'runs/M441-W2-W4-simulation-coverage-21/PREPARATION.json'
    op=json.loads(oldprep.read_bytes());original=next(c for c in op['cases'] if c['name']=='W2_max')
    oldsyn=ROOT/'tmp/m441_hls_project_02/hls/syn/verilog'
    oldnames={p.name for p in oldsyn.glob('*.v')}
    newfiles=sorted(SYN.glob('*.v'));assert newfiles
    # Retained vendor floating point IP models must match the exact new wrapper.
    math=[]
    for p in newfiles:
        if any(x in p.name for x in ('_fadd_','_fmul_','_hptosp_','_sitofp_','_sptohp_','_uitofp_')):
            assert sha(p)==sha(oldsyn/p.name),p.name
            math.append(evidence(p))
    assert len(math)==6
    monitor=(OLD/'verilog/m441_max_monitor.sv').read_text(encoding='utf-8-sig')
    monitor=monitor.replace('m441_compute','m443_compute').replace('VITIS_LOOP_106_7_fu_590','VITIS_LOOP_114_7_fu_3179').replace('icmp_ln106_fu_2557','icmp_ln114_fu_3771').replace('expected_calls*16','expected_calls*64')
    assert 'm441_compute' not in monitor and 'expected_calls*16' not in monitor
    # Check the actual new hierarchy and iteration guard before compilation.
    for suffix in ('','_1','_2','_3'):
        compute=(SYN/f'm89x_runtime_kernel_m443_compute{suffix}.v').read_text(encoding='utf-8-sig')
        pipe=(SYN/f'm89x_runtime_kernel_m443_compute{suffix}_Pipeline_VITIS_LOOP_114_7.v').read_text(encoding='utf-8-sig')
        assert f'grp_m443_compute{suffix}_Pipeline_VITIS_LOOP_114_7_fu_3179' in compute
        assert all(x in pipe for x in ('icmp_ln114_fu_3771_p2','ap_enable_reg_pp0_iter0','ap_block_pp0_stage0_subdone'))
    anchor='always @(posedge `D.ap_clk)begin\n cyc=cyc+1;'
    assert monitor.count(anchor)==1
    observer='''longint pipeline_completed[4],pipeline_work[4],pipeline_gap[4];
bit pipeline_inside[4];
initial for(integer j=0;j<4;j=j+1)begin pipeline_completed[j]=0;pipeline_work[j]=0;pipeline_gap[j]=0;pipeline_inside[j]=0;end
always @(posedge `D.ap_clk)begin
 for(integer j=0;j<4;j=j+1)begin
  if(start[j]&&!old_start[j])begin
   if(pipeline_inside[j])$fatal(1,"M443 reentered incomplete 64-work pipeline");
   pipeline_work[j]=0;
  end
  if(iter[j])begin
   pipeline_inside[j]=1;pipeline_work[j]=pipeline_work[j]+1;
   if(pipeline_work[j]==64)begin pipeline_inside[j]=0;pipeline_completed[j]=pipeline_completed[j]+1;end
   else if(pipeline_work[j]>64)$fatal(1,"M443 more than 64 work inputs");
  end else if(pipeline_inside[j])begin pipeline_gap[j]=pipeline_gap[j]+1;$fatal(1,"M443 gap inside four-pair continuous input");end
 end
end
'''
    # Keep shared counters in a single always block to avoid simulator ordering races.
    begin=observer.index('always @(posedge `D.ap_clk)begin\n')
    declarations=observer[:begin]
    statements=observer[begin+len('always @(posedge `D.ap_clk)begin\n'):].rsplit('end\n',1)[0]
    monitor=(OLD/'verilog/m441_max_monitor.sv').read_text(encoding='utf-8-sig').replace('m441_compute','m443_compute').replace('VITIS_LOOP_106_7_fu_590','VITIS_LOOP_114_7_fu_3179').replace('icmp_ln106_fu_2557','icmp_ln114_fu_3771').replace('expected_calls*16','expected_calls*64')
    monitor=monitor.replace(anchor,declarations+'always @(posedge `D.ap_clk)begin\n'+statements+' cyc=cyc+1;')
    check='  $display("M441MAX_DONE'
    assert monitor.count(check)==1
    monitor=monitor.replace(check,'''  for(integer j=0;j<4;j=j+1)begin
   if(pipeline_completed[j]!=expected_calls||pipeline_gap[j]!=0||pipeline_inside[j])$fatal(1,"M443 continuous pipeline incomplete");
   $display("M443_PAIR_PIPELINE shard=%0d completed=%0d work=%0d gap=%0d",j,pipeline_completed[j],pipeline_work[j],pipeline_gap[j]);
  end
'''+check)
    full=json.loads((BASE/'runs/M441-full-numeric-preparation-01/RESULT.json').read_bytes())
    cases=[]
    for name in ('W2_max','W4_max','q','gate_up','mlp_down'):
        folder=OUT/name
        for row in original['files']:
            src=ROOT/row['path'];assert sha(src)==row['sha256']
            rel=src.relative_to(OLD)
            if rel.parts[0]=='verilog' and len(rel.parts)==2 and rel.name in oldnames:continue
            atomic(folder/rel,src.read_bytes(),immutable=True)
        # W4 max inputs are the original zero-scale protocol oracle, not numerical proof.
        if name=='W4_max':
            original4=json.loads((BASE/'runs/M441-bounded-boundary-preparation-07/RESULT.json').read_bytes())
            source4=ROOT/'tmp/m441_boundary_protocol_07'
            for row in original4['files']:
                src=ROOT/row['path'];rel=src.relative_to(source4)
                if rel.parts[0]=='tv' or rel.as_posix()=='golden.bin':atomic(folder/rel,src.read_bytes())
        for p in newfiles:atomic(folder/'verilog'/p.name,p.read_bytes(),immutable=True)
        atomic(folder/'verilog/m441_max_monitor.sv',monitor.encode('utf-8'))
        atomic(folder/'verilog/pressure.tcl',pressure_tcl().encode('utf-8'))
        prj=(OLD/'verilog/m441_max.prj').read_text(encoding='utf-8-sig')
        kept=[];inserted=False
        for line in prj.splitlines():
            paths=re.findall(r'"([^"]+)"',line)
            if paths and Path(paths[0]).name in oldnames:
                if not inserted:kept.extend('sv xil_defaultlib "'+p.name+'"' for p in newfiles);inserted=True
            else:kept.append(line)
        assert inserted
        atomic(folder/'verilog/m441_max.prj',('\n'.join(kept)+'\n').encode('utf-8'))
        (folder/'tv/rtldatafile').mkdir(parents=True)
        fixture=None
        if name=='W2_max':chain=write_max_W2(folder)
        elif name=='W4_max':
            chain=dict(bits=4,groups=1,descriptor_count=10,output_words64=327680,output_bytes=2621440,descriptors=[dict(rows_per_shard=512,encoded_u64='0x120000000000') for _ in range(10)],staged_base_words=0)
        else:
            case=next(c for c in full['cases'] if c['family']==name);chain=write_full_fixture(folder,case);fixture=case['fixture_sha256']
        apreturn=folder/'tv/cdatafile/c.m89x_runtime_kernel.autotvout_ap_return.dat'
        data=apreturn.read_bytes();assert b'0x4d343431' in data
        atomic(apreturn,data.replace(b'0x4d343431',b'0x4d343433'))
        reads=chain['groups']*sum(d['rows_per_shard']//8 for d in chain['descriptors'])*(1+4*chain['bits'])
        calls=chain['groups']*sum(d['rows_per_shard']//8 for d in chain['descriptors'])
        for path in (folder/'verilog').rglob('*'):
            if path.suffix in ('.v','.sv','.svh','.vh'):
                for rel in re.findall(r'"(\.\./tv/(?:cdatafile|stream_size)/[^"\r\n]+)"',path.read_text(encoding='utf-8-sig')):assert (folder/'verilog'/rel).resolve().is_file(),rel
        cases.append(dict(name=name,bits=chain['bits'],chain=chain,fixture_sha256=fixture,path=folder.relative_to(ROOT).as_posix(),cycle_budget=16000000 if name=='gate_up' else 8000000 if name=='mlp_down' else 4000000,wall_budget_s=28800 if name=='gate_up' else 21600 if name=='mlp_down' else 14400,expected=dict(output_words=chain['output_words64'],output_bytes=chain['output_bytes'],weight_beats_per_shard=reads,mac_calls_per_shard=calls,descriptors=chain['descriptor_count'],input_words=170 if name.endswith('_max') else chain['input_words128']),full_real_numerical=not name.endswith('_max'),maximum_pressure=name.endswith('_max'),files=[evidence(p) for p in sorted(folder.rglob('*')) if p.is_file()]))
    collector=(HERE/'m441_sim_evidence21.py').read_text(encoding='utf-8')
    collector=collector.replace('M441-W2-W4-simulation-coverage-21','M443-W2-W4-pair-pipeline-RTL-03').replace('tmp/m441_sim_coverage_21','tmp/m443_sim_coverage_03').replace('0x4D343431','0x4D343433').replace('16*e[','64*e[')
    collector=collector.replace("if p['maximum_pressure']:\n        splits=","if p['name']=='W2_max':\n        splits=")
    collector=collector.replace("    checks['reads']=", "    continuous=rows('M443_PAIR_PIPELINE')\n    checks['continuous_four_pair_inputs']=len(continuous)==4 and sorted(x['shard'] for x in continuous)==list(range(4)) and all(x['completed']==e['mac_calls_per_shard'] and x['work']==64 and x['gap']==0 for x in continuous)\n    checks['reads']=",1)
    # Explicit host fixtures preserve old saved evidence and only adapt observer schema.
    collector=collector.replace("    log+=''.join", "    log=log.replace('mac_calls=2560','mac_calls=640')\n    log+=''.join(f'M443_PAIR_PIPELINE shard={i} completed=640 work=64 gap=0\\n' for i in range(4))\n    log+=''.join")
    collector=collector.replace('mac_calls_per_shard=2560','mac_calls_per_shard=640').replace("    payload=b''.join(x.to_bytes(8,'little') for x in ports['rx_V_data_V']);golden=", "    ports['ap_return']=[0x4D343433]\n    payload=b''.join(x.to_bytes(8,'little') for x in ports['rx_V_data_V']);golden=")
    collector=collector.replace('PASS_M441_SUPPLEMENTAL','PASS_M443_PAIR_PIPELINE').replace('FAIL_M441_SUPPLEMENTAL','FAIL_M443_PAIR_PIPELINE').replace('latest_m441_simulation19','latest_m443_pair_pipeline_rtl03')
    collector=collector.replace('M441补充仿真19','M443新电路RTL03').replace('M441 W2同快照','M443 W2同快照').replace('Build0x4D343431','Build0x4D343433')
    collector=collector.replace('synthetic accepted-overlap marker only for parser testing','synthetic schema-only overlap and 64-work markers/Build for parser testing; NOT M443 RTL')
    collector=collector.replace("('missing_overlap','M441C19_OVERLAP shard=3','BROKEN_OVERLAP shard=3'),", "('missing_overlap','M441C19_OVERLAP shard=3','BROKEN_OVERLAP shard=3'),('continuous_gap','gap=0','gap=1'),('missing_continuous','M443_PAIR_PIPELINE shard=3','BROKEN_PAIR shard=3'),('incomplete_work','work=64','work=63'),")
    # The schema-only fixture lacks a name; maximum=False must not require one.
    collector=collector.replace("if p['name']=='W2_max':","if p.get('name')=='W2_max':")
    atomic(HERE/'m443_sim_evidence03.py',collector.encode('utf-8'),immutable=True)
    controller=(HERE/'m441_sim_control21.py').read_text(encoding='utf-8').replace('m441_sim_evidence21','m443_sim_evidence03').replace('M441-W2-W4-simulation-coverage-21','M443-W2-W4-pair-pipeline-RTL-03').replace('tmp/m441_sim_coverage_21','tmp/m443_sim_coverage_03').replace('m441_coverage21','m443_coverage03').replace('CONTROL_POLICY21.json','CONTROL_POLICY03.json')
    controller=controller.replace('PASS_M441_SUPPLEMENTAL','PASS_M443_PAIR_PIPELINE').replace('FAIL_M441_SUPPLEMENTAL','FAIL_M443_PAIR_PIPELINE').replace('STOP_M441_SUPPLEMENTAL','STOP_M443_PAIR_PIPELINE').replace('latest_m441_simulation19','latest_m443_pair_pipeline_rtl03').replace('M441补充仿真19','M443新电路RTL03').replace('M441 W2/W4缺口仿真','M443 W2/W4新电路仿真')
    controller=controller.replace('冻结同原DUT/实际VIP，新参数化观察器只覆盖缺口，不重综合/布线。','新M443实际综合DUT/原实际VIP，新层级连续64输入观察器；独立编译，尚未整壳布线。').replace('四新隔离缺口及W2timeout全部按原字节核对PASS。','新M443六项隔离RTL及W2timeout全部按原字节核对PASS。')
    atomic(HERE/'m443_sim_control03.py',controller.encode('utf-8'),immutable=True)
    for file in ('m443_sim_control03.py','m443_sim_evidence03.py'):ast.parse((HERE/file).read_bytes(),feature_version=(3,10))
    r=dict(status='PREPARED_M443_NEW_DUT_W2_W4_BOUNDED_RTL03',build_id='0x4D343433',numeric_sha256=sha(numeric),new_DUT_RTL=[evidence(p) for p in newfiles],unchanged_vendor_math_wrappers=math,original_scaffold_sha256=sha(oldprep),seed=441,random_delay_range=[0,8],AR_hold_at_least_cycles=10000,output_hold_at_least_cycles=100000,final_TLAST_hold_valid_cycles=128,cases=cases,order=['W2_max','timeout','W4_max','q','gate_up','mlp_down'],global_wall_budget_s=24*3600,compile_wall_budget_s=3600,controller=evidence(HERE/'m443_sim_control03.py'),collector=evidence(HERE/'m443_sim_evidence03.py'),generator=evidence(Path(__file__)),board=False,performance=False)
    atomic(PREP,encoded(r),immutable=True)
    policy=RUN/'CONTROL_POLICY03.json'
    atomic(policy,encoded(dict(preparation_sha256=sha(PREP),files=[r['controller'],r['collector'],r['generator']])),immutable=True)
    sync('latest_m443_pair_pipeline_rtl_preparation03',dict(status=r['status'],result=PREP.relative_to(ROOT).as_posix(),sha256=sha(PREP),board=False),f'## M443新DUT有界RTL冻结03（2026-10-10）\n\nSHA {sha(PREP)}；新实际RTL/原真实VIP/新层级观察器，W2及W4最大327680字零scale仅协议；完整Q/gate_up/down原参考，四端口seed441有界0..8、FIFO8192/34/4KiB/尾TLAST128有效拍/Build/done/200周期timeout原判据及每次64输入无空档新判据。独立24h全局/有限本级，不kill/不重跑旧PASS。下一步支持拒绝检查及一次新编译/仿真，非板端/收益。')
    print(r['status'],sha(PREP),flush=True)

if __name__=='__main__':main()
