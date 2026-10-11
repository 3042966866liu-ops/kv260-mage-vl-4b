`timescale 1ns/1ps
`define D apatb_m89x_runtime_kernel_top.AESL_inst_m89x_runtime_kernel
module m441_max_monitor;
bit tail_block=0;
integer expected_words,expected_reads,expected_calls,expected_descs,cycle_budget;
initial begin
 if(!$value$plusargs("WORDS=%d",expected_words)||!$value$plusargs("READS=%d",expected_reads)||
    !$value$plusargs("CALLS=%d",expected_calls)||!$value$plusargs("DESCS=%d",expected_descs)||
    !$value$plusargs("CYCLES=%d",cycle_budget))$fatal(1,"Missing frozen case contract");
end
longint accepted_overlap[4];
initial for(integer j=0;j<4;j=j+1)accepted_overlap[j]=0;

integer tail_hold_valid_cycles=0;
bit tail_armed=0,tail_released=0;
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
wire [3:0] shard_start,qwrite,qread,qfull;
wire [13:0] occupancy[4];wire [6:0] qcount[4];
reg [3:0] old_shard_start=0,old_AR_stall=0;
reg previous_output_stall=0;
reg [63:0] held_output,held_address[4];
reg [7:0] held_keep,held_strb,held_length[4];
reg held_last;reg [2:0] held_size[4];reg [1:0] held_burst[4];
longint descs[4],fifo_max[4],queue_writes[4],queue_reads[4],queue_full_cycles[4];
longint held=0,stable_output_stall_cycles=0,stable_AR_stall_cycles[4];
integer queue_high[4];
initial for(integer j=0;j<4;j=j+1)begin
 descs[j]=0;fifo_max[j]=0;queue_writes[j]=0;queue_reads[j]=0;queue_full_cycles[j]=0;queue_high[j]=0;stable_AR_stall_cycles[j]=0;
end
assign shard_start[0]=`D.grp_m89x_four_fu_404.m89x_shard_U0.ap_start;
assign occupancy[0]=`D.grp_m89x_four_fu_404.result_num_data_valid;
assign qwrite[0]=`D.grp_m89x_four_fu_404.m89x_shard_U0.records_U.if_write && `D.grp_m89x_four_fu_404.m89x_shard_U0.records_U.if_write_ce && `D.grp_m89x_four_fu_404.m89x_shard_U0.records_U.if_full_n;
assign qread[0]=`D.grp_m89x_four_fu_404.m89x_shard_U0.records_U.if_read && `D.grp_m89x_four_fu_404.m89x_shard_U0.records_U.if_read_ce && `D.grp_m89x_four_fu_404.m89x_shard_U0.records_U.if_empty_n;
assign qfull[0]=!`D.grp_m89x_four_fu_404.m89x_shard_U0.records_U.if_full_n;
assign qcount[0]=`D.grp_m89x_four_fu_404.m89x_shard_U0.records_U.if_num_data_valid;
assign shard_start[1]=`D.grp_m89x_four_fu_404.m89x_shard_4_U0.ap_start;
assign occupancy[1]=`D.grp_m89x_four_fu_404.result_1_num_data_valid;
assign qwrite[1]=`D.grp_m89x_four_fu_404.m89x_shard_4_U0.records_U.if_write && `D.grp_m89x_four_fu_404.m89x_shard_4_U0.records_U.if_write_ce && `D.grp_m89x_four_fu_404.m89x_shard_4_U0.records_U.if_full_n;
assign qread[1]=`D.grp_m89x_four_fu_404.m89x_shard_4_U0.records_U.if_read && `D.grp_m89x_four_fu_404.m89x_shard_4_U0.records_U.if_read_ce && `D.grp_m89x_four_fu_404.m89x_shard_4_U0.records_U.if_empty_n;
assign qfull[1]=!`D.grp_m89x_four_fu_404.m89x_shard_4_U0.records_U.if_full_n;
assign qcount[1]=`D.grp_m89x_four_fu_404.m89x_shard_4_U0.records_U.if_num_data_valid;
assign shard_start[2]=`D.grp_m89x_four_fu_404.m89x_shard_5_U0.ap_start;
assign occupancy[2]=`D.grp_m89x_four_fu_404.result_2_num_data_valid;
assign qwrite[2]=`D.grp_m89x_four_fu_404.m89x_shard_5_U0.records_U.if_write && `D.grp_m89x_four_fu_404.m89x_shard_5_U0.records_U.if_write_ce && `D.grp_m89x_four_fu_404.m89x_shard_5_U0.records_U.if_full_n;
assign qread[2]=`D.grp_m89x_four_fu_404.m89x_shard_5_U0.records_U.if_read && `D.grp_m89x_four_fu_404.m89x_shard_5_U0.records_U.if_read_ce && `D.grp_m89x_four_fu_404.m89x_shard_5_U0.records_U.if_empty_n;
assign qfull[2]=!`D.grp_m89x_four_fu_404.m89x_shard_5_U0.records_U.if_full_n;
assign qcount[2]=`D.grp_m89x_four_fu_404.m89x_shard_5_U0.records_U.if_num_data_valid;
assign shard_start[3]=`D.grp_m89x_four_fu_404.m89x_shard_6_U0.ap_start;
assign occupancy[3]=`D.grp_m89x_four_fu_404.result_3_num_data_valid;
assign qwrite[3]=`D.grp_m89x_four_fu_404.m89x_shard_6_U0.records_U.if_write && `D.grp_m89x_four_fu_404.m89x_shard_6_U0.records_U.if_write_ce && `D.grp_m89x_four_fu_404.m89x_shard_6_U0.records_U.if_full_n;
assign qread[3]=`D.grp_m89x_four_fu_404.m89x_shard_6_U0.records_U.if_read && `D.grp_m89x_four_fu_404.m89x_shard_6_U0.records_U.if_read_ce && `D.grp_m89x_four_fu_404.m89x_shard_6_U0.records_U.if_empty_n;
assign qfull[3]=!`D.grp_m89x_four_fu_404.m89x_shard_6_U0.records_U.if_full_n;
assign qcount[3]=`D.grp_m89x_four_fu_404.m89x_shard_6_U0.records_U.if_num_data_valid;

longint active[4],mac_busy[4],calls[4],iterations[4],ar[4],rr[4],gap[4],rstall[4],arstall[4],ar_mac[4],r_mac[4];
integer head[4],tail[4],remaining[4][512],badlast[4],badresp[4];
reg [3:0] live=0,old_start=0;
wire [3:0] start,iter,busy,arok,rok,rdvalid,rdready,avalid,aready,rlast;
wire [7:0] lens[4];wire [63:0] addresses[4];wire [2:0] sizes[4];wire [1:0] bursts[4],resp[4];
initial for(i=0;i<4;i=i+1)begin
 active[i]=0;mac_busy[i]=0;calls[i]=0;iterations[i]=0;ar[i]=0;rr[i]=0;gap[i]=0;rstall[i]=0;arstall[i]=0;ar_mac[i]=0;r_mac[i]=0;head[i]=0;tail[i]=0;badlast[i]=0;badresp[i]=0;
end
assign start[0]=`D.grp_m89x_four_fu_404.m89x_shard_U0.m441_compute_U0.grp_m441_compute_Pipeline_VITIS_LOOP_106_7_fu_590_ap_start;
assign iter[0]=`D.grp_m89x_four_fu_404.m89x_shard_U0.m441_compute_U0.grp_m441_compute_Pipeline_VITIS_LOOP_106_7_fu_590.ap_enable_reg_pp0_iter0 && !`D.grp_m89x_four_fu_404.m89x_shard_U0.m441_compute_U0.grp_m441_compute_Pipeline_VITIS_LOOP_106_7_fu_590.icmp_ln106_fu_2557_p2 && !`D.grp_m89x_four_fu_404.m89x_shard_U0.m441_compute_U0.grp_m441_compute_Pipeline_VITIS_LOOP_106_7_fu_590.ap_block_pp0_stage0_subdone;
assign busy[0]=!`D.grp_m89x_four_fu_404.m89x_shard_U0.m441_compute_U0.grp_m441_compute_Pipeline_VITIS_LOOP_106_7_fu_590.ap_idle;
assign arok[0]=`D.m_axi_w0_ARVALID && `D.m_axi_w0_ARREADY;
assign rok[0]=`D.m_axi_w0_RVALID && `D.m_axi_w0_RREADY;
assign lens[0]=`D.m_axi_w0_ARLEN; assign addresses[0]=`D.m_axi_w0_ARADDR;
assign sizes[0]=`D.m_axi_w0_ARSIZE;assign bursts[0]=`D.m_axi_w0_ARBURST;
assign rdvalid[0]=`D.m_axi_w0_RVALID;assign rdready[0]=`D.m_axi_w0_RREADY;
assign avalid[0]=`D.m_axi_w0_ARVALID;assign aready[0]=`D.m_axi_w0_ARREADY;
assign rlast[0]=`D.m_axi_w0_RLAST;assign resp[0]=`D.m_axi_w0_RRESP;
always @(posedge `D.ap_clk)begin if(`D.grp_m89x_four_fu_404.m89x_shard_U0.m441_compute_U0.ap_start)live[0]=1;if(`D.grp_m89x_four_fu_404.m89x_shard_U0.m441_compute_U0.ap_done)live[0]=0;end
assign start[1]=`D.grp_m89x_four_fu_404.m89x_shard_4_U0.m441_compute_1_U0.grp_m441_compute_1_Pipeline_VITIS_LOOP_106_7_fu_590_ap_start;
assign iter[1]=`D.grp_m89x_four_fu_404.m89x_shard_4_U0.m441_compute_1_U0.grp_m441_compute_1_Pipeline_VITIS_LOOP_106_7_fu_590.ap_enable_reg_pp0_iter0 && !`D.grp_m89x_four_fu_404.m89x_shard_4_U0.m441_compute_1_U0.grp_m441_compute_1_Pipeline_VITIS_LOOP_106_7_fu_590.icmp_ln106_fu_2557_p2 && !`D.grp_m89x_four_fu_404.m89x_shard_4_U0.m441_compute_1_U0.grp_m441_compute_1_Pipeline_VITIS_LOOP_106_7_fu_590.ap_block_pp0_stage0_subdone;
assign busy[1]=!`D.grp_m89x_four_fu_404.m89x_shard_4_U0.m441_compute_1_U0.grp_m441_compute_1_Pipeline_VITIS_LOOP_106_7_fu_590.ap_idle;
assign arok[1]=`D.m_axi_w1_ARVALID && `D.m_axi_w1_ARREADY;
assign rok[1]=`D.m_axi_w1_RVALID && `D.m_axi_w1_RREADY;
assign lens[1]=`D.m_axi_w1_ARLEN; assign addresses[1]=`D.m_axi_w1_ARADDR;
assign sizes[1]=`D.m_axi_w1_ARSIZE;assign bursts[1]=`D.m_axi_w1_ARBURST;
assign rdvalid[1]=`D.m_axi_w1_RVALID;assign rdready[1]=`D.m_axi_w1_RREADY;
assign avalid[1]=`D.m_axi_w1_ARVALID;assign aready[1]=`D.m_axi_w1_ARREADY;
assign rlast[1]=`D.m_axi_w1_RLAST;assign resp[1]=`D.m_axi_w1_RRESP;
always @(posedge `D.ap_clk)begin if(`D.grp_m89x_four_fu_404.m89x_shard_4_U0.m441_compute_1_U0.ap_start)live[1]=1;if(`D.grp_m89x_four_fu_404.m89x_shard_4_U0.m441_compute_1_U0.ap_done)live[1]=0;end
assign start[2]=`D.grp_m89x_four_fu_404.m89x_shard_5_U0.m441_compute_2_U0.grp_m441_compute_2_Pipeline_VITIS_LOOP_106_7_fu_590_ap_start;
assign iter[2]=`D.grp_m89x_four_fu_404.m89x_shard_5_U0.m441_compute_2_U0.grp_m441_compute_2_Pipeline_VITIS_LOOP_106_7_fu_590.ap_enable_reg_pp0_iter0 && !`D.grp_m89x_four_fu_404.m89x_shard_5_U0.m441_compute_2_U0.grp_m441_compute_2_Pipeline_VITIS_LOOP_106_7_fu_590.icmp_ln106_fu_2557_p2 && !`D.grp_m89x_four_fu_404.m89x_shard_5_U0.m441_compute_2_U0.grp_m441_compute_2_Pipeline_VITIS_LOOP_106_7_fu_590.ap_block_pp0_stage0_subdone;
assign busy[2]=!`D.grp_m89x_four_fu_404.m89x_shard_5_U0.m441_compute_2_U0.grp_m441_compute_2_Pipeline_VITIS_LOOP_106_7_fu_590.ap_idle;
assign arok[2]=`D.m_axi_w2_ARVALID && `D.m_axi_w2_ARREADY;
assign rok[2]=`D.m_axi_w2_RVALID && `D.m_axi_w2_RREADY;
assign lens[2]=`D.m_axi_w2_ARLEN; assign addresses[2]=`D.m_axi_w2_ARADDR;
assign sizes[2]=`D.m_axi_w2_ARSIZE;assign bursts[2]=`D.m_axi_w2_ARBURST;
assign rdvalid[2]=`D.m_axi_w2_RVALID;assign rdready[2]=`D.m_axi_w2_RREADY;
assign avalid[2]=`D.m_axi_w2_ARVALID;assign aready[2]=`D.m_axi_w2_ARREADY;
assign rlast[2]=`D.m_axi_w2_RLAST;assign resp[2]=`D.m_axi_w2_RRESP;
always @(posedge `D.ap_clk)begin if(`D.grp_m89x_four_fu_404.m89x_shard_5_U0.m441_compute_2_U0.ap_start)live[2]=1;if(`D.grp_m89x_four_fu_404.m89x_shard_5_U0.m441_compute_2_U0.ap_done)live[2]=0;end
assign start[3]=`D.grp_m89x_four_fu_404.m89x_shard_6_U0.m441_compute_3_U0.grp_m441_compute_3_Pipeline_VITIS_LOOP_106_7_fu_590_ap_start;
assign iter[3]=`D.grp_m89x_four_fu_404.m89x_shard_6_U0.m441_compute_3_U0.grp_m441_compute_3_Pipeline_VITIS_LOOP_106_7_fu_590.ap_enable_reg_pp0_iter0 && !`D.grp_m89x_four_fu_404.m89x_shard_6_U0.m441_compute_3_U0.grp_m441_compute_3_Pipeline_VITIS_LOOP_106_7_fu_590.icmp_ln106_fu_2557_p2 && !`D.grp_m89x_four_fu_404.m89x_shard_6_U0.m441_compute_3_U0.grp_m441_compute_3_Pipeline_VITIS_LOOP_106_7_fu_590.ap_block_pp0_stage0_subdone;
assign busy[3]=!`D.grp_m89x_four_fu_404.m89x_shard_6_U0.m441_compute_3_U0.grp_m441_compute_3_Pipeline_VITIS_LOOP_106_7_fu_590.ap_idle;
assign arok[3]=`D.m_axi_w3_ARVALID && `D.m_axi_w3_ARREADY;
assign rok[3]=`D.m_axi_w3_RVALID && `D.m_axi_w3_RREADY;
assign lens[3]=`D.m_axi_w3_ARLEN; assign addresses[3]=`D.m_axi_w3_ARADDR;
assign sizes[3]=`D.m_axi_w3_ARSIZE;assign bursts[3]=`D.m_axi_w3_ARBURST;
assign rdvalid[3]=`D.m_axi_w3_RVALID;assign rdready[3]=`D.m_axi_w3_RREADY;
assign avalid[3]=`D.m_axi_w3_ARVALID;assign aready[3]=`D.m_axi_w3_ARREADY;
assign rlast[3]=`D.m_axi_w3_RLAST;assign resp[3]=`D.m_axi_w3_RRESP;
always @(posedge `D.ap_clk)begin if(`D.grp_m89x_four_fu_404.m89x_shard_6_U0.m441_compute_3_U0.ap_start)live[3]=1;if(`D.grp_m89x_four_fu_404.m89x_shard_6_U0.m441_compute_3_U0.ap_done)live[3]=0;end
always @(posedge `D.ap_clk)begin
 cyc=cyc+1;if(cyc>cycle_budget)begin progress_snapshot(2);$fatal(1,"M441MAX bounded RTL cycle budget exceeded"); end
 for(i=0;i<4;i=i+1)begin
  if(shard_start[i]&&!old_shard_start[i])descs[i]=descs[i]+1;
  if(occupancy[i]>8192)begin progress_snapshot(2);$fatal(1,"M441MAX output FIFO overflow"); end
  if(occupancy[i]>fifo_max[i])fifo_max[i]=occupancy[i];
  if(rok[i]&&iter[i])accepted_overlap[i]=accepted_overlap[i]+1;
  if(qwrite[i])queue_writes[i]=queue_writes[i]+1;
  if(qread[i])queue_reads[i]=queue_reads[i]+1;
  if(qfull[i])queue_full_cycles[i]=queue_full_cycles[i]+1;
  if(qcount[i]>queue_high[i])queue_high[i]=qcount[i];
  if(qcount[i]>34||queue_reads[i]>queue_writes[i]||queue_writes[i]-queue_reads[i]>34)begin progress_snapshot(2);$fatal(1,"M441MAX record queue bound"); end
  if(`D.ap_rst_n)begin
   if(old_AR_stall[i])begin
    if(!avalid[i]||addresses[i]!==held_address[i]||lens[i]!==held_length[i]||sizes[i]!==held_size[i]||bursts[i]!==held_burst[i])begin progress_snapshot(2);$fatal(1,"M441MAX unstable stalled AR"); end
    stable_AR_stall_cycles[i]=stable_AR_stall_cycles[i]+1;
   end
   old_AR_stall[i]=avalid[i]&&!aready[i];
   held_address[i]=addresses[i];held_length[i]=lens[i];held_size[i]=sizes[i];held_burst[i]=bursts[i];
  end else old_AR_stall[i]=0;
  if(live[i])begin active[i]=active[i]+1;if(busy[i])mac_busy[i]=mac_busy[i]+1;end
  if(start[i]&&!old_start[i])calls[i]=calls[i]+1;
  if(iter[i])iterations[i]=iterations[i]+1;
  if(tail[i]>head[i]&&rdready[i]&&!rdvalid[i])gap[i]=gap[i]+1;
  if(rdvalid[i]&&!rdready[i])rstall[i]=rstall[i]+1;
  if(avalid[i]&&!aready[i])arstall[i]=arstall[i]+1;
  if(arok[i])begin
   if(tail[i]-head[i]>=512)begin progress_snapshot(2);$fatal(1,"M441MAX address queue budget exceeded"); end
   remaining[i][tail[i]%512]=lens[i]+1;tail[i]=tail[i]+1;ar[i]=ar[i]+1;
   if(busy[i]&&live[i])ar_mac[i]=ar_mac[i]+1;
   $display("M441MAX_AR shard=%0d address=%0h len=%0d size=%0d burst=%0d",i,addresses[i],lens[i],sizes[i],bursts[i]);
  end
  if(rok[i])begin
   if(head[i]>=tail[i])begin progress_snapshot(2);$fatal(1,"M441MAX return without recorded address"); end
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
 old_shard_start=shard_start;
 if(`D.rx_TVALID&&!`D.rx_TREADY)held=held+1;
 if(`D.ap_rst_n)begin
  if(previous_output_stall)begin
   if(!`D.rx_TVALID||`D.rx_TDATA!==held_output||`D.rx_TKEEP!==held_keep||`D.rx_TSTRB!==held_strb||`D.rx_TLAST!==held_last)begin progress_snapshot(2);$fatal(1,"M441MAX unstable stalled output"); end
   stable_output_stall_cycles=stable_output_stall_cycles+1;
  end
  previous_output_stall=`D.rx_TVALID&&!`D.rx_TREADY;
  held_output=`D.rx_TDATA;held_keep=`D.rx_TKEEP;held_strb=`D.rx_TSTRB;held_last=`D.rx_TLAST;
 end else previous_output_stall=0;

 if(`D.rx_TVALID&&`D.rx_TREADY)begin words=words+1;if(`D.rx_TLAST)lasts=lasts+1;end
 if(cyc%10000==0)begin progress_snapshot(0);$display("M441MAX_HEARTBEAT cycle=%0d output=%0d",cyc,words);end
 if(`D.ap_done)begin
 progress_snapshot(1);
 if(tail_hold_valid_cycles!=128||!tail_released)begin progress_snapshot(2);$fatal(1,"M441 boundary final TLAST hold unproven");end
  if(words!=expected_words||lasts!=1)begin progress_snapshot(2);$fatal(1,"M441MAX output count/TLAST"); end
  $display("M441MAX_HELD_VALID=%0d STABLE_OUTPUT_CYCLES=%0d",held,stable_output_stall_cycles);
  for(integer j=0;j<4;j=j+1)begin
   if(descs[j]!=expected_descs||calls[j]!=expected_calls||iterations[j]!=expected_calls*16||rr[j]!=expected_reads||tail[j]!=head[j]||badlast[j]||badresp[j])begin progress_snapshot(2);$fatal(1,"M441MAX incomplete descriptor/MAC/R protocol"); end
   if(queue_writes[j]!=expected_reads||queue_reads[j]!=expected_reads||qcount[j]!=0||queue_high[j]!=34||queue_full_cycles[j]==0)begin progress_snapshot(2);$fatal(1,"M441MAX record FIFO incomplete"); end
   $display("M441MAX_PROTOCOL shard=%0d descriptors=%0d FIFO_MAX=%0d queue_writes=%0d queue_reads=%0d queue_high=%0d queue_full=%0d queue_final=%0d AR_STABLE=%0d",j,descs[j],fifo_max[j],queue_writes[j],queue_reads[j],queue_high[j],queue_full_cycles[j],qcount[j],stable_AR_stall_cycles[j]);
  end

  for(integer j=0;j<4;j=j+1)begin
   if(accepted_overlap[j]==0)$fatal(1,"No accepted MAC/read overlap");
   $display("M441C19_OVERLAP shard=%0d accepted=%0d",j,accepted_overlap[j]);
  end
  $display("M441MAX_DONE cycles=%0d output=%0d tlast=%0d",cyc,words,lasts);
  for(i=0;i<4;i=i+1)$display("M441MAX_METRIC shard=%0d active=%0d mac_busy=%0d mac_calls=%0d iterations=%0d AR=%0d R=%0d return_gap=%0d RSTALL=%0d ARSTALL=%0d AR_during_MAC=%0d R_during_MAC=%0d pending=%0d bad_RLAST=%0d bad_RRESP=%0d",i,active[i],mac_busy[i],calls[i],iterations[i],ar[i],rr[i],gap[i],rstall[i],arstall[i],ar_mac[i],r_mac[i],tail[i]-head[i],badlast[i],badresp[i]);
 end
end



always @(negedge `D.ap_clk)begin
 if(!tail_armed && words==expected_words-1)begin
  tail_block=1;tail_armed=1;
 end else if(tail_armed&&!tail_released&&`D.rx_TVALID&&`D.rx_TLAST)begin
  if(`D.rx_TREADY)$fatal(1,"held last ready not low");
  tail_hold_valid_cycles++;
  if(tail_hold_valid_cycles==128)begin
   tail_block=0;tail_released=1;
   $display("M441_BOUNDARY_LAST_HOLD valid_cycles=%0d accepted_before=%0d",tail_hold_valid_cycles,words);
  end
 end
end

endmodule
