`timescale 1ns/1ps
`define D apatb_m89x_runtime_kernel_top.AESL_inst_m89x_runtime_kernel
module m439_monitor;
integer cyc=0,i,words=0,lasts=0;
longint active[4],mac_busy[4],calls[4],iterations[4],ar[4],rr[4],gap[4],rstall[4],arstall[4],ar_mac[4],r_mac[4];
integer head[4],tail[4],remaining[4][1024],badlast[4],badresp[4];
reg [3:0] live=0,old_start=0;
wire [3:0] start,iter,busy,arok,rok,rdvalid,rdready,avalid,aready,rlast;
wire [7:0] lens[4];wire [63:0] addresses[4];wire [2:0] sizes[4];wire [1:0] bursts[4],resp[4];
initial for(i=0;i<4;i=i+1)begin
 active[i]=0;mac_busy[i]=0;calls[i]=0;iterations[i]=0;ar[i]=0;rr[i]=0;gap[i]=0;rstall[i]=0;arstall[i]=0;ar_mac[i]=0;r_mac[i]=0;head[i]=0;tail[i]=0;badlast[i]=0;badresp[i]=0;
end
assign start[0]=`D.grp_m89x_four_fu_404.m89x_shard_U0.grp_m89x_shard_Pipeline_VITIS_LOOP_80_6_fu_601_ap_start;
assign iter[0]=`D.grp_m89x_four_fu_404.m89x_shard_U0.grp_m89x_shard_Pipeline_VITIS_LOOP_80_6_fu_601.ap_enable_reg_pp0_iter0 && !`D.grp_m89x_four_fu_404.m89x_shard_U0.grp_m89x_shard_Pipeline_VITIS_LOOP_80_6_fu_601.icmp_ln80_fu_2557_p2 && !`D.grp_m89x_four_fu_404.m89x_shard_U0.grp_m89x_shard_Pipeline_VITIS_LOOP_80_6_fu_601.ap_block_pp0_stage0_subdone;
assign busy[0]=!`D.grp_m89x_four_fu_404.m89x_shard_U0.grp_m89x_shard_Pipeline_VITIS_LOOP_80_6_fu_601.ap_idle;
assign arok[0]=`D.m_axi_w0_ARVALID && `D.m_axi_w0_ARREADY;
assign rok[0]=`D.m_axi_w0_RVALID && `D.m_axi_w0_RREADY;
assign lens[0]=`D.m_axi_w0_ARLEN; assign addresses[0]=`D.m_axi_w0_ARADDR;
assign sizes[0]=`D.m_axi_w0_ARSIZE;assign bursts[0]=`D.m_axi_w0_ARBURST;
assign rdvalid[0]=`D.m_axi_w0_RVALID;assign rdready[0]=`D.m_axi_w0_RREADY;
assign avalid[0]=`D.m_axi_w0_ARVALID;assign aready[0]=`D.m_axi_w0_ARREADY;
assign rlast[0]=`D.m_axi_w0_RLAST;assign resp[0]=`D.m_axi_w0_RRESP;
always @(posedge `D.ap_clk)begin if(`D.grp_m89x_four_fu_404.m89x_shard_U0.ap_start)live[0]=1;if(`D.grp_m89x_four_fu_404.m89x_shard_U0.ap_done)live[0]=0;end
assign start[1]=`D.grp_m89x_four_fu_404.m89x_shard_1_U0.grp_m89x_shard_1_Pipeline_VITIS_LOOP_80_6_fu_601_ap_start;
assign iter[1]=`D.grp_m89x_four_fu_404.m89x_shard_1_U0.grp_m89x_shard_1_Pipeline_VITIS_LOOP_80_6_fu_601.ap_enable_reg_pp0_iter0 && !`D.grp_m89x_four_fu_404.m89x_shard_1_U0.grp_m89x_shard_1_Pipeline_VITIS_LOOP_80_6_fu_601.icmp_ln80_fu_2557_p2 && !`D.grp_m89x_four_fu_404.m89x_shard_1_U0.grp_m89x_shard_1_Pipeline_VITIS_LOOP_80_6_fu_601.ap_block_pp0_stage0_subdone;
assign busy[1]=!`D.grp_m89x_four_fu_404.m89x_shard_1_U0.grp_m89x_shard_1_Pipeline_VITIS_LOOP_80_6_fu_601.ap_idle;
assign arok[1]=`D.m_axi_w1_ARVALID && `D.m_axi_w1_ARREADY;
assign rok[1]=`D.m_axi_w1_RVALID && `D.m_axi_w1_RREADY;
assign lens[1]=`D.m_axi_w1_ARLEN; assign addresses[1]=`D.m_axi_w1_ARADDR;
assign sizes[1]=`D.m_axi_w1_ARSIZE;assign bursts[1]=`D.m_axi_w1_ARBURST;
assign rdvalid[1]=`D.m_axi_w1_RVALID;assign rdready[1]=`D.m_axi_w1_RREADY;
assign avalid[1]=`D.m_axi_w1_ARVALID;assign aready[1]=`D.m_axi_w1_ARREADY;
assign rlast[1]=`D.m_axi_w1_RLAST;assign resp[1]=`D.m_axi_w1_RRESP;
always @(posedge `D.ap_clk)begin if(`D.grp_m89x_four_fu_404.m89x_shard_1_U0.ap_start)live[1]=1;if(`D.grp_m89x_four_fu_404.m89x_shard_1_U0.ap_done)live[1]=0;end
assign start[2]=`D.grp_m89x_four_fu_404.m89x_shard_2_U0.grp_m89x_shard_2_Pipeline_VITIS_LOOP_80_6_fu_601_ap_start;
assign iter[2]=`D.grp_m89x_four_fu_404.m89x_shard_2_U0.grp_m89x_shard_2_Pipeline_VITIS_LOOP_80_6_fu_601.ap_enable_reg_pp0_iter0 && !`D.grp_m89x_four_fu_404.m89x_shard_2_U0.grp_m89x_shard_2_Pipeline_VITIS_LOOP_80_6_fu_601.icmp_ln80_fu_2557_p2 && !`D.grp_m89x_four_fu_404.m89x_shard_2_U0.grp_m89x_shard_2_Pipeline_VITIS_LOOP_80_6_fu_601.ap_block_pp0_stage0_subdone;
assign busy[2]=!`D.grp_m89x_four_fu_404.m89x_shard_2_U0.grp_m89x_shard_2_Pipeline_VITIS_LOOP_80_6_fu_601.ap_idle;
assign arok[2]=`D.m_axi_w2_ARVALID && `D.m_axi_w2_ARREADY;
assign rok[2]=`D.m_axi_w2_RVALID && `D.m_axi_w2_RREADY;
assign lens[2]=`D.m_axi_w2_ARLEN; assign addresses[2]=`D.m_axi_w2_ARADDR;
assign sizes[2]=`D.m_axi_w2_ARSIZE;assign bursts[2]=`D.m_axi_w2_ARBURST;
assign rdvalid[2]=`D.m_axi_w2_RVALID;assign rdready[2]=`D.m_axi_w2_RREADY;
assign avalid[2]=`D.m_axi_w2_ARVALID;assign aready[2]=`D.m_axi_w2_ARREADY;
assign rlast[2]=`D.m_axi_w2_RLAST;assign resp[2]=`D.m_axi_w2_RRESP;
always @(posedge `D.ap_clk)begin if(`D.grp_m89x_four_fu_404.m89x_shard_2_U0.ap_start)live[2]=1;if(`D.grp_m89x_four_fu_404.m89x_shard_2_U0.ap_done)live[2]=0;end
assign start[3]=`D.grp_m89x_four_fu_404.m89x_shard_3_U0.grp_m89x_shard_3_Pipeline_VITIS_LOOP_80_6_fu_601_ap_start;
assign iter[3]=`D.grp_m89x_four_fu_404.m89x_shard_3_U0.grp_m89x_shard_3_Pipeline_VITIS_LOOP_80_6_fu_601.ap_enable_reg_pp0_iter0 && !`D.grp_m89x_four_fu_404.m89x_shard_3_U0.grp_m89x_shard_3_Pipeline_VITIS_LOOP_80_6_fu_601.icmp_ln80_fu_2557_p2 && !`D.grp_m89x_four_fu_404.m89x_shard_3_U0.grp_m89x_shard_3_Pipeline_VITIS_LOOP_80_6_fu_601.ap_block_pp0_stage0_subdone;
assign busy[3]=!`D.grp_m89x_four_fu_404.m89x_shard_3_U0.grp_m89x_shard_3_Pipeline_VITIS_LOOP_80_6_fu_601.ap_idle;
assign arok[3]=`D.m_axi_w3_ARVALID && `D.m_axi_w3_ARREADY;
assign rok[3]=`D.m_axi_w3_RVALID && `D.m_axi_w3_RREADY;
assign lens[3]=`D.m_axi_w3_ARLEN; assign addresses[3]=`D.m_axi_w3_ARADDR;
assign sizes[3]=`D.m_axi_w3_ARSIZE;assign bursts[3]=`D.m_axi_w3_ARBURST;
assign rdvalid[3]=`D.m_axi_w3_RVALID;assign rdready[3]=`D.m_axi_w3_RREADY;
assign avalid[3]=`D.m_axi_w3_ARVALID;assign aready[3]=`D.m_axi_w3_ARREADY;
assign rlast[3]=`D.m_axi_w3_RLAST;assign resp[3]=`D.m_axi_w3_RRESP;
always @(posedge `D.ap_clk)begin if(`D.grp_m89x_four_fu_404.m89x_shard_3_U0.ap_start)live[3]=1;if(`D.grp_m89x_four_fu_404.m89x_shard_3_U0.ap_done)live[3]=0;end
always @(posedge `D.ap_clk)begin
 cyc=cyc+1;if(cyc>500000)$fatal(1,"M439 bounded RTL cycle budget exceeded");
 for(i=0;i<4;i=i+1)begin
  if(live[i])begin active[i]=active[i]+1;if(busy[i])mac_busy[i]=mac_busy[i]+1;end
  if(start[i]&&!old_start[i])calls[i]=calls[i]+1;
  if(iter[i])iterations[i]=iterations[i]+1;
  if(tail[i]>head[i]&&rdready[i]&&!rdvalid[i])gap[i]=gap[i]+1;
  if(rdvalid[i]&&!rdready[i])rstall[i]=rstall[i]+1;
  if(avalid[i]&&!aready[i])arstall[i]=arstall[i]+1;
  if(arok[i])begin
   if(tail[i]>=1024)$fatal(1,"M439 address queue budget exceeded");
   remaining[i][tail[i]]=lens[i]+1;tail[i]=tail[i]+1;ar[i]=ar[i]+1;
   if(busy[i]&&live[i])ar_mac[i]=ar_mac[i]+1;
   $display("M439_AR shard=%0d address=%0h len=%0d size=%0d burst=%0d",i,addresses[i],lens[i],sizes[i],bursts[i]);
  end
  if(rok[i])begin
   if(head[i]>=tail[i])$fatal(1,"M439 return without recorded address");
   if(rlast[i]!=(remaining[i][head[i]]==1))badlast[i]=badlast[i]+1;
   if(resp[i]!=0)badresp[i]=badresp[i]+1;
   remaining[i][head[i]]=remaining[i][head[i]]-1;if(remaining[i][head[i]]==0)head[i]=head[i]+1;
   rr[i]=rr[i]+1;if(busy[i]&&live[i])r_mac[i]=r_mac[i]+1;
  end
 end
 old_start=start;
 if(`D.rx_TVALID&&`D.rx_TREADY)begin words=words+1;if(`D.rx_TLAST)lasts=lasts+1;end
 if(cyc%50000==0)$display("M439_HEARTBEAT cycle=%0d output=%0d",cyc,words);
 if(`D.ap_done)begin
  $display("M439_DONE cycles=%0d output=%0d tlast=%0d",cyc,words,lasts);
  for(i=0;i<4;i=i+1)$display("M439_METRIC shard=%0d active=%0d mac_busy=%0d mac_calls=%0d iterations=%0d AR=%0d R=%0d return_gap=%0d RSTALL=%0d ARSTALL=%0d AR_during_MAC=%0d R_during_MAC=%0d pending=%0d bad_RLAST=%0d bad_RRESP=%0d",i,active[i],mac_busy[i],calls[i],iterations[i],ar[i],rr[i],gap[i],rstall[i],arstall[i],ar_mac[i],r_mac[i],tail[i]-head[i],badlast[i],badresp[i]);
 end
end
endmodule
