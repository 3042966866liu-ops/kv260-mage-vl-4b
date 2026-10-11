`timescale 1ns/1ps
`define D apatb_m89x_runtime_kernel_top.AESL_inst_m89x_runtime_kernel
module m438_monitor;
integer cyc=0,i,words=0,lasts=0;
longint active[4],addr_phase[4],data_phase[4],addr_wait[4],data_wait[4],mac_phase[4],other[4];
longint calls[4],iterations[4],ar[4],rr[4],burst[4],ar_mac[4],r_mac[4],internal_ar_mac[4];
reg [3:0] live=0,old_start=0;
wire [3:0] start,done,iter;
wire [3:0] adr,dat,mp,aw,dw,arok,rok,iar;
wire [7:0] lens[4];
initial for(i=0;i<4;i=i+1)begin
 active[i]=0;addr_phase[i]=0;data_phase[i]=0;addr_wait[i]=0;data_wait[i]=0;mac_phase[i]=0;other[i]=0;
 calls[i]=0;iterations[i]=0;ar[i]=0;rr[i]=0;burst[i]=0;ar_mac[i]=0;r_mac[i]=0;internal_ar_mac[i]=0;
end
assign adr[0] = `D.grp_m89x_four_fu_404.m89x_shard_U0.ap_CS_fsm_state11 | `D.grp_m89x_four_fu_404.m89x_shard_U0.ap_CS_fsm_state21 | `D.grp_m89x_four_fu_404.m89x_shard_U0.ap_CS_fsm_state22 | `D.grp_m89x_four_fu_404.m89x_shard_U0.ap_CS_fsm_state31 | `D.grp_m89x_four_fu_404.m89x_shard_U0.ap_CS_fsm_state32;
assign dat[0] = `D.grp_m89x_four_fu_404.m89x_shard_U0.ap_CS_fsm_state19 | `D.grp_m89x_four_fu_404.m89x_shard_U0.ap_CS_fsm_state29 | `D.grp_m89x_four_fu_404.m89x_shard_U0.ap_CS_fsm_state30 | `D.grp_m89x_four_fu_404.m89x_shard_U0.ap_CS_fsm_state39 | `D.grp_m89x_four_fu_404.m89x_shard_U0.ap_CS_fsm_state40;
assign mp[0]=`D.grp_m89x_four_fu_404.m89x_shard_U0.ap_CS_fsm_state54;
assign aw[0]=adr[0] && !`D.grp_m89x_four_fu_404.m89x_shard_U0.m_axi_w0_0_ARREADY;
assign dw[0]=dat[0] && !`D.grp_m89x_four_fu_404.m89x_shard_U0.m_axi_w0_0_RVALID;
assign start[0]=`D.grp_m89x_four_fu_404.m89x_shard_U0.grp_m89x_shard_Pipeline_VITIS_LOOP_80_6_fu_601_ap_start;
assign done[0]=`D.grp_m89x_four_fu_404.m89x_shard_U0.ap_done;
assign iter[0]=`D.grp_m89x_four_fu_404.m89x_shard_U0.grp_m89x_shard_Pipeline_VITIS_LOOP_80_6_fu_601.ap_enable_reg_pp0_iter0 && !`D.grp_m89x_four_fu_404.m89x_shard_U0.grp_m89x_shard_Pipeline_VITIS_LOOP_80_6_fu_601.icmp_ln80_fu_2557_p2 && !`D.grp_m89x_four_fu_404.m89x_shard_U0.grp_m89x_shard_Pipeline_VITIS_LOOP_80_6_fu_601.ap_block_pp0_stage0_subdone;
assign arok[0]=`D.m_axi_w0_ARVALID && `D.m_axi_w0_ARREADY;
assign rok[0]=`D.m_axi_w0_RVALID && `D.m_axi_w0_RREADY;
assign iar[0]=`D.grp_m89x_four_fu_404.m89x_shard_U0.m_axi_w0_0_ARVALID && `D.grp_m89x_four_fu_404.m89x_shard_U0.m_axi_w0_0_ARREADY;
assign lens[0]=`D.m_axi_w0_ARLEN;
always @(posedge `D.ap_clk)begin if(`D.grp_m89x_four_fu_404.m89x_shard_U0.ap_start)live[0]=1; if(`D.grp_m89x_four_fu_404.m89x_shard_U0.ap_done)live[0]=0; end
assign adr[1] = `D.grp_m89x_four_fu_404.m89x_shard_1_U0.ap_CS_fsm_state11 | `D.grp_m89x_four_fu_404.m89x_shard_1_U0.ap_CS_fsm_state21 | `D.grp_m89x_four_fu_404.m89x_shard_1_U0.ap_CS_fsm_state22 | `D.grp_m89x_four_fu_404.m89x_shard_1_U0.ap_CS_fsm_state31 | `D.grp_m89x_four_fu_404.m89x_shard_1_U0.ap_CS_fsm_state32;
assign dat[1] = `D.grp_m89x_four_fu_404.m89x_shard_1_U0.ap_CS_fsm_state19 | `D.grp_m89x_four_fu_404.m89x_shard_1_U0.ap_CS_fsm_state29 | `D.grp_m89x_four_fu_404.m89x_shard_1_U0.ap_CS_fsm_state30 | `D.grp_m89x_four_fu_404.m89x_shard_1_U0.ap_CS_fsm_state39 | `D.grp_m89x_four_fu_404.m89x_shard_1_U0.ap_CS_fsm_state40;
assign mp[1]=`D.grp_m89x_four_fu_404.m89x_shard_1_U0.ap_CS_fsm_state54;
assign aw[1]=adr[1] && !`D.grp_m89x_four_fu_404.m89x_shard_1_U0.m_axi_w1_0_ARREADY;
assign dw[1]=dat[1] && !`D.grp_m89x_four_fu_404.m89x_shard_1_U0.m_axi_w1_0_RVALID;
assign start[1]=`D.grp_m89x_four_fu_404.m89x_shard_1_U0.grp_m89x_shard_1_Pipeline_VITIS_LOOP_80_6_fu_601_ap_start;
assign done[1]=`D.grp_m89x_four_fu_404.m89x_shard_1_U0.ap_done;
assign iter[1]=`D.grp_m89x_four_fu_404.m89x_shard_1_U0.grp_m89x_shard_1_Pipeline_VITIS_LOOP_80_6_fu_601.ap_enable_reg_pp0_iter0 && !`D.grp_m89x_four_fu_404.m89x_shard_1_U0.grp_m89x_shard_1_Pipeline_VITIS_LOOP_80_6_fu_601.icmp_ln80_fu_2557_p2 && !`D.grp_m89x_four_fu_404.m89x_shard_1_U0.grp_m89x_shard_1_Pipeline_VITIS_LOOP_80_6_fu_601.ap_block_pp0_stage0_subdone;
assign arok[1]=`D.m_axi_w1_ARVALID && `D.m_axi_w1_ARREADY;
assign rok[1]=`D.m_axi_w1_RVALID && `D.m_axi_w1_RREADY;
assign iar[1]=`D.grp_m89x_four_fu_404.m89x_shard_1_U0.m_axi_w1_0_ARVALID && `D.grp_m89x_four_fu_404.m89x_shard_1_U0.m_axi_w1_0_ARREADY;
assign lens[1]=`D.m_axi_w1_ARLEN;
always @(posedge `D.ap_clk)begin if(`D.grp_m89x_four_fu_404.m89x_shard_1_U0.ap_start)live[1]=1; if(`D.grp_m89x_four_fu_404.m89x_shard_1_U0.ap_done)live[1]=0; end
assign adr[2] = `D.grp_m89x_four_fu_404.m89x_shard_2_U0.ap_CS_fsm_state11 | `D.grp_m89x_four_fu_404.m89x_shard_2_U0.ap_CS_fsm_state21 | `D.grp_m89x_four_fu_404.m89x_shard_2_U0.ap_CS_fsm_state22 | `D.grp_m89x_four_fu_404.m89x_shard_2_U0.ap_CS_fsm_state31 | `D.grp_m89x_four_fu_404.m89x_shard_2_U0.ap_CS_fsm_state32;
assign dat[2] = `D.grp_m89x_four_fu_404.m89x_shard_2_U0.ap_CS_fsm_state19 | `D.grp_m89x_four_fu_404.m89x_shard_2_U0.ap_CS_fsm_state29 | `D.grp_m89x_four_fu_404.m89x_shard_2_U0.ap_CS_fsm_state30 | `D.grp_m89x_four_fu_404.m89x_shard_2_U0.ap_CS_fsm_state39 | `D.grp_m89x_four_fu_404.m89x_shard_2_U0.ap_CS_fsm_state40;
assign mp[2]=`D.grp_m89x_four_fu_404.m89x_shard_2_U0.ap_CS_fsm_state54;
assign aw[2]=adr[2] && !`D.grp_m89x_four_fu_404.m89x_shard_2_U0.m_axi_w2_0_ARREADY;
assign dw[2]=dat[2] && !`D.grp_m89x_four_fu_404.m89x_shard_2_U0.m_axi_w2_0_RVALID;
assign start[2]=`D.grp_m89x_four_fu_404.m89x_shard_2_U0.grp_m89x_shard_2_Pipeline_VITIS_LOOP_80_6_fu_601_ap_start;
assign done[2]=`D.grp_m89x_four_fu_404.m89x_shard_2_U0.ap_done;
assign iter[2]=`D.grp_m89x_four_fu_404.m89x_shard_2_U0.grp_m89x_shard_2_Pipeline_VITIS_LOOP_80_6_fu_601.ap_enable_reg_pp0_iter0 && !`D.grp_m89x_four_fu_404.m89x_shard_2_U0.grp_m89x_shard_2_Pipeline_VITIS_LOOP_80_6_fu_601.icmp_ln80_fu_2557_p2 && !`D.grp_m89x_four_fu_404.m89x_shard_2_U0.grp_m89x_shard_2_Pipeline_VITIS_LOOP_80_6_fu_601.ap_block_pp0_stage0_subdone;
assign arok[2]=`D.m_axi_w2_ARVALID && `D.m_axi_w2_ARREADY;
assign rok[2]=`D.m_axi_w2_RVALID && `D.m_axi_w2_RREADY;
assign iar[2]=`D.grp_m89x_four_fu_404.m89x_shard_2_U0.m_axi_w2_0_ARVALID && `D.grp_m89x_four_fu_404.m89x_shard_2_U0.m_axi_w2_0_ARREADY;
assign lens[2]=`D.m_axi_w2_ARLEN;
always @(posedge `D.ap_clk)begin if(`D.grp_m89x_four_fu_404.m89x_shard_2_U0.ap_start)live[2]=1; if(`D.grp_m89x_four_fu_404.m89x_shard_2_U0.ap_done)live[2]=0; end
assign adr[3] = `D.grp_m89x_four_fu_404.m89x_shard_3_U0.ap_CS_fsm_state11 | `D.grp_m89x_four_fu_404.m89x_shard_3_U0.ap_CS_fsm_state21 | `D.grp_m89x_four_fu_404.m89x_shard_3_U0.ap_CS_fsm_state22 | `D.grp_m89x_four_fu_404.m89x_shard_3_U0.ap_CS_fsm_state31 | `D.grp_m89x_four_fu_404.m89x_shard_3_U0.ap_CS_fsm_state32;
assign dat[3] = `D.grp_m89x_four_fu_404.m89x_shard_3_U0.ap_CS_fsm_state19 | `D.grp_m89x_four_fu_404.m89x_shard_3_U0.ap_CS_fsm_state29 | `D.grp_m89x_four_fu_404.m89x_shard_3_U0.ap_CS_fsm_state30 | `D.grp_m89x_four_fu_404.m89x_shard_3_U0.ap_CS_fsm_state39 | `D.grp_m89x_four_fu_404.m89x_shard_3_U0.ap_CS_fsm_state40;
assign mp[3]=`D.grp_m89x_four_fu_404.m89x_shard_3_U0.ap_CS_fsm_state54;
assign aw[3]=adr[3] && !`D.grp_m89x_four_fu_404.m89x_shard_3_U0.m_axi_w3_0_ARREADY;
assign dw[3]=dat[3] && !`D.grp_m89x_four_fu_404.m89x_shard_3_U0.m_axi_w3_0_RVALID;
assign start[3]=`D.grp_m89x_four_fu_404.m89x_shard_3_U0.grp_m89x_shard_3_Pipeline_VITIS_LOOP_80_6_fu_601_ap_start;
assign done[3]=`D.grp_m89x_four_fu_404.m89x_shard_3_U0.ap_done;
assign iter[3]=`D.grp_m89x_four_fu_404.m89x_shard_3_U0.grp_m89x_shard_3_Pipeline_VITIS_LOOP_80_6_fu_601.ap_enable_reg_pp0_iter0 && !`D.grp_m89x_four_fu_404.m89x_shard_3_U0.grp_m89x_shard_3_Pipeline_VITIS_LOOP_80_6_fu_601.icmp_ln80_fu_2557_p2 && !`D.grp_m89x_four_fu_404.m89x_shard_3_U0.grp_m89x_shard_3_Pipeline_VITIS_LOOP_80_6_fu_601.ap_block_pp0_stage0_subdone;
assign arok[3]=`D.m_axi_w3_ARVALID && `D.m_axi_w3_ARREADY;
assign rok[3]=`D.m_axi_w3_RVALID && `D.m_axi_w3_RREADY;
assign iar[3]=`D.grp_m89x_four_fu_404.m89x_shard_3_U0.m_axi_w3_0_ARVALID && `D.grp_m89x_four_fu_404.m89x_shard_3_U0.m_axi_w3_0_ARREADY;
assign lens[3]=`D.m_axi_w3_ARLEN;
always @(posedge `D.ap_clk)begin if(`D.grp_m89x_four_fu_404.m89x_shard_3_U0.ap_start)live[3]=1; if(`D.grp_m89x_four_fu_404.m89x_shard_3_U0.ap_done)live[3]=0; end
always @(posedge `D.ap_clk)begin
 cyc=cyc+1;
 if(cyc>500000)$fatal(1,"M438 bounded RTL cycle budget exceeded");
 for(i=0;i<4;i=i+1)begin
  if(live[i])begin
   active[i]=active[i]+1;
   if(adr[i])addr_phase[i]=addr_phase[i]+1;
   else if(dat[i])data_phase[i]=data_phase[i]+1;
   else if(mp[i])mac_phase[i]=mac_phase[i]+1;
   else other[i]=other[i]+1;
   if(aw[i])addr_wait[i]=addr_wait[i]+1;
   if(dw[i])data_wait[i]=data_wait[i]+1;
  end
  if(start[i]&&!old_start[i])calls[i]=calls[i]+1;
  if(iter[i])iterations[i]=iterations[i]+1;
  if(arok[i])begin ar[i]=ar[i]+1;if(lens[i]!=0)burst[i]=burst[i]+1;if(mp[i])ar_mac[i]=ar_mac[i]+1;end
  if(rok[i])begin rr[i]=rr[i]+1;if(mp[i])r_mac[i]=r_mac[i]+1;end
  if(iar[i]&&mp[i])internal_ar_mac[i]=internal_ar_mac[i]+1;
 end
 old_start=start;
 if(`D.rx_TVALID&&`D.rx_TREADY)begin words=words+1;if(`D.rx_TLAST)lasts=lasts+1;end
 if(cyc%50000==0)$display("M438_HEARTBEAT cycle=%0d output=%0d",cyc,words);
 if(`D.ap_done)begin
  $display("M438_DONE cycles=%0d output=%0d tlast=%0d return=%0h",cyc,words,lasts,`D.ap_return);
  for(i=0;i<4;i=i+1)$display("M438_METRIC shard=%0d active=%0d address_phase=%0d data_phase=%0d address_wait=%0d data_wait=%0d mac_phase=%0d other=%0d mac_calls=%0d iterations=%0d AR=%0d R=%0d multi_beat=%0d AR_during_MAC=%0d R_during_MAC=%0d internal_AR_during_MAC=%0d",i,active[i],addr_phase[i],data_phase[i],addr_wait[i],data_wait[i],mac_phase[i],other[i],calls[i],iterations[i],ar[i],rr[i],burst[i],ar_mac[i],r_mac[i],internal_ar_mac[i]);
 end
end
endmodule
