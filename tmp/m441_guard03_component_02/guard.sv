
`timescale 1ns/1ps
`define D guard_tb
module guard_tb;
reg clk=0;always #1 clk=~clk;
reg tx_TVALID=0,tx_TREADY=1,rx_TVALID=0,rx_TREADY=1,ap_done=0;
reg [3:0] arok=0,rok=0,iter=0,start=0,old_start=0;
reg ctrl_activity=0;
longint tx_seen=0,rx_backpressure=0,tx_backpressure=0,ctrl_seen=0;
integer cyc=0,stagnant=0;string test_case;
task automatic progress_snapshot(input integer terminal_kind);
 $display("M441_GUARD_SNAPSHOT cycle=%0d stagnant=%0d terminal=%0d",cyc,stagnant,terminal_kind);
endtask
initial begin
 if(!$value$plusargs("CASE=%s",test_case))$fatal(1,"CASE required");
 if(test_case=="budget")cyc=79999998;
end
always @(posedge clk)begin
 cyc=cyc+1;if(cyc>80000000)begin progress_snapshot(2);$fatal(1,"M441 bounded RTL cycle budget exceeded"); end

 if(`D.tx_TVALID&&`D.tx_TREADY)tx_seen=tx_seen+1;
 if(`D.rx_TVALID&&!`D.rx_TREADY)rx_backpressure=rx_backpressure+1;
 if(`D.tx_TVALID&&!`D.tx_TREADY)tx_backpressure=tx_backpressure+1;
 if(ctrl_activity)ctrl_seen=ctrl_seen+1;
 if((`D.tx_TVALID&&`D.tx_TREADY)||(`D.rx_TVALID&&`D.rx_TREADY)||
    (|arok)||(|rok)||(|iter)||(|(start&~old_start))||ctrl_activity||`D.ap_done)stagnant=0;
 else stagnant=stagnant+1;
 if(stagnant>=1000000)begin progress_snapshot(2);$fatal(1,"M441 global progress stalled for 1000000 cycles");end

 old_start=start;
 if(test_case=="progress")begin
  tx_TVALID=(cyc%10==0);
  if(cyc==1000100)begin progress_snapshot(1);$display("M441_GUARD_DONE");$finish;end
 end
end
endmodule
