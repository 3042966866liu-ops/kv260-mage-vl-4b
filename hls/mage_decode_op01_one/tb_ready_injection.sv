`timescale 1ns/1ps
interface ready_probe_if;
  logic ready;
endinterface
module tb_ready_injection;
  reg clk=0;
  always #5 clk=~clk;
  ready_probe_if vip();
  wire dut_ready;
  assign dut_ready=vip.ready;
  reg active=0;
  integer dut_count=0, monitor_count=0, mismatch=0;
  integer phase=0;
  always @(negedge clk) vip.ready=1;
  always @(posedge clk) if(active) begin
    if(dut_ready) dut_count=dut_count+1;
    if(vip.ready) monitor_count=monitor_count+1;
    if(dut_ready !== vip.ready) mismatch=mismatch+1;
  end
  initial begin
    repeat(3) @(negedge clk);
    #1; active=1; force dut_ready=0;
    repeat(32) @(posedge clk);
    @(negedge clk); #1; active=0;
    if(dut_count!=0 || monitor_count!=32 || mismatch!=32)
      $fatal(1,"OLD_INJECTION_NOT_REPRODUCED");
    $display("OLD_INJECTION_REPRODUCED dut=%0d monitor=%0d mismatch=%0d",dut_count,monitor_count,mismatch);
    release dut_ready;
    dut_count=0; monitor_count=0; mismatch=0;
    force vip.ready=0; active=1; phase=1;
    repeat(256) @(posedge clk);
    @(negedge clk); #1;
    if(dut_count!=0 || monitor_count!=0 || mismatch!=0)
      $fatal(1,"SHARED_READY_HOLD_FAILED");
    release vip.ready;
    repeat(33) @(posedge clk);
    @(negedge clk); #1; active=0;
    if(dut_count!=32 || monitor_count!=32 || mismatch!=0)
      $fatal(1,"SHARED_READY_RECOVERY_FAILED dut=%0d monitor=%0d",dut_count,monitor_count);
    $display("SHARED_READY_SMOKE_PASS blocked_cycles=256 recovered_transfers=32 mismatches=0");
    $finish;
  end
  initial begin #10000; $fatal(1,"SMOKE_TIMEOUT"); end
endmodule
