"""Prepare separate legal maximum descriptor/FIFO case; never run hardware."""
import json
import shutil
import struct
from pathlib import Path
from m356_prepare_rtl_trace import tv
import m351_workflow as w
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'deployment/mage_vl4b/optimization_v1'
OUT=ROOT/'tmp/m357_maxfifo_trace'
def main():
    if OUT.exists():raise RuntimeError('Existing max fixture; inspect only')
    data=OUT/'tv/cdatafile';data.mkdir(parents=True);sizes=OUT/'tv/stream_size';sizes.mkdir();(OUT/'tv/rtldatafile').mkdir();(OUT/'verilog').mkdir()
    prefix='c.m89x_runtime_kernel.'
    tv(data/(prefix+'autotvin_config_r.dat'),['0x000a0401'])
    tv(data/(prefix+'autotvout_ap_return.dat'),['0x4d333537'])
    for i in range(4):
        tv(data/(prefix+'autotvin_s'+str(i)+'.dat'),['0x0'])
        raw=b''.join(b'\0'*16+b'\1'*(16*16) for _ in range(64))
        assert len(raw)==1088*16
        (data/(prefix+'autotvin_w'+str(i)+'.dat')).write_bytes(struct.pack('>Q',1088)+raw+bytes.fromhex('5a5aa5a50f0ff0f0'))
    packet=(512<<32|4<<42).to_bytes(16,'little')*10
    packet+=b''.join(b'\1'*64+bytes.fromhex('003c')+b'\0'*14 for _ in range(32))
    golden=b'\0'*(32768*10*8)
    for direction,port,raw,width in [('in','tx',packet,16),('out','rx',golden,8)]:
        count=len(raw)//width
        for field in ('data','keep','strb','last'):
            values=['0x'+format(int.from_bytes(raw[i*width:(i+1)*width],'little') if field=='data' else (int(i==count-1) if field=='last' else (1<<width)-1),'x') for i in range(count)]
            tv(data/(prefix+'autotv'+direction+'_'+port+'_V_'+field+'_V.dat'),values)
            tv(sizes/('stream_size_'+direction+'_'+port+'_V_'+field+'_V.dat'),[count])
            label='ingress' if direction=='in' else 'egress'
            (sizes/('stream_'+label+'_status_'+port+'_V_'+field+'_V.dat')).write_text('[[[runtime]]]\n[[[/runtime]]]\n',encoding='utf-8')
    (OUT/'golden.bin').write_bytes(golden)
    tcl='''set ready_path /apatb_m89x_runtime_kernel_top/svtb_top/svr_rx_if/ready
add_force $ready_path 0
run 2880us
if {[get_value -radix unsigned /apatb_m89x_runtime_kernel_top/rx_TREADY] != 0} {error "Shared VIP output backpressure not effective"}
puts "M357_SHARED_VIP_OUTPUT_HOLD_VERIFIED cycles=600000"
remove_forces $ready_path
run all
quit
'''
    (OUT/'verilog/m357_max_run.tcl').write_text(tcl,encoding='utf-8')
    result=dict(status='PREPARED_CANDIDATE_MAX_DESCRIPTOR_FIFO_FIXTURE',build_id='0x4D333537',groups=1,bits=4,descriptor_count=10,
        rows_per_shard=512,pairs_per_shard_per_descriptor=8192,output_words=327680,output_bytes=len(golden),
        expected_output_sha256=w.sha(OUT/'golden.bin'),input_bytes=len(packet),packet_sha256=w.sha(data/(prefix+'autotvin_tx_V_data_V.dat')),
        backpressure='Force shared UVM AXIS interface ready=0 for 600000 cycles, verify DUT observes 0, then release; do not force only DUT',
        oracle='Nonzero activations and packed weight codes, zero weight scales => complete wire output exactly zero',
        files=[dict(path=p.relative_to(ROOT).as_posix(),sha256=w.sha(p)) for p in sorted(OUT.rglob('*')) if p.is_file()],rtl_run=False,board_run=False)
    ev=BASE/'runs/M357-max-fifo-preparation-01/RESULT.json';w.atomic(ev,w.encoded(result),immutable=True)
    print(json.dumps(dict(status=result['status'],sha256=w.sha(ev)),ensure_ascii=True))

if __name__=='__main__':main()
