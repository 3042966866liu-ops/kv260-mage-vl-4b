`timescale 1ns/1ps
`define WGD apatb_m89x_runtime_kernel_top.AESL_inst_m89x_runtime_kernel
module m441_rtl_watchdog;
  longint requested[4], received[4], awaiting[4], address_stalls[4];
  longint output_stalls=0;
  integer i;
  wire [3:0] arvalid={`WGD.m_axi_w3_ARVALID,`WGD.m_axi_w2_ARVALID,`WGD.m_axi_w1_ARVALID,`WGD.m_axi_w0_ARVALID};
  wire [3:0] arready={`WGD.m_axi_w3_ARREADY,`WGD.m_axi_w2_ARREADY,`WGD.m_axi_w1_ARREADY,`WGD.m_axi_w0_ARREADY};
  wire [3:0] rvalid={`WGD.m_axi_w3_RVALID,`WGD.m_axi_w2_RVALID,`WGD.m_axi_w1_RVALID,`WGD.m_axi_w0_RVALID};
  wire [3:0] rready={`WGD.m_axi_w3_RREADY,`WGD.m_axi_w2_RREADY,`WGD.m_axi_w1_RREADY,`WGD.m_axi_w0_RREADY};
  wire [7:0] arlen[4];
  assign arlen[0]=`WGD.m_axi_w0_ARLEN;
  assign arlen[1]=`WGD.m_axi_w1_ARLEN;
  assign arlen[2]=`WGD.m_axi_w2_ARLEN;
  assign arlen[3]=`WGD.m_axi_w3_ARLEN;
  initial begin
    for(i=0;i<4;i=i+1)begin requested[i]=0;received[i]=0;awaiting[i]=0;address_stalls[i]=0;end
    if($test$plusargs("M441MAX_EXPECT_TIMEOUT"))begin
      wait(`WGD.ap_start===1'b1);
      repeat(200) @(posedge `WGD.ap_clk);
      if(`WGD.ap_done!==1'b1)begin
        $display("M441MAX_RTL_TIMEOUT_TRIGGERED ap_done=0 budget_cycles=200");
        $fatal(1,"M441MAX bounded timeout expired before ap_done");
      end else $fatal(1,"M441MAX timeout negative unexpectedly completed");
    end
  end
  always @(posedge `WGD.ap_clk)begin
    for(i=0;i<4;i=i+1)begin
      if(arvalid[i]&&arready[i])requested[i]=requested[i]+arlen[i]+1;
      if(rvalid[i]&&rready[i])received[i]=received[i]+1;
      if(arvalid[i]&&!arready[i])address_stalls[i]=address_stalls[i]+1;
      if(requested[i]>received[i]&&rready[i]&&!rvalid[i])awaiting[i]=awaiting[i]+1;
      if(received[i]>requested[i])$fatal(1,"M441MAX unexpected weight R beat without outstanding AR");
    end
    if(`WGD.rx_TVALID&&!`WGD.rx_TREADY)output_stalls=output_stalls+1;
    if(`WGD.ap_done)begin
      $display("M441MAX_OUTPUT_HELD_VALID_CYCLES=%0d",output_stalls);
      for(i=0;i<4;i=i+1)$display("M441MAX_AXI_METRICS shard=%0d requested=%0d received=%0d awaiting_with_pending=%0d address_stalls=%0d",i,requested[i],received[i],awaiting[i],address_stalls[i]);
    end
  end
endmodule
