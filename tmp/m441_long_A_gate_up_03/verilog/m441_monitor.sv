`timescale 1ns/1ps
`define D apatb_m89x_runtime_kernel_top.AESL_inst_m89x_runtime_kernel
module m441_monitor;
longint tx_seen=0,rx_backpressure=0,tx_backpressure=0,ctrl_seen=0;
integer stagnant=0;
wire ctrl_activity=(`D.s_axi_control_AWVALID&&`D.s_axi_control_AWREADY)||
 (`D.s_axi_control_WVALID&&`D.s_axi_control_WREADY)||
 (`D.s_axi_control_BVALID&&`D.s_axi_control_BREADY)||
 (`D.s_axi_control_ARVALID&&`D.s_axi_control_ARREADY)||
 (`D.s_axi_control_RVALID&&`D.s_axi_control_RREADY);
task automatic progress_snapshot(input integer terminal_kind);
 $display("M441_PROGRESS cycle=%0d output=%0d tx=%0d rx_stall=%0d tx_stall=%0d ctrl=%0d stagnant=%0d terminal=%0d",cyc,words,tx_seen,rx_backpressure,tx_backpressure,ctrl_seen,stagnant,terminal_kind);
 for(integer j=0;j<4;j=j+1)
  $display("M441_PORT_PROGRESS cycle=%0d shard=%0d AR=%0d R=%0d pending=%0d gap=%0d ARSTALL=%0d RSTALL=%0d MAC=%0d iter=%0d qwrite=%0d qread=%0d qcount=%0d qhigh=%0d qfull=%0d live=%0d",cyc,j,ar[j],rr[j],tail[j]-head[j],gap[j],arstall[j],rstall[j],calls[j],iterations[j],queue_writes[j],queue_reads[j],qcount[j],queue_high[j],queue_full_cycles[j],live[j]);
endtask

integer cyc=0,i,words=0,lasts=0;

bit [524287:0] seen[4];
longint queue_writes[4],queue_reads[4],queue_full_cycles[4];
longint R_during_accepted_MAC[4];
longint ar_histogram[4][65];
integer queue_high[4];
wire [3:0] qwrite,qread,qfull;
wire [6:0] qcount[4];
function automatic bit allowed_word(input longint index);
 allowed_word=(index>=0 && index<43520) || (index>=43520 && index<87040) || (index>=87040 && index<130560) || (index>=130560 && index<174080) || (index>=174080 && index<206720) || (index>=206848 && index<250368) || (index>=250368 && index<293888) || (index>=293888 && index<337408) || (index>=337408 && index<380928) || (index>=380928 && index<413568);
endfunction
initial for(integer j=0;j<4;j=j+1)begin
 seen[j]='0;queue_writes[j]=0;queue_reads[j]=0;queue_full_cycles[j]=0;queue_high[j]=0;R_during_accepted_MAC[j]=0;
 for(integer k=0;k<65;k=k+1)ar_histogram[j][k]=0;
end
assign qwrite[0]=0;assign qread[0]=0;assign qfull[0]=0;assign qcount[0]=0;
assign qwrite[1]=0;assign qread[1]=0;assign qfull[1]=0;assign qcount[1]=0;
assign qwrite[2]=0;assign qread[2]=0;assign qfull[2]=0;assign qcount[2]=0;
assign qwrite[3]=0;assign qread[3]=0;assign qfull[3]=0;assign qcount[3]=0;

longint active[4],mac_busy[4],calls[4],iterations[4],ar[4],rr[4],gap[4],rstall[4],arstall[4],ar_mac[4],r_mac[4];
integer head[4],tail[4],remaining[4][512],badlast[4],badresp[4];
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
 cyc=cyc+1;if(cyc>80000000)begin progress_snapshot(2);$fatal(1,"M441 bounded RTL cycle budget exceeded"); end
 for(i=0;i<4;i=i+1)begin
  if(qwrite[i])queue_writes[i]=queue_writes[i]+1;
  if(qread[i])queue_reads[i]=queue_reads[i]+1;
  if(qfull[i])queue_full_cycles[i]=queue_full_cycles[i]+1;
  if(rok[i]&&iter[i])R_during_accepted_MAC[i]=R_during_accepted_MAC[i]+1;
  if(qcount[i]>queue_high[i])queue_high[i]=qcount[i];
  if(qcount[i]>34||queue_reads[i]>queue_writes[i]||queue_writes[i]-queue_reads[i]>34)begin progress_snapshot(2);$fatal(1,"M441 queue bound"); end
  if(live[i])begin active[i]=active[i]+1;if(busy[i])mac_busy[i]=mac_busy[i]+1;end
  if(start[i]&&!old_start[i])calls[i]=calls[i]+1;
  if(iter[i])iterations[i]=iterations[i]+1;
  if(tail[i]>head[i]&&rdready[i]&&!rdvalid[i])gap[i]=gap[i]+1;
  if(rdvalid[i]&&!rdready[i])rstall[i]=rstall[i]+1;
  if(avalid[i]&&!aready[i])arstall[i]=arstall[i]+1;
  if(arok[i])begin
   if(tail[i]-head[i]>=512)begin progress_snapshot(2);$fatal(1,"M441 address queue budget exceeded"); end
   remaining[i][tail[i]%512]=lens[i]+1;tail[i]=tail[i]+1;ar[i]=ar[i]+1;
   if(busy[i]&&live[i])ar_mac[i]=ar_mac[i]+1;
   if(lens[i]>63||(addresses[i][11:0]+(lens[i]+1)*16)>4096)begin progress_snapshot(2);$fatal(1,"M441 burst length/boundary"); end
   ar_histogram[i][lens[i]+1]=ar_histogram[i][lens[i]+1]+1;
   if(sizes[i]!=4||bursts[i]!=1||addresses[i][3:0]!=0)begin progress_snapshot(2);$fatal(1,"M441 bad address geometry"); end
   for(integer k=0;k<=lens[i];k=k+1)begin
    longint word_index;
    word_index=(addresses[i]>>4)+k;
    if(word_index>=524288||!allowed_word(word_index))begin progress_snapshot(2);$fatal(1,"M441 unexpected record address"); end
    if(seen[i][word_index])begin progress_snapshot(2);$fatal(1,"M441 duplicate record address"); end
    seen[i][word_index]=1;
   end
  end
  if(rok[i])begin
   if(head[i]>=tail[i])begin progress_snapshot(2);$fatal(1,"M441 return without recorded address"); end
   if(rlast[i]!=(remaining[i][head[i]%512]==1))badlast[i]=badlast[i]+1;
   if(resp[i]!=0)badresp[i]=badresp[i]+1;
   remaining[i][head[i]%512]=remaining[i][head[i]%512]-1;if(remaining[i][head[i]%512]==0)head[i]=head[i]+1;
   rr[i]=rr[i]+1;if(busy[i]&&live[i])r_mac[i]=r_mac[i]+1;
  end
 end

 if(`D.tx_TVALID&&`D.tx_TREADY)tx_seen=tx_seen+1;
 if(`D.rx_TVALID&&!`D.rx_TREADY)rx_backpressure=rx_backpressure+1;
 if(`D.tx_TVALID&&!`D.tx_TREADY)tx_backpressure=tx_backpressure+1;
 if(ctrl_activity)ctrl_seen=ctrl_seen+1;
 if((`D.tx_TVALID&&`D.tx_TREADY)||(`D.rx_TVALID&&`D.rx_TREADY)||
    (|arok)||(|rok)||(|iter)||(|(start&~old_start))||ctrl_activity||`D.ap_done)stagnant=0;
 else stagnant=stagnant+1;
 if(stagnant>=1000000)begin progress_snapshot(2);$fatal(1,"M441 global progress stalled for 1000000 cycles");end

 old_start=start;
 if(`D.rx_TVALID&&`D.rx_TREADY)begin words=words+1;if(`D.rx_TLAST)lasts=lasts+1;end
 if(cyc%50000==0)begin progress_snapshot(0);$display("M441_HEARTBEAT cycle=%0d output=%0d",cyc,words);end
 if(`D.ap_done)begin
 progress_snapshot(1);
  if(words!=311296||lasts!=1)begin progress_snapshot(2);$fatal(1,"M441 full output count/TLAST"); end
  for(integer j=0;j<4;j=j+1)begin
   if($countones(seen[j])!=413440||rr[j]!=413440||tail[j]!=head[j]||badlast[j]||badresp[j])begin progress_snapshot(2);$fatal(1,"M441 incomplete full address/R proof"); end
   if(calls[j]!=97280||iterations[j]!=1556480)begin progress_snapshot(2);$fatal(1,"M441 changed full MAC work"); end
   $display("M441_QUEUE shard=%0d writes=%0d reads=%0d high=%0d full_cycles=%0d final=%0d covered=%0d R_accepted_MAC=%0d",j,queue_writes[j],queue_reads[j],queue_high[j],queue_full_cycles[j],qcount[j],$countones(seen[j]),R_during_accepted_MAC[j]);
   for(integer k=1;k<65;k=k+1)if(ar_histogram[j][k])$display("M441_ARLEN shard=%0d beats=%0d requests=%0d",j,k,ar_histogram[j][k]);
  end

  $display("M441_DONE cycles=%0d output=%0d tlast=%0d",cyc,words,lasts);
  for(i=0;i<4;i=i+1)$display("M441_METRIC shard=%0d active=%0d mac_busy=%0d mac_calls=%0d iterations=%0d AR=%0d R=%0d return_gap=%0d RSTALL=%0d ARSTALL=%0d AR_during_MAC=%0d R_during_MAC=%0d pending=%0d bad_RLAST=%0d bad_RRESP=%0d",i,active[i],mac_busy[i],calls[i],iterations[i],ar[i],rr[i],gap[i],rstall[i],arstall[i],ar_mac[i],r_mac[i],tail[i]-head[i],badlast[i],badresp[i]);
 end
end
endmodule
