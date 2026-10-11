"""Isolated generated-TB backpressure test; unchanged DUT and frozen expected output."""
import json
import shutil
from pathlib import Path
from measurement import sha256, write_json
root=Path(__file__).resolve().parents[2]
src=root/'tmp/op01_decode_one_rtl/hls/sim'
dst=root/'tmp/op01_decode_one_occupancy_v3'
smoke=root/'tmp/op01_ready_driver_recovery/xsim.log'
if 'VIP_DRIVER_RECOVERY_PASS transfers=32 mismatches=0' not in smoke.read_text():
    raise RuntimeError('Shared-ready injection smoke missing')
if dst.exists():raise RuntimeError('Refuse existing occupancy staging')
if 'Pass' not in (src/'report/op01_decode_one_kernel_cosim.rpt').read_text():raise RuntimeError('Normal PASS missing')
for folder in ['verilog','tv']:shutil.copytree(src/folder,dst/folder)
expected={}
for p in (dst/'tv/rtldatafile').glob('rtl.*.dat'):
    expected[p.name]=sha256(p)
    p.unlink() # Only cloned output files; force this run to produce fresh evidence.
if len(expected)!=5:raise RuntimeError('Expected five output streams')
tb=dst/'verilog/op01_decode_one_kernel.autotb.v'
text=tb.read_text()
if text.count('endmodule')!=1:raise RuntimeError('Unexpected testbench')
hier='AESL_inst_op01_decode_one_kernel.grp_m89x_four_fu_317'
names=['result_U','result_1_U','result_2_U','result_3_U']
code='\n// External output backpressure only; no DUT arithmetic modification.\n'
for i,name in enumerate(names):
    code+=f'''integer occ_peak_{i} = 0;
always @(posedge AESL_clock) begin
  if ({hier}.{name}.num_data_cnt > occ_peak_{i})
    occ_peak_{i} = {hier}.{name}.num_data_cnt;
  if ({hier}.{name}.num_data_cnt > 8192)
    $fatal(1, "OP01_FIFO_OVERFLOW shard={i}");
end
'''
code+='''// Force the interface observed by BOTH the VIP monitor and DUT.
always @(posedge AESL_clock) begin
  if (start_cnt > 0 && (rx_TREADY !== svtb_top.svr_rx_if.ready))
    $fatal(1, "OP01_READY_OBSERVATION_MISMATCH");
end
integer occ_tx;
integer hold_cycle;
initial begin
  for (occ_tx=0; occ_tx<4; occ_tx=occ_tx+1) begin
    @(negedge AESL_clock);
    if (occ_tx==0 || occ_tx==2) force svtb_top.svr_rx_if.ready = 1'b0;
    wait (start_cnt > occ_tx);
    if (occ_tx==0 || occ_tx==2) begin
'''+f'''      wait ({hier}.result_3_U.num_data_cnt == 8192);
'''+'''      $display("OP01_FIFO_FULL tx=%0d shard=3 occupancy=8192",occ_tx);
      for (hold_cycle=0; hold_cycle<256; hold_cycle=hold_cycle+1) begin
        @(posedge AESL_clock);
'''+f'''        if ({hier}.result_3_U.num_data_cnt != 8192)
          $fatal(1, "OP01_FULL_HOLD_LOST");
'''+'''      end
      @(negedge AESL_clock);
      $display("OP01_FULL_HOLD_PASS tx=%0d cycles=256 release_time=%0t",occ_tx,$time);
      release svtb_top.svr_rx_if.ready;
      svtb_top.svr_rx_if.ready = 1'b1;
    end
    wait (finish_cnt > occ_tx);
    $display("OP01_OCC_TX_COMPLETE tx=%0d time=%0t peaks=%0d,%0d,%0d,%0d",occ_tx,$time,occ_peak_0,occ_peak_1,occ_peak_2,occ_peak_3);
  end
  $display("OP01_FIFO_OCCUPANCY_PASS peaks=%0d,%0d,%0d,%0d",occ_peak_0,occ_peak_1,occ_peak_2,occ_peak_3);
end
initial begin
  wait (start_cnt > 0);
  repeat (12000000) @(posedge AESL_clock);
  if (finish_cnt != 4) $fatal(1,"OP01_OCCUPANCY_TIMEOUT");
end
'''
code+='''integer heartbeat_cycle=0;
always @(posedge AESL_clock) begin
  heartbeat_cycle=heartbeat_cycle+1;
  if (heartbeat_cycle % 100000 == 0)
'''+f'''    $display("OP01_HEARTBEAT cycle=%0d start=%0d finish=%0d fifo=%0d,%0d,%0d,%0d ready=%b time=%0t",heartbeat_cycle,start_cnt,finish_cnt,{hier}.result_U.num_data_cnt,{hier}.result_1_U.num_data_cnt,{hier}.result_2_U.num_data_cnt,{hier}.result_3_U.num_data_cnt,rx_TREADY,$time);
'''+'''  if (heartbeat_cycle==1000000 && start_cnt==0)
    $fatal(1,"OP01_NO_TRANSACTION_START");
end
'''
tb.write_text(text.replace('endmodule',code+'\nendmodule'))
calls=[line for line in (dst/'verilog/run_xsim.bat').read_text().splitlines() if line.strip().lower().startswith('call ')]
if len(calls)!=2:raise RuntimeError('Unexpected simulator runner')
(dst/'verilog/run_occupancy.cmd').write_text('@echo off\nset PATH=\n'+calls[0]+'\nif errorlevel 1 exit /b %errorlevel%\n'+calls[1]+'\nexit /b %errorlevel%\n')
write_json(dst/'PREPARATION.json',dict(status='PREPARED_NOT_EXECUTED',tb_sha256=sha256(tb),
    expected_outputs=expected,normal_report_sha256=sha256(src/'report/op01_decode_one_kernel_cosim.rpt'),
    injection_smoke_sha256=sha256(smoke),
    bound_cycles=12000000,scope='Hold shared svr_rx_if.ready until shard3 reaches8192 in each max-row mode; assert256cycle full hold and handshake equivalence; release and compare outputs; not all FIFOs required to reach8192',
    dut_files={p.name:sha256(p) for p in (src/'verilog').glob('*.v') if p.name!=tb.name}))
print('OCCUPANCY_PREPARED_NOT_EXECUTED')
