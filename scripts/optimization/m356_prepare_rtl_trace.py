"""Isolate exact stable RTL/VIP and frozen 0:q chain; never edit stable HLS tree."""
import importlib.util
import json
import shutil
import struct
import sys
from pathlib import Path
import m351_workflow as w
from m355_reference import activation, digest

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'deployment/mage_vl4b/optimization_v1'
OUT=ROOT/'tmp/m356_stable_q_trace'

def tv(path,values):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text('[[[runtime]]]\n[[transaction]] 0\n'+'\n'.join(map(str,values))+'\n[[/transaction]]\n[[[/runtime]]]\n',encoding='utf-8')

def main():
    if OUT.exists():raise RuntimeError('Existing isolated trace directory; do not regenerate or rerun')
    spec=json.loads((BASE/'candidates/M355-device-phase-01/CASE_CONTRACT.json').read_text(encoding='utf-8'))
    case=spec['cases'][0];chain=case['chain']
    assert chain['chain_index']==0 and chain['descriptor_count']==2
    stable=ROOT/'deployment/mage_vl4b/m175_m120_fixed_text_candidate'
    p=stable/'runtime/contract_runtime.py'
    assert w.sha(p)==spec['stable_sources']['runtime/contract_runtime.py']['sha256']
    module_spec=importlib.util.spec_from_file_location('contract_runtime',p)
    module=importlib.util.module_from_spec(module_spec);sys.modules['contract_runtime']=module;module_spec.loader.exec_module(module)
    packet=module.pack_chain_input(chain,activation(chain['groups']),case['base_words'],0)
    assert digest(packet)==case['packet_sha256']
    golden=(BASE/'runs/M355-device-phase-preparation-01/golden/0.bin').read_bytes()
    assert digest(golden)==case['expected_ftz_sha256']
    source=ROOT/'m132_m120_fifo_backpressure_hls/hls/sim/verilog'
    allowed={'.v','.vh','.sv','.svh','.vhd','.prj','.mem'}
    checked=[]
    for p in sorted(source.rglob('*')):
        rel=p.relative_to(source)
        if not p.is_file() or p.suffix not in allowed or any(a.startswith('xsim') for a in rel.parts):continue
        dest=OUT/'verilog'/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
        checked.append(dict(path=p.relative_to(ROOT).as_posix(),sha256=w.sha(p),copy=dest.relative_to(ROOT).as_posix()))
    syn=ROOT/'m132_m120_fifo_backpressure_hls/hls/syn/verilog'
    for p in syn.glob('*.v'):
        dest=OUT/'verilog'/p.name
        # The old VIP directory has instrumented deadlock-monitor variants.
        # Compare the stable computational modules, preserving VIP instrumentation.
        if dest.exists() and p.name not in ('m89x_runtime_kernel.v','m89x_runtime_kernel_m89x_four.v'):
            assert w.sha(p)==w.sha(dest),p.name
    rd='m89x_runtime_kernel_m89x_four_Block_entry_x_0_rd_proc.v'
    assert w.sha(OUT/'verilog'/rd)=='aa1f872c715eb7a42f3e33f3cb229ded051e2430f0c615de5eb0fdb8b2dd8f8f'
    data=OUT/'tv/cdatafile';data.mkdir(parents=True)
    (OUT/'tv/rtldatafile').mkdir();sizes=OUT/'tv/stream_size';sizes.mkdir()
    prefix='c.m89x_runtime_kernel.'
    tv(data/(prefix+'autotvin_config_r.dat'),[chain['config_u32']])
    for i in range(4):tv(data/(prefix+'autotvin_s'+str(i)+'.dat'),['0x00000000'])
    release=ROOT/'release_staging/kv260-mage-vl-4b-prebuilt-install-20260926-v7/external_assets/weights/language_fourport'
    for i,row in enumerate(case['windows']):
        with (release/row['file']).open('rb') as f:f.seek(case['base_words']*16);raw=f.read(case['window_bytes_per_port'])
        assert digest(raw)==row['sha256']
        # $fread loads vectors in big-endian byte order; weight source words are LE.
        words=b''.join(raw[j:j+16][::-1] for j in range(0,len(raw),16))
        (data/(prefix+'autotvin_w'+str(i)+'.dat')).write_bytes(struct.pack('>Q',len(raw)//16)+words+bytes.fromhex('5a5aa5a50f0ff0f0'))
    for direction,port,raw,width in [('in','tx',packet,16),('out','rx',golden,8)]:
        count=len(raw)//width
        for field in ('data','keep','strb','last'):
            values=[]
            for i in range(count):
                value=int.from_bytes(raw[i*width:(i+1)*width],'little') if field=='data' else (int(i==count-1) if field=='last' else (1<<width)-1)
                values.append('0x'+format(value,'x'))
            tv(data/(prefix+'autotv'+direction+'_'+port+'_V_'+field+'_V.dat'),values)
            tv(sizes/('stream_size_'+direction+'_'+port+'_V_'+field+'_V.dat'),[count])
            label='ingress' if direction=='in' else 'egress'
            # Empty ingress-status queue is valid: stream sizes control the actual TV.
            (sizes/('stream_'+label+'_status_'+port+'_V_'+field+'_V.dat')).write_text('[[[runtime]]]\n[[[/runtime]]]\n',encoding='utf-8')
    tv(data/(prefix+'autotvout_ap_return.dat'),['0x4d395832'])
    (OUT/'golden.bin').write_bytes(golden)
    shutil.copyfile(ROOT/'scripts/optimization/m356_trace_monitor.sv',OUT/'verilog/m356_trace_monitor.sv')
    prj=OUT/'verilog/m89x_runtime_kernel.prj'
    prj.write_text(prj.read_text(encoding='utf-8')+'\nsv xil_defaultlib "m356_trace_monitor.sv"\n',encoding='utf-8')
    (OUT/'verilog/m356_run.tcl').write_text('run all\nquit\n',encoding='utf-8')
    result=dict(status='PREPARED_STABLE_RTL_REPRESENTATIVE_TRACE',build_id='0x4D395832',candidate_changed=False,board_run=False,
        chain=chain,packet_sha256=digest(packet),golden_sha256=digest(golden),copied_sources=checked,
        source_rtl_sha256=w.sha(syn/rd),vip='Original generated AXI/AXIS VIP, NO_DELAY sequence; no new board evidence',
        pending='Compile and simulate isolated 0:q; quantify shared activation scheduling, AXI and output FIFO; candidate not implemented')
    evidence=BASE/'runs/M356-stable-rtl-trace-preparation-01/RESULT.json'
    w.atomic(evidence,w.encoded(result),immutable=True)
    sha=w.sha(evidence)
    w.sync('M356_stable_rtl_trace_preparation',dict(status=result['status'],sha256=sha,evidence_path=evidence.relative_to(ROOT).as_posix(),build_id='0x4D395832',board_run=False),
        'M356 用户授权设备控制/供给优化。隔离复制匹配稳定 Build 的 RTL/VIP，冻结真实 0:q 两 descriptor 与完整输出，仅准备未仿真、未改电路、未上板。共享激活和 scale 双口存储导致 read-proc 状态 2/4/6/8 依次服务四 shard；不能直接同时启动。下一步独立 RTL 波形与完整输出核对。证据 '+sha)
    print(json.dumps(dict(status=result['status'],evidence=str(evidence),sha256=sha,source_count=len(checked)),ensure_ascii=True))

if __name__=='__main__':main()
