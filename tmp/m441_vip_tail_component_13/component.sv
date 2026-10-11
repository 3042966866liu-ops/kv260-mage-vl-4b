
`timescale 1ns/1ps
module actual_vip_tail;
import uvm_pkg::*;import svr_pkg::*;
reg rx_clk=0;always #1 rx_clk=~rx_clk;
svr_if #(64) sink(rx_clk,1'b1);
string scenario;
bit tail_block=0,tail_armed=0,tail_released=0;
reg rx_valid=0,rx_last=0;
wire rx_ready=sink.ready && !(scenario!="old_release"&&tail_block);
assign sink.valid=rx_valid && !(scenario!="old_release"&&tail_block);
assign sink.data=64'b0;
integer words=327677,cycles=0,held_edges=0,accepted=0;
integer tail_hold_valid_cycles=0;
svr_slave_driver #(64) driver;
svr_transfer #(64) item;
task automatic progress_snapshot(input integer kind);$display("VIP_SNAPSHOT kind=%0d",kind);endtask
initial begin
 if(!$value$plusargs("CASE=%s",scenario))$fatal(1,"case missing");
 sink.ready=0;
 driver=new("actual_vendor_driver",null);driver.vif=sink;driver.cfg=new();
 driver.cfg.prt_type=AXIS;driver.cfg.reset_level=RESET_LEVEL_LOW;
 for(integer k=0;k<3;k++)begin
  item=new();item.delay=(scenario=="delay8")?8:0;
  @(negedge rx_clk);driver.get_and_drive(item);accepted++;
 end
 #0.2;
 if(words!=327680||held_edges<128||tail_hold_valid_cycles!=128||!tail_released||accepted!=3)$fatal(1,"actual VIP incomplete or hold");
 $display("M441_ACTUAL_VIP_TAIL_PASS words=%0d held_edges=%0d accepted=%0d",words,held_edges,accepted);$finish;
end
always @(posedge rx_clk)begin
 cycles++;
 if(rx_valid&&rx_last&&!rx_ready)held_edges++;
 if(rx_valid&&rx_ready)words++;
 if(cycles>1000)begin
  if(scenario=="old_release"&&words==327679&&tail_hold_valid_cycles==128&&tail_released&&sink.ready==0)begin
   $display("M441_ACTUAL_VIP_OLD_RELEASE_STUCK words=%0d ready=%0d held=%0d",words,sink.ready,tail_hold_valid_cycles);$finish;
  end
  $display("VIP_BUDGET words=%0d ready=%0d armed=%0d released=%0d held=%0d accepted=%0d",words,sink.ready,tail_armed,tail_released,tail_hold_valid_cycles,accepted);$fatal(1,"actual receiver component budget");
 end
end
always @(negedge rx_clk)begin #0.1;rx_valid=1;rx_last=(words==327679);end
generate if(1)begin:tail_hook
always @(negedge rx_clk)begin end
// Shared VIP ready, not a forced DUT datapath signal. Arm before last transfer.
always @(negedge rx_clk)begin
 if(scenario=="old_release"&&!tail_armed && words==327679)begin
  force sink.ready=0;
  tail_armed=1;
 end else if(scenario=="old_release"&&tail_armed && !tail_released && rx_valid && rx_last)begin
  if(rx_ready)begin progress_snapshot(2);$fatal(1,"M441 final hold ready not low");end
  tail_hold_valid_cycles=tail_hold_valid_cycles+1;
  if(tail_hold_valid_cycles==128)begin
   release sink.ready;
   tail_released=1;
   $display("M441_BOUNDARY_LAST_HOLD valid_cycles=%0d accepted_before=%0d",tail_hold_valid_cycles,words);
  end
 end
end



always @(negedge rx_clk)begin
 if(scenario!="old_release"&&!tail_armed && words==327679)begin
  tail_block=1;tail_armed=1;
 end else if(scenario!="old_release"&&tail_armed&&!tail_released&&rx_valid&&rx_last)begin
  if(rx_ready)$fatal(1,"held last ready not low");
  tail_hold_valid_cycles++;
  if(tail_hold_valid_cycles==128)begin
   tail_block=0;tail_released=1;
   $display("M441_BOUNDARY_LAST_HOLD valid_cycles=%0d accepted_before=%0d",tail_hold_valid_cycles,words);
  end
 end
end
end endgenerate
endmodule
