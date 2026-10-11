
`timescale 1ns/1ps
`define D apatb_m89x_runtime_kernel_top
module ready_fake; reg ready=1; endmodule
module svtb_fake; ready_fake svr_rx_if(); endmodule
class svr_latency; function new(string name="");endfunction endclass
class axi_latency; function new(string name="");endfunction endclass
class svr_latency_tx extends svr_latency;
        rand int    transfer_latency;
        function new ( string name = "svr_latency_tx" );
            super.new(name);
        endfunction
        virtual function int get_transfer_lat();
 static longint count=0,total=0;

            int delay;
            if ($test$plusargs("M438_ZERO_EXTRA_LATENCY")) return 0;
            void'(std::randomize(delay) with {
				delay dist {0:=8, 0:=1, 8:=1, [0:8]:/2};
				delay inside {[0:8]};
				});
            transfer_latency = delay;
            count=count+1;total=total+delay;
 if(count%4096==0)$display("M441_DELAY channel=svr_latency_tx_get_transfer_lat count=%0d sum=%0d",count,total);
 return delay;
        endfunction
    endclass
class svr_latency_rx extends svr_latency;
        rand int    transfer_latency;
        function new ( string name = "svr_latency_rx" );
            super.new(name);
        endfunction
        virtual function int get_transfer_lat();
 static longint count=0,total=0;

            int delay;
            if ($test$plusargs("M438_ZERO_EXTRA_LATENCY")) return 0;
            void'(std::randomize(delay) with {
				delay dist {0:=8, 0:=1, 8:=1, [0:8]:/2};
				delay inside {[0:8]};
				});
            transfer_latency = delay;
            count=count+1;total=total+delay;
 if(count%4096==0)$display("M441_DELAY channel=svr_latency_rx_get_transfer_lat count=%0d sum=%0d",count,total);
 return delay;
        endfunction
    endclass
class axi_latency_w0 extends axi_latency;
        rand int    wctrl_latency;
        rand int    wdata_latency;
        rand int    wbrsp_latency;
        rand int    rctrl_latency;
        rand int    rdata_latency;
        function new ( string name = "axi_latency_w0" );
            super.new(name);
        endfunction
        virtual function int get_wctrl_lat();
            int delay;
            if ($test$plusargs("M438_ZERO_EXTRA_LATENCY")) return 0;
            void'(std::randomize(delay) with {
				delay dist {0:=8, 0:=1, 8:=1, [0:8]:/2};
				delay inside {[0:8]};
				});
            wctrl_latency = delay;
            return wctrl_latency;
        endfunction
        virtual function int get_wdata_lat();
            int delay;
            if ($test$plusargs("M438_ZERO_EXTRA_LATENCY")) return 0;
            void'(std::randomize(delay) with {
				delay dist {0:=8, 0:=1, 8:=1, [0:8]:/2};
				delay inside {[0:8]};
				});
            wdata_latency = delay;
            return wdata_latency;
        endfunction
        virtual function int get_wbrsp_lat();
            int delay;
            if ($test$plusargs("M438_ZERO_EXTRA_LATENCY")) return 0;
            void'(std::randomize(delay) with {
				delay dist {0:=8, 0:=1, 8:=1, [0:8]:/2};
				delay inside {[0:8]};
				});
            wbrsp_latency = delay;
            return wbrsp_latency;
        endfunction
        virtual function int get_rctrl_lat();
 static longint count=0,total=0;

            int delay;
            if ($test$plusargs("M438_ZERO_EXTRA_LATENCY")) return 0;
            void'(std::randomize(delay) with {
				delay dist {0:=8, 0:=1, 8:=1, [0:8]:/2};
				delay inside {[0:8]};
				});
            rctrl_latency = delay;
            count=count+1;total=total+delay;
 if(count%4096==0)$display("M441_DELAY channel=axi_latency_w0_get_rctrl_lat count=%0d sum=%0d",count,total);
 return delay;
        endfunction
        virtual function int get_rdata_lat();
 static longint count=0,total=0;

            int delay;
            if ($test$plusargs("M438_ZERO_EXTRA_LATENCY")) return 0;
            void'(std::randomize(delay) with {
				delay dist {0:=8, 0:=1, 8:=1, [0:8]:/2};
				delay inside {[0:8]};
				});
            rdata_latency = delay;
            count=count+1;total=total+delay;
 if(count%4096==0)$display("M441_DELAY channel=axi_latency_w0_get_rdata_lat count=%0d sum=%0d",count,total);
 return delay;
        endfunction
    endclass
class axi_latency_w1 extends axi_latency;
        rand int    wctrl_latency;
        rand int    wdata_latency;
        rand int    wbrsp_latency;
        rand int    rctrl_latency;
        rand int    rdata_latency;
        function new ( string name = "axi_latency_w1" );
            super.new(name);
        endfunction
        virtual function int get_wctrl_lat();
            int delay;
            if ($test$plusargs("M438_ZERO_EXTRA_LATENCY")) return 0;
            void'(std::randomize(delay) with {
				delay dist {0:=8, 0:=1, 8:=1, [0:8]:/2};
				delay inside {[0:8]};
				});
            wctrl_latency = delay;
            return wctrl_latency;
        endfunction
        virtual function int get_wdata_lat();
            int delay;
            if ($test$plusargs("M438_ZERO_EXTRA_LATENCY")) return 0;
            void'(std::randomize(delay) with {
				delay dist {0:=8, 0:=1, 8:=1, [0:8]:/2};
				delay inside {[0:8]};
				});
            wdata_latency = delay;
            return wdata_latency;
        endfunction
        virtual function int get_wbrsp_lat();
            int delay;
            if ($test$plusargs("M438_ZERO_EXTRA_LATENCY")) return 0;
            void'(std::randomize(delay) with {
				delay dist {0:=8, 0:=1, 8:=1, [0:8]:/2};
				delay inside {[0:8]};
				});
            wbrsp_latency = delay;
            return wbrsp_latency;
        endfunction
        virtual function int get_rctrl_lat();
 static longint count=0,total=0;

            int delay;
            if ($test$plusargs("M438_ZERO_EXTRA_LATENCY")) return 0;
            void'(std::randomize(delay) with {
				delay dist {0:=8, 0:=1, 8:=1, [0:8]:/2};
				delay inside {[0:8]};
				});
            rctrl_latency = delay;
            count=count+1;total=total+delay;
 if(count%4096==0)$display("M441_DELAY channel=axi_latency_w1_get_rctrl_lat count=%0d sum=%0d",count,total);
 return delay;
        endfunction
        virtual function int get_rdata_lat();
 static longint count=0,total=0;

            int delay;
            if ($test$plusargs("M438_ZERO_EXTRA_LATENCY")) return 0;
            void'(std::randomize(delay) with {
				delay dist {0:=8, 0:=1, 8:=1, [0:8]:/2};
				delay inside {[0:8]};
				});
            rdata_latency = delay;
            count=count+1;total=total+delay;
 if(count%4096==0)$display("M441_DELAY channel=axi_latency_w1_get_rdata_lat count=%0d sum=%0d",count,total);
 return delay;
        endfunction
    endclass
class axi_latency_w2 extends axi_latency;
        rand int    wctrl_latency;
        rand int    wdata_latency;
        rand int    wbrsp_latency;
        rand int    rctrl_latency;
        rand int    rdata_latency;
        function new ( string name = "axi_latency_w2" );
            super.new(name);
        endfunction
        virtual function int get_wctrl_lat();
            int delay;
            if ($test$plusargs("M438_ZERO_EXTRA_LATENCY")) return 0;
            void'(std::randomize(delay) with {
				delay dist {0:=8, 0:=1, 8:=1, [0:8]:/2};
				delay inside {[0:8]};
				});
            wctrl_latency = delay;
            return wctrl_latency;
        endfunction
        virtual function int get_wdata_lat();
            int delay;
            if ($test$plusargs("M438_ZERO_EXTRA_LATENCY")) return 0;
            void'(std::randomize(delay) with {
				delay dist {0:=8, 0:=1, 8:=1, [0:8]:/2};
				delay inside {[0:8]};
				});
            wdata_latency = delay;
            return wdata_latency;
        endfunction
        virtual function int get_wbrsp_lat();
            int delay;
            if ($test$plusargs("M438_ZERO_EXTRA_LATENCY")) return 0;
            void'(std::randomize(delay) with {
				delay dist {0:=8, 0:=1, 8:=1, [0:8]:/2};
				delay inside {[0:8]};
				});
            wbrsp_latency = delay;
            return wbrsp_latency;
        endfunction
        virtual function int get_rctrl_lat();
 static longint count=0,total=0;

            int delay;
            if ($test$plusargs("M438_ZERO_EXTRA_LATENCY")) return 0;
            void'(std::randomize(delay) with {
				delay dist {0:=8, 0:=1, 8:=1, [0:8]:/2};
				delay inside {[0:8]};
				});
            rctrl_latency = delay;
            count=count+1;total=total+delay;
 if(count%4096==0)$display("M441_DELAY channel=axi_latency_w2_get_rctrl_lat count=%0d sum=%0d",count,total);
 return delay;
        endfunction
        virtual function int get_rdata_lat();
 static longint count=0,total=0;

            int delay;
            if ($test$plusargs("M438_ZERO_EXTRA_LATENCY")) return 0;
            void'(std::randomize(delay) with {
				delay dist {0:=8, 0:=1, 8:=1, [0:8]:/2};
				delay inside {[0:8]};
				});
            rdata_latency = delay;
            count=count+1;total=total+delay;
 if(count%4096==0)$display("M441_DELAY channel=axi_latency_w2_get_rdata_lat count=%0d sum=%0d",count,total);
 return delay;
        endfunction
    endclass
class axi_latency_w3 extends axi_latency;
        rand int    wctrl_latency;
        rand int    wdata_latency;
        rand int    wbrsp_latency;
        rand int    rctrl_latency;
        rand int    rdata_latency;
        function new ( string name = "axi_latency_w3" );
            super.new(name);
        endfunction
        virtual function int get_wctrl_lat();
            int delay;
            if ($test$plusargs("M438_ZERO_EXTRA_LATENCY")) return 0;
            void'(std::randomize(delay) with {
				delay dist {0:=8, 0:=1, 8:=1, [0:8]:/2};
				delay inside {[0:8]};
				});
            wctrl_latency = delay;
            return wctrl_latency;
        endfunction
        virtual function int get_wdata_lat();
            int delay;
            if ($test$plusargs("M438_ZERO_EXTRA_LATENCY")) return 0;
            void'(std::randomize(delay) with {
				delay dist {0:=8, 0:=1, 8:=1, [0:8]:/2};
				delay inside {[0:8]};
				});
            wdata_latency = delay;
            return wdata_latency;
        endfunction
        virtual function int get_wbrsp_lat();
            int delay;
            if ($test$plusargs("M438_ZERO_EXTRA_LATENCY")) return 0;
            void'(std::randomize(delay) with {
				delay dist {0:=8, 0:=1, 8:=1, [0:8]:/2};
				delay inside {[0:8]};
				});
            wbrsp_latency = delay;
            return wbrsp_latency;
        endfunction
        virtual function int get_rctrl_lat();
 static longint count=0,total=0;

            int delay;
            if ($test$plusargs("M438_ZERO_EXTRA_LATENCY")) return 0;
            void'(std::randomize(delay) with {
				delay dist {0:=8, 0:=1, 8:=1, [0:8]:/2};
				delay inside {[0:8]};
				});
            rctrl_latency = delay;
            count=count+1;total=total+delay;
 if(count%4096==0)$display("M441_DELAY channel=axi_latency_w3_get_rctrl_lat count=%0d sum=%0d",count,total);
 return delay;
        endfunction
        virtual function int get_rdata_lat();
 static longint count=0,total=0;

            int delay;
            if ($test$plusargs("M438_ZERO_EXTRA_LATENCY")) return 0;
            void'(std::randomize(delay) with {
				delay dist {0:=8, 0:=1, 8:=1, [0:8]:/2};
				delay inside {[0:8]};
				});
            rdata_latency = delay;
            count=count+1;total=total+delay;
 if(count%4096==0)$display("M441_DELAY channel=axi_latency_w3_get_rdata_lat count=%0d sum=%0d",count,total);
 return delay;
        endfunction
    endclass
module apatb_m89x_runtime_kernel_top;
svtb_fake svtb_top();
reg ap_clk=0;always #1 ap_clk=~ap_clk;
reg rx_TVALID=0,rx_TLAST=0;
integer words=327677,cycles=0,held_posedges=0;string test_case;
wire rx_TREADY=(test_case=="ready_error")?1'b1:svtb_top.svr_rx_if.ready;
task automatic progress_snapshot(input integer kind);
 $display("M441_COMPONENT_SNAPSHOT terminal=%0d",kind);
endtask
svr_latency_tx tx;svr_latency_rx rx;
axi_latency_w0 w0;axi_latency_w1 w1;axi_latency_w2 w2;axi_latency_w3 w3;
integer v;
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


initial begin
 if(!$value$plusargs("CASE=%s",test_case))$fatal(1,"CASE required");
 if(test_case=="latency")begin
  tx=new();rx=new();w0=new();w1=new();w2=new();w3=new();
  for(integer j=0;j<8192;j=j+1)begin
   v=tx.get_transfer_lat();if(v<0||v>8)$fatal(1,"tx range");
   v=rx.get_transfer_lat();if(v<0||v>8)$fatal(1,"rx range");
   v=w0.get_rctrl_lat();if(v<0||v>8)$fatal(1,"w0 AR range");
   v=w0.get_rdata_lat();if(v<0||v>8)$fatal(1,"w0 R range");
   v=w1.get_rctrl_lat();if(v<0||v>8)$fatal(1,"w1 AR range");
   v=w1.get_rdata_lat();if(v<0||v>8)$fatal(1,"w1 R range");
   v=w2.get_rctrl_lat();if(v<0||v>8)$fatal(1,"w2 AR range");
   v=w2.get_rdata_lat();if(v<0||v>8)$fatal(1,"w2 R range");
   v=w3.get_rctrl_lat();if(v<0||v>8)$fatal(1,"w3 AR range");
   v=w3.get_rdata_lat();if(v<0||v>8)$fatal(1,"w3 R range");
  end
  $display("M441_COMPONENT_LATENCY_DONE draws=81920");$finish;
 end
end
always @(posedge ap_clk)begin
 cycles=cycles+1;
 if(rx_TVALID&&rx_TLAST&&!rx_TREADY)held_posedges=held_posedges+1;
 if(rx_TVALID&&rx_TREADY)begin
  words=words+1;
  if(rx_TLAST)begin
   if(words!=327680||held_posedges!=128||tail_hold_valid_cycles!=128||!tail_released)$fatal(1,"tail count");
   $display("M441_COMPONENT_TAIL_DONE held_posedges=%0d",held_posedges);$finish;
  end
 end
 if(cycles>1000)$fatal(1,"component budget");
end
// Drive after the observer's negedge, avoiding a fabricated scheduling race.
always @(negedge ap_clk)begin
 #0.1;
 svtb_top.svr_rx_if.ready=1;
 rx_TVALID=(test_case!="tail_gaps"||cycles%3!=0);
 rx_TLAST=(words==327679);
end

endmodule
