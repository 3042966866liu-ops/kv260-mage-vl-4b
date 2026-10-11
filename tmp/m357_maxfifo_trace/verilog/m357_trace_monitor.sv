`timescale 1ns/1ps
`define D apatb_m89x_runtime_kernel_top.AESL_inst_m89x_runtime_kernel
`define F `D.grp_m89x_four_fu_404
`define P `F
module m357_trace_monitor;
  integer fileh, cyc=0, active_mask=0, overlap=0, outwords=0, lasts=0;
  integer arcount[4], rcount[4], rstall[4], maxfifo[4];
  reg [3:0] starts_old=0, dones_old=0;
  wire [3:0] starts={`P.m89x_shard_3_U0_ap_start,`P.m89x_shard_2_U0_ap_start,`P.m89x_shard_1_U0_ap_start,`P.m89x_shard_U0_ap_start};
  wire [3:0] dones={`P.m89x_shard_3_U0_ap_done,`P.m89x_shard_2_U0_ap_done,`P.m89x_shard_1_U0_ap_done,`P.m89x_shard_U0_ap_done};
  wire [3:0] ars={`D.m_axi_w3_ARVALID&&`D.m_axi_w3_ARREADY,`D.m_axi_w2_ARVALID&&`D.m_axi_w2_ARREADY,`D.m_axi_w1_ARVALID&&`D.m_axi_w1_ARREADY,`D.m_axi_w0_ARVALID&&`D.m_axi_w0_ARREADY};
  wire [3:0] rs={`D.m_axi_w3_RVALID&&`D.m_axi_w3_RREADY,`D.m_axi_w2_RVALID&&`D.m_axi_w2_RREADY,`D.m_axi_w1_RVALID&&`D.m_axi_w1_RREADY,`D.m_axi_w0_RVALID&&`D.m_axi_w0_RREADY};
  wire [3:0] stalls={`D.m_axi_w3_RVALID&&!`D.m_axi_w3_RREADY,`D.m_axi_w2_RVALID&&!`D.m_axi_w2_RREADY,`D.m_axi_w1_RVALID&&!`D.m_axi_w1_RREADY,`D.m_axi_w0_RVALID&&!`D.m_axi_w0_RREADY};
  wire [31:0] fifo[4];
  assign fifo[0]=`F.result_num_data_valid;
  assign fifo[1]=`F.result_1_num_data_valid;
  assign fifo[2]=`F.result_2_num_data_valid;
  assign fifo[3]=`F.result_3_num_data_valid;
  integer i;
  initial begin
    fileh=$fopen("m357_trace.csv","w");
    $fwrite(fileh,"cycle,event,shard,value\n");
    for(i=0;i<4;i=i+1)begin arcount[i]=0;rcount[i]=0;rstall[i]=0;maxfifo[i]=0;end
  end
  always @(posedge `D.ap_clk) begin
    cyc=cyc+1;
    if(cyc%500000==0)begin $fflush(fileh);$display("M357_TRACE_HEARTBEAT cycle=%0d words=%0d",cyc,outwords);end
    for(i=0;i<4;i=i+1)begin
      if(starts[i]&&!starts_old[i])begin active_mask=active_mask|(1<<i);$fwrite(fileh,"%0d,start,%0d,0\n",cyc,i);end
      if(dones[i]&&!dones_old[i])begin active_mask=active_mask&~(1<<i);$fwrite(fileh,"%0d,done,%0d,0\n",cyc,i);end
      if(ars[i])arcount[i]=arcount[i]+1;
      if(rs[i])rcount[i]=rcount[i]+1;
      if(stalls[i])rstall[i]=rstall[i]+1;
      if(fifo[i]>maxfifo[i])maxfifo[i]=fifo[i];
    end
    starts_old=starts;dones_old=dones;
    if(active_mask!=0 && (active_mask&(active_mask-1))!=0)overlap=overlap+1;
    if(`D.rx_TVALID&&`D.rx_TREADY)begin
      outwords=outwords+1;
      if(outwords==1)$fwrite(fileh,"%0d,first_output,-1,0\n",cyc);
      if(`D.rx_TLAST)begin lasts=lasts+1;$fwrite(fileh,"%0d,tlast,-1,%0d\n",cyc,outwords);end
    end
    if(`D.ap_done)begin
      $fwrite(fileh,"%0d,ap_done,-1,%0d\n",cyc,outwords);
      $display("M357_TRACE_DONE cycles=%0d output=%0d tlast=%0d overlap_cycles=%0d",cyc,outwords,lasts,overlap);
      for(i=0;i<4;i=i+1)$display("M357_SHARD i=%0d AR=%0d R=%0d RSTALL=%0d FIFO_MAX=%0d",i,arcount[i],rcount[i],rstall[i],maxfifo[i]);
      $fflush(fileh);
    end
  end
endmodule
