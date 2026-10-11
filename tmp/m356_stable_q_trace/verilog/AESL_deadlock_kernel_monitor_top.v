`timescale 1 ns / 1 ps

module AESL_deadlock_kernel_monitor_top ( 
    input wire kernel_monitor_clock,
    input wire kernel_monitor_reset
);
wire [2:0] axis_block_sigs;
wire [7:0] inst_idle_sigs;
wire [1:0] inst_block_sigs;
wire kernel_block;

assign axis_block_sigs[0] = ~AESL_inst_m89x_runtime_kernel.grp_m89x_runtime_kernel_Pipeline_VITIS_LOOP_188_1_fu_279.tx_TDATA_blk_n;
assign axis_block_sigs[1] = ~AESL_inst_m89x_runtime_kernel.grp_m89s_load_fu_295.grp_m89s_load_Pipeline_VITIS_LOOP_23_1_VITIS_LOOP_23_2_VITIS_LOOP_23_3_fu_78.tx_TDATA_blk_n;
assign axis_block_sigs[2] = ~AESL_inst_m89x_runtime_kernel.grp_m89x_four_fu_313.m89x_merge_U0.rx_TDATA_blk_n;

assign inst_idle_sigs[0] = AESL_inst_m89x_runtime_kernel.grp_m89x_four_fu_313.m89x_four_Block_entry_x_0_rd_proc_U0.ap_idle;
assign inst_block_sigs[0] = (AESL_inst_m89x_runtime_kernel.grp_m89x_four_fu_313.m89x_four_Block_entry_x_0_rd_proc_U0.ap_done & ~AESL_inst_m89x_runtime_kernel.grp_m89x_four_fu_313.m89x_four_Block_entry_x_0_rd_proc_U0.ap_continue) | ~AESL_inst_m89x_runtime_kernel.grp_m89x_four_fu_313.m89x_four_Block_entry_x_0_rd_proc_U0.grp_m89x_shard_fu_156.grp_m89x_shard_Pipeline_VITIS_LOOP_95_7_VITIS_LOOP_96_8_fu_563.result_0_blk_n | ~AESL_inst_m89x_runtime_kernel.grp_m89x_four_fu_313.m89x_four_Block_entry_x_0_rd_proc_U0.grp_m89x_shard_1_fu_184.grp_m89x_shard_1_Pipeline_VITIS_LOOP_95_7_VITIS_LOOP_96_8_fu_563.result_1_blk_n | ~AESL_inst_m89x_runtime_kernel.grp_m89x_four_fu_313.m89x_four_Block_entry_x_0_rd_proc_U0.grp_m89x_shard_2_fu_208.grp_m89x_shard_2_Pipeline_VITIS_LOOP_95_7_VITIS_LOOP_96_8_fu_563.result_2_blk_n | ~AESL_inst_m89x_runtime_kernel.grp_m89x_four_fu_313.m89x_four_Block_entry_x_0_rd_proc_U0.grp_m89x_shard_3_fu_232.grp_m89x_shard_3_Pipeline_VITIS_LOOP_95_7_VITIS_LOOP_96_8_fu_563.result_3_blk_n;
assign inst_idle_sigs[1] = AESL_inst_m89x_runtime_kernel.grp_m89x_four_fu_313.m89x_merge_U0.ap_idle;
assign inst_block_sigs[1] = (AESL_inst_m89x_runtime_kernel.grp_m89x_four_fu_313.m89x_merge_U0.ap_done & ~AESL_inst_m89x_runtime_kernel.grp_m89x_four_fu_313.m89x_merge_U0.ap_continue) | ~AESL_inst_m89x_runtime_kernel.grp_m89x_four_fu_313.m89x_merge_U0.result_0_blk_n | ~AESL_inst_m89x_runtime_kernel.grp_m89x_four_fu_313.m89x_merge_U0.result_1_blk_n | ~AESL_inst_m89x_runtime_kernel.grp_m89x_four_fu_313.m89x_merge_U0.result_2_blk_n | ~AESL_inst_m89x_runtime_kernel.grp_m89x_four_fu_313.m89x_merge_U0.result_3_blk_n;

assign inst_idle_sigs[2] = 1'b0;
assign inst_idle_sigs[3] = AESL_inst_m89x_runtime_kernel.grp_m89x_runtime_kernel_Pipeline_VITIS_LOOP_188_1_fu_279.ap_idle;
assign inst_idle_sigs[4] = AESL_inst_m89x_runtime_kernel.grp_m89s_load_fu_295.ap_idle;
assign inst_idle_sigs[5] = AESL_inst_m89x_runtime_kernel.grp_m89s_load_fu_295.grp_m89s_load_Pipeline_VITIS_LOOP_23_1_VITIS_LOOP_23_2_VITIS_LOOP_23_3_fu_78.ap_idle;
assign inst_idle_sigs[6] = AESL_inst_m89x_runtime_kernel.grp_m89x_four_fu_313.ap_idle;
assign inst_idle_sigs[7] = AESL_inst_m89x_runtime_kernel.grp_m89x_four_fu_313.m89x_merge_U0.ap_idle;

AESL_deadlock_idx0_monitor AESL_deadlock_idx0_monitor_U (
    .clock(kernel_monitor_clock),
    .reset(kernel_monitor_reset),
    .axis_block_sigs(axis_block_sigs),
    .inst_idle_sigs(inst_idle_sigs),
    .inst_block_sigs(inst_block_sigs),
    .block(kernel_block)
);


initial begin : trigger_axis_deadlock
reg block_delay;
    block_delay = 0;
    while(1) begin
        @(posedge kernel_monitor_clock);
    if (kernel_block == 1'b1 && block_delay == 1'b0)
        block_delay = kernel_block;
    end
end

endmodule
