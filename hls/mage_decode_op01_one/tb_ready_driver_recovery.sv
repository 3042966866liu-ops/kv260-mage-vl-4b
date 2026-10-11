`timescale 1ns/1ps
interface ready_driver_if;
  logic ready=0;
endinterface
module tb_ready_driver_recovery;
  reg clk=0;
  always #5 clk=~clk;
  ready_driver_if vip();
  wire dut_ready=vip.ready;
  integer transfers=0, mismatches=0, packet=0;
  always @(posedge clk) begin
    if (dut_ready) transfers=transfers+1;
    if (dut_ready !== vip.ready) mismatches=mismatches+1;
  end
  // Same relevant semantics as svr_slave_driver::get_and_drive:
  // one blocking ready=1, then wait for valid && ready; no periodic rewrite.
  initial begin
    repeat(2) @(negedge clk);
    for(packet=0;packet<32;packet=packet+1) begin
      vip.ready=1;
      forever begin
        @(posedge clk);
        if(vip.ready==1) begin vip.ready<=0; break; end
      end
      @(negedge clk);
    end
  end
  initial begin
    @(negedge clk); #1; force vip.ready=0;
    repeat(256) @(posedge clk);
    @(negedge clk); #1; release vip.ready;
    repeat(32) @(posedge clk);
    @(negedge clk); #1;
    if(transfers!=0 || vip.ready!==0) $fatal(1,"RELEASE_STALL_NOT_REPRODUCED");
    $display("RELEASE_ONLY_STALL_REPRODUCED transfers=0 ready=0");
    vip.ready=1; // Restore the driver's pending request at a non-sampling edge.
    repeat(33) @(posedge clk);
    @(negedge clk); #1;
    if(transfers!=32 || mismatches!=0) $fatal(1,"RECOVERY_FAILED transfers=%0d mismatch=%0d",transfers,mismatches);
    $display("VIP_DRIVER_RECOVERY_PASS transfers=32 mismatches=0");
    $finish;
  end
  initial begin #10000; $fatal(1,"SMOKE_TIMEOUT"); end
endmodule
