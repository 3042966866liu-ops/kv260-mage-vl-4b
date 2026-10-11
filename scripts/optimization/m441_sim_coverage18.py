"""Frozen M441 W2/W4 simulation gap audit and isolated supplemental inputs.

No synthesis, implementation, UART, board, model or production entry points.
"""
import collections
import hashlib
import json
import re
import shutil
import struct
from pathlib import Path
from m351_workflow import ROOT, BASE, HERE, encoded, sha, sync
from m441_host_io08 import atomic
from m438_prepare import PREFIX, tv, values

OUT = ROOT / 'tmp/m441_sim_coverage_18'
RUN = BASE / 'runs/M441-W2-W4-simulation-coverage-18'
PREP = RUN / 'PREPARATION.json'
SUPPORT = ROOT / 'tmp/m441_boundary_protocol_07'


def evidence(path):
    return dict(path=path.relative_to(ROOT).as_posix(), sha256=sha(path), bytes=path.stat().st_size)


def audit():
    docs = {}
    for name in ('AGENTS.md', 'CURRENT_STATE.md', 'docsMILESTONES.md', 'DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md', 'deployment/mage_vl4b/BOARD_GATE_RESULT.json'):
        p = ROOT / name
        text = p.read_text(encoding='utf-8-sig')
        docs[name] = dict(**evidence(p), lines=len(text.splitlines()))
    board = json.loads((ROOT / 'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    keys = ['latest_m441_record_pipeline_csim', 'latest_m441_full_numeric_csim',
            'latest_m441_actual_schedule_queue_guard', 'latest_m441_long_B_gate_up_zero02',
            'latest_m441_long_B_mlp_down_zero05', 'latest_m441_boundary07_max', 'latest_m441_boundary07_timeout']
    refs = []
    for key in keys:
        row = board[key]; p = ROOT / row['result']; r = json.loads(p.read_bytes())
        assert sha(p) == row['sha256'] and r['status'].startswith('PASS_')
        assert all(sha(p) in (ROOT / n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md', 'docsMILESTONES.md'))
        # Recheck every stored raw artifact, not just the aggregate PASS label.
        for item in r.get('evidence', []):
            assert sha(ROOT / item['path']) == item['sha256'], item['path']
        refs.append(dict(key=key, **evidence(p), status=r['status']))
    source = ROOT / 'tmp/m441_record_pipeline_02/hls/mage_prefill_m89x_runtime/mage_prefill_m89x_runtime.cpp'
    assert sha(source) == 'de023abc5b849a56048d5e71bcefc67be1564fe150174607fdc89792905dbe6a'
    s = source.read_text(encoding='utf-8-sig')
    assert 'const unsigned words = 1 + 4 * bits;' in s
    assert 'records.write(memory[base + i]);' in s and 'record[i] = records.read();' in s
    assert '#pragma HLS STREAM variable=records depth=34' in s
    assert 'm441_load_records(memory, records, groups, rows, bits);' in s
    assert 'm441_compute(records, x, as, out, groups, rows, bits);' in s
    # Frozen HLS source/header closure and actual generated RTL both matter.
    prep = BASE / 'runs/M441-record-pipeline-preparation-02/RESULT.json'
    p = json.loads(prep.read_bytes())
    for row in p['files']:
        assert sha(ROOT / row['path']) == row['sha256']
    syn = ROOT / 'tmp/m441_hls_project_02/hls/syn/verilog'
    boundary = json.loads((BASE / 'runs/M441-bounded-boundary-preparation-07/RESULT.json').read_bytes())
    for row in boundary['files']:
        assert sha(ROOT / row['path']) == row['sha256']
    rtl = []
    for path in syn.glob('*.v'):
        assert sha(path) == sha(SUPPORT / 'verilog' / path.name), path.name
        rtl.append(evidence(path))
    full = json.loads((BASE / 'runs/M441-full-numeric-preparation-01/RESULT.json').read_bytes())
    cases = []
    for c in full['cases']:
        assert sha(ROOT / c['fixture_path']) == c['fixture_sha256']
        cases.append(dict(family=c['family'], bits=c['chain']['bits'], groups=c['chain']['groups'],
                          descriptors=c['chain']['descriptor_count'], output_words=c['chain']['output_words64'],
                          fixture_sha256=c['fixture_sha256']))
    r = dict(status='AUDITED_M441_W2_W4_SIMULATION_GAPS', build_id='0x4D343431',
             recovery_read=docs, evidence=refs, source=evidence(source), frozen_source_preparation=evidence(prep), actual_RTL=rtl,
             W2_uses_new_load_FIFO_compute=True, W2_record_words128=9, W4_record_words128=17,
             FIFO_words128=34, continuous_scope='Within each record only; block/group record addresses preserve original layout.',
             complete_CSim_cases=cases,
             existing_W2_complete_CSim=True, existing_W2_complete_RTL=False, existing_W2_max_pressure_RTL=False,
             existing_W4_full_real_Zero_RTL=['gate_up', 'mlp_down'], existing_W4_max_pressure_zero_scale=True,
             gaps=['W2 Q full real numerical RTL under bounded delay and end/backpressure',
                   'W2 maximum 10-descriptor/FIFO8192/FIFO34/4KiB/final-TLAST pressure plus timeout',
                   'W4 gate_up full real numerical RTL under bounded delay/backpressure',
                   'W4 mlp_down full real numerical RTL under bounded delay/backpressure'],
             estimate_hours=[9, 13], estimate_basis=dict(W4_gate_up_prior_wall='5h16m03s', W4_down_prior_wall='2h30m08s',
                                                       max_pressure_prior_wall_s=715.578, compile_prior_wall_s=49.031),
             original_Random02_FAIL_preserved=True, original_Random03_interruption_preserved=True,
             original_six_Random_suite_not_resumed=True, board=False, production_changed=False)
    ev = RUN / 'AUDIT.json'; atomic(ev, encoded(r), immutable=True)
    report = '''# M441 W2/W4 仿真覆盖审计（2026-10-10）

W2 与 W4 都经 m441_load_records → 每 shard 34×128bit FIFO → m441_compute。
bits=2 时一条记录9字，bits=4 时17字；连续读取是记录内部，跨记录按原 block/group 地址布局。
冻结源 SHA de023abc5b849a56048d5e71bcefc67be1564fe150174607fdc89792905dbe6a，实际综合 RTL 与通过压力07的 DUT 逐文件同 SHA。

|模式|已有完整数值|已有 RTL 结束协议/有界压力|待补|
|---|---|---|---|
|W2 Q G40/D2|M441完整CSim，65,536输出字|未找到M441自身完整数值RTL及W2最大压力|完整真实Q有界背压RTL；W2最大协议及200周期timeout|
|W4 gate_up G40/D10|完整CSim和完整Zero RTL，311,296输出字|最大G1/D10零scale压力已PASS|真实非零完整链有界背压RTL|
|W4 down G152/D2|完整CSim和完整Zero RTL，40,960输出字|最大G1/D10零scale压力已PASS|真实非零完整链有界背压RTL|

原压力07完整327,680输出/FIFO8192和34满背压排空/四端口4KiB拆分/尾TLAST128有效拍停顿/Build/ap_done及独立timeout已闭合，但bits=4且零scale，仅协议证据。
原Random02 FAIL和03中断保留，不恢复旧六组Random。本轮只补新固定0..8拍延迟、固定种子441的四个缺口，不比较性能、不重复综合布线或访问板端。

预计9–13小时：参考原W4 gate_up 5h16m、down 2h30m、最大压力715.6秒；W2完整Q MAC工作约gate_up的21%。实际耗时依仿真器，固定周期和墙钟预算不因结果临时放宽。
每项保存全部输出、KEEP/STRB/TLAST、Build/ap_done、四端口AR/R地址计数、FIFO满/背压/排空、停顿payload稳定、真实读算重叠；数值夹具复用已SHA核对的完整真实权重及全参考。CSim的无界stream不当成FIFO证明。
'''
    atomic(RUN / 'AUDIT.md', report.encode('utf-8'), immutable=True)
    sync('latest_m441_simulation_coverage_audit18', dict(status=r['status'], result=ev.relative_to(ROOT).as_posix(), sha256=sha(ev), board=False),
         '## M441 W2/W4仿真覆盖审计18（2026-10-10）\n\nSHA '+sha(ev)+'；冻结源码/实际RTL逐SHA证明W2也走9字连续record→FIFO34→原MAC，W4为17字。W2完整CSim已过但完整RTL/最大压力缺证；W4完整Zero数值及零scale最大压力已过，真实完整链有界背压数值待补。用户授权补齐四缺口，预计9–13h；原PASS/FAIL不改，0板端/生产/重新综合布线。详见同目录AUDIT.md。')
    return r


def monitor():
    s = (SUPPORT / 'verilog/m441_max_monitor.sv').read_text(encoding='utf-8-sig')
    decl = '''integer expected_words,expected_reads,expected_calls,expected_descs,cycle_budget;
initial begin
 if(!$value$plusargs("WORDS=%d",expected_words)||!$value$plusargs("READS=%d",expected_reads)||
    !$value$plusargs("CALLS=%d",expected_calls)||!$value$plusargs("DESCS=%d",expected_descs)||
    !$value$plusargs("CYCLES=%d",cycle_budget))$fatal(1,"Missing frozen case contract");
end
longint accepted_overlap[4];
initial for(integer j=0;j<4;j=j+1)accepted_overlap[j]=0;
'''
    s = s.replace('bit tail_block=0;', 'bit tail_block=0;\n'+decl)
    for a,b in [('cyc>4000000','cyc>cycle_budget'), ('words!=327680','words!=expected_words'),
                ('words==327679','words==expected_words-1'), ('descs[j]!=10','descs[j]!=expected_descs'),
                ('calls[j]!=2560','calls[j]!=expected_calls'), ('iterations[j]!=40960','iterations[j]!=expected_calls*16'),
                ('rr[j]!=10880','rr[j]!=expected_reads'), ('queue_writes[j]!=10880','queue_writes[j]!=expected_reads'),
                ('queue_reads[j]!=10880','queue_reads[j]!=expected_reads')]:
        assert a in s, a; s=s.replace(a,b)
    s=s.replace('  if(qwrite[i])', '  if(rok[i]&&iter[i])accepted_overlap[i]=accepted_overlap[i]+1;\n  if(qwrite[i])')
    anchor='  $display("M441MAX_DONE'
    assert s.count(anchor)==1
    s=s.replace(anchor, '''  for(integer j=0;j<4;j=j+1)begin
   if(accepted_overlap[j]==0)$fatal(1,"No accepted MAC/read overlap");
   $display("M441C18_OVERLAP shard=%0d accepted=%0d",j,accepted_overlap[j]);
  end
'''+anchor)
    assert 'force ' not in s and 'release ' not in s
    return s


def pressure_tcl():
    # Reuse the already proven actual VIP initial holds. Tail uses the dual
    # handshake interposer, never SV force/release on a receiver ready variable.
    return '''set ready /apatb_m89x_runtime_kernel_top/svtb_top/svr_rx_if/ready
set ar /apatb_m89x_runtime_kernel_top/svtb_top/axi_w0_if/ARREADY
set dut /apatb_m89x_runtime_kernel_top
add_force $ready 0
add_force $ar 0
for {set i 0} {$i < 100} {incr i} {
 run 4.8us
 if {[get_value -radix unsigned $dut/w0_ARVALID] == 1} {break}
}
if {[get_value -radix unsigned $dut/w0_ARVALID] != 1} {error "No actual pending AR"}
run 48us
if {[get_value -radix unsigned $dut/w0_ARREADY] != 0} {error "AR hold failed"}
puts "M441MAX_SHARED_VIP_WEIGHT_AR_HOLD_VERIFIED cycles=10000"
remove_forces $ar
for {set i 0} {$i < 200} {incr i} {
 run 48us
 if {[get_value -radix unsigned $dut/rx_TVALID] == 1} {break}
}
if {[get_value -radix unsigned $dut/rx_TVALID] != 1 || [get_value -radix unsigned $dut/rx_TREADY] != 0} {error "No actual held RX valid"}
run 480us
puts "M441MAX_SHARED_VIP_OUTPUT_HOLD_VERIFIED cycles=100000"
remove_forces $ready
run all
quit
'''


def write_full_fixture(out, case):
    raw=(ROOT/case['fixture_path']).read_bytes()
    assert sha(ROOT/case['fixture_path'])==case['fixture_sha256'] and raw[:8]==b'M441FUL1'
    config,dc,inp,outp,window=struct.unpack('<5I',raw[8:28]);pos=28
    packet=raw[pos:pos+inp];pos+=inp;weights=[]
    for i in range(4):weights.append(raw[pos:pos+window]);pos+=window
    golden=raw[pos:];assert len(golden)==outp
    data=out/'tv/cdatafile';ss=out/'tv/stream_size'
    for direction,port,payload,width in [('in','tx',packet,16),('out','rx',golden,8)]:
        vals=[int.from_bytes(payload[j:j+width],'little') for j in range(0,len(payload),width)]
        for field in ('data','keep','strb','last'):
            vs=vals if field=='data' else ([int(j==len(vals)-1) for j in range(len(vals))] if field=='last' else [(1<<width)-1]*len(vals))
            tv(data/(PREFIX+f'autotv{direction}_{port}_V_{field}_V.dat'),[hex(x) for x in vs])
            tv(ss/f'stream_size_{direction}_{port}_V_{field}_V.dat',[len(vs)])
    for i,w in enumerate(weights):
        be=b''.join(w[j:j+16][::-1] for j in range(0,len(w),16))
        atomic(data/(PREFIX+f'autotvin_w{i}.dat'),struct.pack('>Q',len(w)//16)+be+bytes.fromhex('5a5aa5a50f0ff0f0'),immutable=True)
    tv(data/(PREFIX+'autotvin_config_r.dat'),[hex(config)])
    atomic(out/'golden.bin',golden,immutable=True)
    return case['chain']


def write_max_W2(out):
    data=out/'tv/cdatafile'
    p=data/(PREFIX+'autotvin_tx_V_data_V.dat');packet=values(p)
    assert len(packet)==170 and packet[:10]==[0x120000000000]*10
    packet[:10]=[0xa0000000000]*10  # rows512, bits2, offset0
    tv(p,[hex(x) for x in packet])
    tv(data/(PREFIX+'autotvin_config_r.dat'),['0x000a0201'])
    for i in range(4):
        p=data/(PREFIX+f'autotvin_w{i}.dat');raw=p.read_bytes()
        count=struct.unpack('>Q',raw[:8])[0];assert count==1088
        rows=[]
        for block in range(64):
            record=raw[8+block*17*16:8+(block+1)*17*16]
            assert record[:16]==bytes(16), 'Protocol zero weight-scale oracle required'
            rows.append(record[:9*16])
        new=b''.join(rows);assert len(new)==576*16
        atomic(p,struct.pack('>Q',576)+new+raw[-8:])
    assert (out/'golden.bin').read_bytes()==bytes(2621440)
    return dict(bits=2,groups=1,descriptor_count=10,output_words64=327680,output_bytes=2621440,
                descriptors=[dict(rows_per_shard=512,encoded_u64='0x00000a0000000000') for _ in range(10)],staged_base_words=0)


def prepare():
    assert not OUT.exists() and not PREP.exists(), 'Existing preparation: collect only'
    audit_result=audit()
    original=json.loads((BASE/'runs/M441-bounded-boundary-preparation-07/RESULT.json').read_bytes())
    full=json.loads((BASE/'runs/M441-full-numeric-preparation-01/RESULT.json').read_bytes())
    cases=[]
    for name in ('W2_max','q','gate_up','mlp_down'):
        out=OUT/name
        for row in original['files']:
            src=ROOT/row['path'];rel=src.relative_to(SUPPORT)
            assert sha(src)==row['sha256']
            atomic(out/rel,src.read_bytes(),immutable=True)
        atomic(out/'verilog/m441_max_monitor.sv',monitor().encode('utf-8'))
        atomic(out/'verilog/pressure.tcl',pressure_tcl().encode('utf-8'),immutable=True)
        (out/'tv/rtldatafile').mkdir(parents=True)
        if name=='W2_max':
            chain=write_max_W2(out);fixture=None;cycle_budget=4000000;wall_s=14400
        else:
            case=next(c for c in full['cases'] if c['family']==name)
            chain=write_full_fixture(out,case);fixture=case['fixture_sha256']
            cycle_budget={'q':4000000,'gate_up':16000000,'mlp_down':8000000}[name]
            wall_s={'q':14400,'gate_up':28800,'mlp_down':21600}[name]
        reads=chain['groups']*sum(d['rows_per_shard']//8 for d in chain['descriptors'])*(1+4*chain['bits'])
        calls=chain['groups']*sum(d['rows_per_shard']//8 for d in chain['descriptors'])*4
        for path in (out/'verilog').rglob('*'):
            if path.suffix in ('.v','.sv','.svh','.vh'):
                for rel in re.findall(r'"(\.\./tv/(?:cdatafile|stream_size)/[^"\r\n]+)"',path.read_text(encoding='utf-8-sig')):
                    assert (out/'verilog'/rel).resolve().is_file(),rel
        cases.append(dict(name=name,bits=chain['bits'],chain=chain,fixture_sha256=fixture,
                          path=out.relative_to(ROOT).as_posix(),cycle_budget=cycle_budget,wall_budget_s=wall_s,
                          expected=dict(output_words=chain['output_words64'],output_bytes=chain['output_bytes'],
                                        weight_beats_per_shard=reads,mac_calls_per_shard=calls,descriptors=chain['descriptor_count'],
                                        input_words=170 if name=='W2_max' else chain['input_words128']),
                          full_real_numerical=name!='W2_max',maximum_pressure=name=='W2_max',
                          files=[evidence(p) for p in sorted(out.rglob('*')) if p.is_file()]))
    # One new compiled monitor, identical RTL and VIP across the four isolated
    # runtime input directories. Exact compiled snapshot is copied only after
    # compile success; timeout runs in a fifth isolated directory.
    models=[p for p in (OUT/'W2_max/verilog').rglob('*') if p.is_file()]
    for c in cases[1:]:
        for path in models:
            assert sha(path)==sha(ROOT/c['path']/'verilog'/path.relative_to(OUT/'W2_max/verilog'))
    r=dict(status='PREPARED_M441_W2_W4_MISSING_SIMULATION18',build_id='0x4D343431',audit_sha256=sha(RUN/'AUDIT.json'),
           unchanged_DUT_RTL=True,seed=441,random_delay_range=[0,8],AR_hold_at_least_cycles=10000,
           output_hold_at_least_cycles=100000,final_TLAST_hold_valid_cycles=128,
           cases=cases,order=['W2_max','timeout','q','gate_up','mlp_down'],
           global_wall_budget_s=22*3600,compile_wall_budget_s=3600,
           estimated_hours=audit_result['estimate_hours'],existing_PASS_not_rerun=True,board=False,production_changed=False,
           controller=evidence(HERE/'m441_sim_control18.py'),collector=evidence(HERE/'m441_sim_evidence18.py'),
           generator=evidence(Path(__file__)))
    atomic(PREP,encoded(r),immutable=True)
    sync('latest_m441_simulation_preparation18',dict(status=r['status'],result=PREP.relative_to(ROOT).as_posix(),sha256=sha(PREP),board=False),
         '## M441 W2/W4缺口仿真冻结18（2026-10-10）\n\nSHA '+sha(PREP)+'；四个隔离夹具/同原DUT/完整真实参考，固定seed441延迟0..8、AR≥10000/RX≥100000拍及尾TLAST128有效拍；先W2最大和同快照200周期timeout，随后完整Q/两W4。固定周期/墙钟预算，已有attempt只Collect，超预算保留进程。尚未执行/新增PASS，0板端/综合布线/生产修改。')
    print(r['status'],sha(PREP),flush=True)


if __name__=='__main__':prepare()
