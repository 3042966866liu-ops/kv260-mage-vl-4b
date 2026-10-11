// ==============================================================
// Vitis HLS - High-Level Synthesis from C, C++ and OpenCL v2026.1 (64-bit)
// Tool Version Limit: 2026.06
// Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
// Copyright 2022-2026 Advanced Micro Devices, Inc. All Rights Reserved.
// 
// ==============================================================
`timescale 1ns/1ps


`define AUTOTB_DUT      op01_decode_one_kernel
`define AUTOTB_DUT_INST AESL_inst_op01_decode_one_kernel
`define AUTOTB_TOP      apatb_op01_decode_one_kernel_top
`define AUTOTB_LAT_RESULT_FILE "op01_decode_one_kernel.result.lat.rb"
`define AUTOTB_PER_RESULT_TRANS_FILE "op01_decode_one_kernel.performance.result.transaction.xml"
`define AUTOTB_TOP_INST AESL_inst_apatb_op01_decode_one_kernel_top
`define AUTOTB_MAX_ALLOW_LATENCY  15000000
`define AUTOTB_CLOCK_PERIOD_DIV2 2.40

`define AESL_DEPTH_w0 1
`define AESL_DEPTH_w1 1
`define AESL_DEPTH_w2 1
`define AESL_DEPTH_w3 1
`define AESL_DEPTH_tx_V_data_V 1
`define AESL_DEPTH_tx_V_keep_V 1
`define AESL_DEPTH_tx_V_strb_V 1
`define AESL_DEPTH_tx_V_last_V 1
`define AESL_DEPTH_s0 1
`define AESL_DEPTH_s1 1
`define AESL_DEPTH_s2 1
`define AESL_DEPTH_s3 1
`define AESL_DEPTH_rx_V_data_V 1
`define AESL_DEPTH_rx_V_keep_V 1
`define AESL_DEPTH_rx_V_strb_V 1
`define AESL_DEPTH_rx_V_last_V 1
`define AESL_DEPTH_config_r 1
`define AUTOTB_TVIN_w0  "../tv/cdatafile/c.op01_decode_one_kernel.autotvin_w0.dat"
`define AUTOTB_TVIN_w1  "../tv/cdatafile/c.op01_decode_one_kernel.autotvin_w1.dat"
`define AUTOTB_TVIN_w2  "../tv/cdatafile/c.op01_decode_one_kernel.autotvin_w2.dat"
`define AUTOTB_TVIN_w3  "../tv/cdatafile/c.op01_decode_one_kernel.autotvin_w3.dat"
`define AUTOTB_TVIN_tx_V_data_V  "../tv/cdatafile/c.op01_decode_one_kernel.autotvin_tx_V_data_V.dat"
`define AUTOTB_TVIN_tx_V_keep_V  "../tv/cdatafile/c.op01_decode_one_kernel.autotvin_tx_V_keep_V.dat"
`define AUTOTB_TVIN_tx_V_strb_V  "../tv/cdatafile/c.op01_decode_one_kernel.autotvin_tx_V_strb_V.dat"
`define AUTOTB_TVIN_tx_V_last_V  "../tv/cdatafile/c.op01_decode_one_kernel.autotvin_tx_V_last_V.dat"
`define AUTOTB_TVIN_s0  "../tv/cdatafile/c.op01_decode_one_kernel.autotvin_s0.dat"
`define AUTOTB_TVIN_s1  "../tv/cdatafile/c.op01_decode_one_kernel.autotvin_s1.dat"
`define AUTOTB_TVIN_s2  "../tv/cdatafile/c.op01_decode_one_kernel.autotvin_s2.dat"
`define AUTOTB_TVIN_s3  "../tv/cdatafile/c.op01_decode_one_kernel.autotvin_s3.dat"
`define AUTOTB_TVIN_config_r  "../tv/cdatafile/c.op01_decode_one_kernel.autotvin_config_r.dat"
`define AUTOTB_TVIN_w0_out_wrapc  "../tv/rtldatafile/rtl.op01_decode_one_kernel.autotvin_w0.dat"
`define AUTOTB_TVIN_w1_out_wrapc  "../tv/rtldatafile/rtl.op01_decode_one_kernel.autotvin_w1.dat"
`define AUTOTB_TVIN_w2_out_wrapc  "../tv/rtldatafile/rtl.op01_decode_one_kernel.autotvin_w2.dat"
`define AUTOTB_TVIN_w3_out_wrapc  "../tv/rtldatafile/rtl.op01_decode_one_kernel.autotvin_w3.dat"
`define AUTOTB_TVIN_tx_V_data_V_out_wrapc  "../tv/rtldatafile/rtl.op01_decode_one_kernel.autotvin_tx_V_data_V.dat"
`define AUTOTB_TVIN_tx_V_keep_V_out_wrapc  "../tv/rtldatafile/rtl.op01_decode_one_kernel.autotvin_tx_V_keep_V.dat"
`define AUTOTB_TVIN_tx_V_strb_V_out_wrapc  "../tv/rtldatafile/rtl.op01_decode_one_kernel.autotvin_tx_V_strb_V.dat"
`define AUTOTB_TVIN_tx_V_last_V_out_wrapc  "../tv/rtldatafile/rtl.op01_decode_one_kernel.autotvin_tx_V_last_V.dat"
`define AUTOTB_TVIN_s0_out_wrapc  "../tv/rtldatafile/rtl.op01_decode_one_kernel.autotvin_s0.dat"
`define AUTOTB_TVIN_s1_out_wrapc  "../tv/rtldatafile/rtl.op01_decode_one_kernel.autotvin_s1.dat"
`define AUTOTB_TVIN_s2_out_wrapc  "../tv/rtldatafile/rtl.op01_decode_one_kernel.autotvin_s2.dat"
`define AUTOTB_TVIN_s3_out_wrapc  "../tv/rtldatafile/rtl.op01_decode_one_kernel.autotvin_s3.dat"
`define AUTOTB_TVIN_config_r_out_wrapc  "../tv/rtldatafile/rtl.op01_decode_one_kernel.autotvin_config_r.dat"
`define AUTOTB_TVOUT_rx_V_data_V  "../tv/cdatafile/c.op01_decode_one_kernel.autotvout_rx_V_data_V.dat"
`define AUTOTB_TVOUT_rx_V_keep_V  "../tv/cdatafile/c.op01_decode_one_kernel.autotvout_rx_V_keep_V.dat"
`define AUTOTB_TVOUT_rx_V_strb_V  "../tv/cdatafile/c.op01_decode_one_kernel.autotvout_rx_V_strb_V.dat"
`define AUTOTB_TVOUT_rx_V_last_V  "../tv/cdatafile/c.op01_decode_one_kernel.autotvout_rx_V_last_V.dat"
`define AUTOTB_TVOUT_ap_return  "../tv/cdatafile/c.op01_decode_one_kernel.autotvout_ap_return.dat"
`define AUTOTB_TVOUT_rx_V_data_V_out_wrapc  "../tv/rtldatafile/rtl.op01_decode_one_kernel.autotvout_rx_V_data_V.dat"
`define AUTOTB_TVOUT_rx_V_keep_V_out_wrapc  "../tv/rtldatafile/rtl.op01_decode_one_kernel.autotvout_rx_V_keep_V.dat"
`define AUTOTB_TVOUT_rx_V_strb_V_out_wrapc  "../tv/rtldatafile/rtl.op01_decode_one_kernel.autotvout_rx_V_strb_V.dat"
`define AUTOTB_TVOUT_rx_V_last_V_out_wrapc  "../tv/rtldatafile/rtl.op01_decode_one_kernel.autotvout_rx_V_last_V.dat"
`define AUTOTB_TVOUT_ap_return_out_wrapc  "../tv/rtldatafile/rtl.op01_decode_one_kernel.autotvout_ap_return.dat"
module `AUTOTB_TOP;

parameter AUTOTB_TRANSACTION_NUM = 4;
parameter PROGRESS_TIMEOUT = 10000000;
parameter LATENCY_ESTIMATION = 463850042;
parameter LENGTH_ap_return = 1;
parameter LENGTH_config_r = 1;
parameter LENGTH_rx_V_data_V = 32768;
parameter LENGTH_rx_V_keep_V = 32768;
parameter LENGTH_rx_V_last_V = 32768;
parameter LENGTH_rx_V_strb_V = 32768;
parameter LENGTH_s0 = 1;
parameter LENGTH_s1 = 1;
parameter LENGTH_s2 = 1;
parameter LENGTH_s3 = 1;
parameter LENGTH_tx_V_data_V = 170;
parameter LENGTH_tx_V_keep_V = 170;
parameter LENGTH_tx_V_last_V = 170;
parameter LENGTH_tx_V_strb_V = 170;
parameter LENGTH_w0 = 524288;
parameter LENGTH_w1 = 524288;
parameter LENGTH_w2 = 524288;
parameter LENGTH_w3 = 524288;

reg AESL_clock;
reg rst;
reg dut_rst;
reg start;
reg ce;
reg tb_continue;
wire AESL_start;
wire AESL_reset;
wire AESL_ce;
wire AESL_ready;
wire AESL_idle;
wire AESL_continue;
wire AESL_done;
reg AESL_done_delay = 0;
reg AESL_done_delay2 = 0;
reg AESL_ready_delay = 0;
wire ready;
wire ready_wire;
wire [7 : 0] control_AWADDR;
wire  control_AWVALID;
wire  control_AWREADY;
wire  control_WVALID;
wire  control_WREADY;
wire [31 : 0] control_WDATA;
wire [3 : 0] control_WSTRB;
wire [7 : 0] control_ARADDR;
wire  control_ARVALID;
wire  control_ARREADY;
wire  control_RVALID;
wire  control_RREADY;
wire [31 : 0] control_RDATA;
wire [1 : 0] control_RRESP;
wire  control_BVALID;
wire  control_BREADY;
wire [1 : 0] control_BRESP;
wire  control_INTERRUPT;
wire  w0_AWVALID;
wire  w0_AWREADY;
wire [63 : 0] w0_AWADDR;
wire [0 : 0] w0_AWID;
wire [7 : 0] w0_AWLEN;
wire [2 : 0] w0_AWSIZE;
wire [1 : 0] w0_AWBURST;
wire [1 : 0] w0_AWLOCK;
wire [3 : 0] w0_AWCACHE;
wire [2 : 0] w0_AWPROT;
wire [3 : 0] w0_AWQOS;
wire [3 : 0] w0_AWREGION;
wire [0 : 0] w0_AWUSER;
wire  w0_WVALID;
wire  w0_WREADY;
wire [127 : 0] w0_WDATA;
wire [15 : 0] w0_WSTRB;
wire  w0_WLAST;
wire [0 : 0] w0_WID;
wire [0 : 0] w0_WUSER;
wire  w0_ARVALID;
wire  w0_ARREADY;
wire [63 : 0] w0_ARADDR;
wire [0 : 0] w0_ARID;
wire [7 : 0] w0_ARLEN;
wire [2 : 0] w0_ARSIZE;
wire [1 : 0] w0_ARBURST;
wire [1 : 0] w0_ARLOCK;
wire [3 : 0] w0_ARCACHE;
wire [2 : 0] w0_ARPROT;
wire [3 : 0] w0_ARQOS;
wire [3 : 0] w0_ARREGION;
wire [0 : 0] w0_ARUSER;
wire  w0_RVALID;
wire  w0_RREADY;
wire [127 : 0] w0_RDATA;
wire  w0_RLAST;
wire [0 : 0] w0_RID;
wire [0 : 0] w0_RUSER;
wire [1 : 0] w0_RRESP;
wire  w0_BVALID;
wire  w0_BREADY;
wire [1 : 0] w0_BRESP;
wire [0 : 0] w0_BID;
wire [0 : 0] w0_BUSER;
wire  w1_AWVALID;
wire  w1_AWREADY;
wire [63 : 0] w1_AWADDR;
wire [0 : 0] w1_AWID;
wire [7 : 0] w1_AWLEN;
wire [2 : 0] w1_AWSIZE;
wire [1 : 0] w1_AWBURST;
wire [1 : 0] w1_AWLOCK;
wire [3 : 0] w1_AWCACHE;
wire [2 : 0] w1_AWPROT;
wire [3 : 0] w1_AWQOS;
wire [3 : 0] w1_AWREGION;
wire [0 : 0] w1_AWUSER;
wire  w1_WVALID;
wire  w1_WREADY;
wire [127 : 0] w1_WDATA;
wire [15 : 0] w1_WSTRB;
wire  w1_WLAST;
wire [0 : 0] w1_WID;
wire [0 : 0] w1_WUSER;
wire  w1_ARVALID;
wire  w1_ARREADY;
wire [63 : 0] w1_ARADDR;
wire [0 : 0] w1_ARID;
wire [7 : 0] w1_ARLEN;
wire [2 : 0] w1_ARSIZE;
wire [1 : 0] w1_ARBURST;
wire [1 : 0] w1_ARLOCK;
wire [3 : 0] w1_ARCACHE;
wire [2 : 0] w1_ARPROT;
wire [3 : 0] w1_ARQOS;
wire [3 : 0] w1_ARREGION;
wire [0 : 0] w1_ARUSER;
wire  w1_RVALID;
wire  w1_RREADY;
wire [127 : 0] w1_RDATA;
wire  w1_RLAST;
wire [0 : 0] w1_RID;
wire [0 : 0] w1_RUSER;
wire [1 : 0] w1_RRESP;
wire  w1_BVALID;
wire  w1_BREADY;
wire [1 : 0] w1_BRESP;
wire [0 : 0] w1_BID;
wire [0 : 0] w1_BUSER;
wire  w2_AWVALID;
wire  w2_AWREADY;
wire [63 : 0] w2_AWADDR;
wire [0 : 0] w2_AWID;
wire [7 : 0] w2_AWLEN;
wire [2 : 0] w2_AWSIZE;
wire [1 : 0] w2_AWBURST;
wire [1 : 0] w2_AWLOCK;
wire [3 : 0] w2_AWCACHE;
wire [2 : 0] w2_AWPROT;
wire [3 : 0] w2_AWQOS;
wire [3 : 0] w2_AWREGION;
wire [0 : 0] w2_AWUSER;
wire  w2_WVALID;
wire  w2_WREADY;
wire [127 : 0] w2_WDATA;
wire [15 : 0] w2_WSTRB;
wire  w2_WLAST;
wire [0 : 0] w2_WID;
wire [0 : 0] w2_WUSER;
wire  w2_ARVALID;
wire  w2_ARREADY;
wire [63 : 0] w2_ARADDR;
wire [0 : 0] w2_ARID;
wire [7 : 0] w2_ARLEN;
wire [2 : 0] w2_ARSIZE;
wire [1 : 0] w2_ARBURST;
wire [1 : 0] w2_ARLOCK;
wire [3 : 0] w2_ARCACHE;
wire [2 : 0] w2_ARPROT;
wire [3 : 0] w2_ARQOS;
wire [3 : 0] w2_ARREGION;
wire [0 : 0] w2_ARUSER;
wire  w2_RVALID;
wire  w2_RREADY;
wire [127 : 0] w2_RDATA;
wire  w2_RLAST;
wire [0 : 0] w2_RID;
wire [0 : 0] w2_RUSER;
wire [1 : 0] w2_RRESP;
wire  w2_BVALID;
wire  w2_BREADY;
wire [1 : 0] w2_BRESP;
wire [0 : 0] w2_BID;
wire [0 : 0] w2_BUSER;
wire  w3_AWVALID;
wire  w3_AWREADY;
wire [63 : 0] w3_AWADDR;
wire [0 : 0] w3_AWID;
wire [7 : 0] w3_AWLEN;
wire [2 : 0] w3_AWSIZE;
wire [1 : 0] w3_AWBURST;
wire [1 : 0] w3_AWLOCK;
wire [3 : 0] w3_AWCACHE;
wire [2 : 0] w3_AWPROT;
wire [3 : 0] w3_AWQOS;
wire [3 : 0] w3_AWREGION;
wire [0 : 0] w3_AWUSER;
wire  w3_WVALID;
wire  w3_WREADY;
wire [127 : 0] w3_WDATA;
wire [15 : 0] w3_WSTRB;
wire  w3_WLAST;
wire [0 : 0] w3_WID;
wire [0 : 0] w3_WUSER;
wire  w3_ARVALID;
wire  w3_ARREADY;
wire [63 : 0] w3_ARADDR;
wire [0 : 0] w3_ARID;
wire [7 : 0] w3_ARLEN;
wire [2 : 0] w3_ARSIZE;
wire [1 : 0] w3_ARBURST;
wire [1 : 0] w3_ARLOCK;
wire [3 : 0] w3_ARCACHE;
wire [2 : 0] w3_ARPROT;
wire [3 : 0] w3_ARQOS;
wire [3 : 0] w3_ARREGION;
wire [0 : 0] w3_ARUSER;
wire  w3_RVALID;
wire  w3_RREADY;
wire [127 : 0] w3_RDATA;
wire  w3_RLAST;
wire [0 : 0] w3_RID;
wire [0 : 0] w3_RUSER;
wire [1 : 0] w3_RRESP;
wire  w3_BVALID;
wire  w3_BREADY;
wire [1 : 0] w3_BRESP;
wire [0 : 0] w3_BID;
wire [0 : 0] w3_BUSER;
wire [127 : 0] tx_TDATA;
wire  tx_TVALID;
wire  tx_TREADY;
wire [15 : 0] tx_TKEEP;
wire [15 : 0] tx_TSTRB;
wire [0 : 0] tx_TLAST;
wire [63 : 0] rx_TDATA;
wire  rx_TVALID;
wire  rx_TREADY;
wire [7 : 0] rx_TKEEP;
wire [7 : 0] rx_TSTRB;
wire [0 : 0] rx_TLAST;
integer done_cnt = 0;
integer AESL_ready_cnt = 0;
integer ready_cnt = 0;
reg ready_initial;
reg ready_initial_n;
reg ready_last_n;
reg ready_delay_last_n;
reg done_delay_last_n;
reg interface_done = 0;
wire control_read_data_finish;
wire control_write_data_finish;
wire AESL_slave_start;
reg AESL_slave_start_lock = 0;
wire AESL_slave_write_start_in;
wire AESL_slave_write_start_finish;
reg AESL_slave_ready;
wire AESL_slave_output_done;
wire AESL_slave_done;
reg ready_rise = 0;
reg start_rise = 0;
reg slave_start_status = 0;
reg slave_done_status = 0;
reg ap_done_lock = 0;


wire all_finish;
wire ap_clk;
wire ap_rst_n;
wire ap_rst_n_n;

`AUTOTB_DUT `AUTOTB_DUT_INST(
    .s_axi_control_AWADDR(control_AWADDR),
    .s_axi_control_AWVALID(control_AWVALID),
    .s_axi_control_AWREADY(control_AWREADY),
    .s_axi_control_WVALID(control_WVALID),
    .s_axi_control_WREADY(control_WREADY),
    .s_axi_control_WDATA(control_WDATA),
    .s_axi_control_WSTRB(control_WSTRB),
    .s_axi_control_ARADDR(control_ARADDR),
    .s_axi_control_ARVALID(control_ARVALID),
    .s_axi_control_ARREADY(control_ARREADY),
    .s_axi_control_RVALID(control_RVALID),
    .s_axi_control_RREADY(control_RREADY),
    .s_axi_control_RDATA(control_RDATA),
    .s_axi_control_RRESP(control_RRESP),
    .s_axi_control_BVALID(control_BVALID),
    .s_axi_control_BREADY(control_BREADY),
    .s_axi_control_BRESP(control_BRESP),
    .interrupt(control_INTERRUPT),
    .ap_clk(ap_clk),
    .ap_rst_n(ap_rst_n),
    .m_axi_w0_AWVALID(w0_AWVALID),
    .m_axi_w0_AWREADY(w0_AWREADY),
    .m_axi_w0_AWADDR(w0_AWADDR),
    .m_axi_w0_AWID(w0_AWID),
    .m_axi_w0_AWLEN(w0_AWLEN),
    .m_axi_w0_AWSIZE(w0_AWSIZE),
    .m_axi_w0_AWBURST(w0_AWBURST),
    .m_axi_w0_AWLOCK(w0_AWLOCK),
    .m_axi_w0_AWCACHE(w0_AWCACHE),
    .m_axi_w0_AWPROT(w0_AWPROT),
    .m_axi_w0_AWQOS(w0_AWQOS),
    .m_axi_w0_AWREGION(w0_AWREGION),
    .m_axi_w0_AWUSER(w0_AWUSER),
    .m_axi_w0_WVALID(w0_WVALID),
    .m_axi_w0_WREADY(w0_WREADY),
    .m_axi_w0_WDATA(w0_WDATA),
    .m_axi_w0_WSTRB(w0_WSTRB),
    .m_axi_w0_WLAST(w0_WLAST),
    .m_axi_w0_WID(w0_WID),
    .m_axi_w0_WUSER(w0_WUSER),
    .m_axi_w0_ARVALID(w0_ARVALID),
    .m_axi_w0_ARREADY(w0_ARREADY),
    .m_axi_w0_ARADDR(w0_ARADDR),
    .m_axi_w0_ARID(w0_ARID),
    .m_axi_w0_ARLEN(w0_ARLEN),
    .m_axi_w0_ARSIZE(w0_ARSIZE),
    .m_axi_w0_ARBURST(w0_ARBURST),
    .m_axi_w0_ARLOCK(w0_ARLOCK),
    .m_axi_w0_ARCACHE(w0_ARCACHE),
    .m_axi_w0_ARPROT(w0_ARPROT),
    .m_axi_w0_ARQOS(w0_ARQOS),
    .m_axi_w0_ARREGION(w0_ARREGION),
    .m_axi_w0_ARUSER(w0_ARUSER),
    .m_axi_w0_RVALID(w0_RVALID),
    .m_axi_w0_RREADY(w0_RREADY),
    .m_axi_w0_RDATA(w0_RDATA),
    .m_axi_w0_RLAST(w0_RLAST),
    .m_axi_w0_RID(w0_RID),
    .m_axi_w0_RUSER(w0_RUSER),
    .m_axi_w0_RRESP(w0_RRESP),
    .m_axi_w0_BVALID(w0_BVALID),
    .m_axi_w0_BREADY(w0_BREADY),
    .m_axi_w0_BRESP(w0_BRESP),
    .m_axi_w0_BID(w0_BID),
    .m_axi_w0_BUSER(w0_BUSER),
    .m_axi_w1_AWVALID(w1_AWVALID),
    .m_axi_w1_AWREADY(w1_AWREADY),
    .m_axi_w1_AWADDR(w1_AWADDR),
    .m_axi_w1_AWID(w1_AWID),
    .m_axi_w1_AWLEN(w1_AWLEN),
    .m_axi_w1_AWSIZE(w1_AWSIZE),
    .m_axi_w1_AWBURST(w1_AWBURST),
    .m_axi_w1_AWLOCK(w1_AWLOCK),
    .m_axi_w1_AWCACHE(w1_AWCACHE),
    .m_axi_w1_AWPROT(w1_AWPROT),
    .m_axi_w1_AWQOS(w1_AWQOS),
    .m_axi_w1_AWREGION(w1_AWREGION),
    .m_axi_w1_AWUSER(w1_AWUSER),
    .m_axi_w1_WVALID(w1_WVALID),
    .m_axi_w1_WREADY(w1_WREADY),
    .m_axi_w1_WDATA(w1_WDATA),
    .m_axi_w1_WSTRB(w1_WSTRB),
    .m_axi_w1_WLAST(w1_WLAST),
    .m_axi_w1_WID(w1_WID),
    .m_axi_w1_WUSER(w1_WUSER),
    .m_axi_w1_ARVALID(w1_ARVALID),
    .m_axi_w1_ARREADY(w1_ARREADY),
    .m_axi_w1_ARADDR(w1_ARADDR),
    .m_axi_w1_ARID(w1_ARID),
    .m_axi_w1_ARLEN(w1_ARLEN),
    .m_axi_w1_ARSIZE(w1_ARSIZE),
    .m_axi_w1_ARBURST(w1_ARBURST),
    .m_axi_w1_ARLOCK(w1_ARLOCK),
    .m_axi_w1_ARCACHE(w1_ARCACHE),
    .m_axi_w1_ARPROT(w1_ARPROT),
    .m_axi_w1_ARQOS(w1_ARQOS),
    .m_axi_w1_ARREGION(w1_ARREGION),
    .m_axi_w1_ARUSER(w1_ARUSER),
    .m_axi_w1_RVALID(w1_RVALID),
    .m_axi_w1_RREADY(w1_RREADY),
    .m_axi_w1_RDATA(w1_RDATA),
    .m_axi_w1_RLAST(w1_RLAST),
    .m_axi_w1_RID(w1_RID),
    .m_axi_w1_RUSER(w1_RUSER),
    .m_axi_w1_RRESP(w1_RRESP),
    .m_axi_w1_BVALID(w1_BVALID),
    .m_axi_w1_BREADY(w1_BREADY),
    .m_axi_w1_BRESP(w1_BRESP),
    .m_axi_w1_BID(w1_BID),
    .m_axi_w1_BUSER(w1_BUSER),
    .m_axi_w2_AWVALID(w2_AWVALID),
    .m_axi_w2_AWREADY(w2_AWREADY),
    .m_axi_w2_AWADDR(w2_AWADDR),
    .m_axi_w2_AWID(w2_AWID),
    .m_axi_w2_AWLEN(w2_AWLEN),
    .m_axi_w2_AWSIZE(w2_AWSIZE),
    .m_axi_w2_AWBURST(w2_AWBURST),
    .m_axi_w2_AWLOCK(w2_AWLOCK),
    .m_axi_w2_AWCACHE(w2_AWCACHE),
    .m_axi_w2_AWPROT(w2_AWPROT),
    .m_axi_w2_AWQOS(w2_AWQOS),
    .m_axi_w2_AWREGION(w2_AWREGION),
    .m_axi_w2_AWUSER(w2_AWUSER),
    .m_axi_w2_WVALID(w2_WVALID),
    .m_axi_w2_WREADY(w2_WREADY),
    .m_axi_w2_WDATA(w2_WDATA),
    .m_axi_w2_WSTRB(w2_WSTRB),
    .m_axi_w2_WLAST(w2_WLAST),
    .m_axi_w2_WID(w2_WID),
    .m_axi_w2_WUSER(w2_WUSER),
    .m_axi_w2_ARVALID(w2_ARVALID),
    .m_axi_w2_ARREADY(w2_ARREADY),
    .m_axi_w2_ARADDR(w2_ARADDR),
    .m_axi_w2_ARID(w2_ARID),
    .m_axi_w2_ARLEN(w2_ARLEN),
    .m_axi_w2_ARSIZE(w2_ARSIZE),
    .m_axi_w2_ARBURST(w2_ARBURST),
    .m_axi_w2_ARLOCK(w2_ARLOCK),
    .m_axi_w2_ARCACHE(w2_ARCACHE),
    .m_axi_w2_ARPROT(w2_ARPROT),
    .m_axi_w2_ARQOS(w2_ARQOS),
    .m_axi_w2_ARREGION(w2_ARREGION),
    .m_axi_w2_ARUSER(w2_ARUSER),
    .m_axi_w2_RVALID(w2_RVALID),
    .m_axi_w2_RREADY(w2_RREADY),
    .m_axi_w2_RDATA(w2_RDATA),
    .m_axi_w2_RLAST(w2_RLAST),
    .m_axi_w2_RID(w2_RID),
    .m_axi_w2_RUSER(w2_RUSER),
    .m_axi_w2_RRESP(w2_RRESP),
    .m_axi_w2_BVALID(w2_BVALID),
    .m_axi_w2_BREADY(w2_BREADY),
    .m_axi_w2_BRESP(w2_BRESP),
    .m_axi_w2_BID(w2_BID),
    .m_axi_w2_BUSER(w2_BUSER),
    .m_axi_w3_AWVALID(w3_AWVALID),
    .m_axi_w3_AWREADY(w3_AWREADY),
    .m_axi_w3_AWADDR(w3_AWADDR),
    .m_axi_w3_AWID(w3_AWID),
    .m_axi_w3_AWLEN(w3_AWLEN),
    .m_axi_w3_AWSIZE(w3_AWSIZE),
    .m_axi_w3_AWBURST(w3_AWBURST),
    .m_axi_w3_AWLOCK(w3_AWLOCK),
    .m_axi_w3_AWCACHE(w3_AWCACHE),
    .m_axi_w3_AWPROT(w3_AWPROT),
    .m_axi_w3_AWQOS(w3_AWQOS),
    .m_axi_w3_AWREGION(w3_AWREGION),
    .m_axi_w3_AWUSER(w3_AWUSER),
    .m_axi_w3_WVALID(w3_WVALID),
    .m_axi_w3_WREADY(w3_WREADY),
    .m_axi_w3_WDATA(w3_WDATA),
    .m_axi_w3_WSTRB(w3_WSTRB),
    .m_axi_w3_WLAST(w3_WLAST),
    .m_axi_w3_WID(w3_WID),
    .m_axi_w3_WUSER(w3_WUSER),
    .m_axi_w3_ARVALID(w3_ARVALID),
    .m_axi_w3_ARREADY(w3_ARREADY),
    .m_axi_w3_ARADDR(w3_ARADDR),
    .m_axi_w3_ARID(w3_ARID),
    .m_axi_w3_ARLEN(w3_ARLEN),
    .m_axi_w3_ARSIZE(w3_ARSIZE),
    .m_axi_w3_ARBURST(w3_ARBURST),
    .m_axi_w3_ARLOCK(w3_ARLOCK),
    .m_axi_w3_ARCACHE(w3_ARCACHE),
    .m_axi_w3_ARPROT(w3_ARPROT),
    .m_axi_w3_ARQOS(w3_ARQOS),
    .m_axi_w3_ARREGION(w3_ARREGION),
    .m_axi_w3_ARUSER(w3_ARUSER),
    .m_axi_w3_RVALID(w3_RVALID),
    .m_axi_w3_RREADY(w3_RREADY),
    .m_axi_w3_RDATA(w3_RDATA),
    .m_axi_w3_RLAST(w3_RLAST),
    .m_axi_w3_RID(w3_RID),
    .m_axi_w3_RUSER(w3_RUSER),
    .m_axi_w3_RRESP(w3_RRESP),
    .m_axi_w3_BVALID(w3_BVALID),
    .m_axi_w3_BREADY(w3_BREADY),
    .m_axi_w3_BRESP(w3_BRESP),
    .m_axi_w3_BID(w3_BID),
    .m_axi_w3_BUSER(w3_BUSER),
    .tx_TDATA(tx_TDATA),
    .tx_TVALID(tx_TVALID),
    .tx_TREADY(tx_TREADY),
    .tx_TKEEP(tx_TKEEP),
    .tx_TSTRB(tx_TSTRB),
    .tx_TLAST(tx_TLAST),
    .rx_TDATA(rx_TDATA),
    .rx_TVALID(rx_TVALID),
    .rx_TREADY(rx_TREADY),
    .rx_TKEEP(rx_TKEEP),
    .rx_TSTRB(rx_TSTRB),
    .rx_TLAST(rx_TLAST));
assign ap_clk = AESL_clock;
assign ap_rst_n = AESL_reset;
assign ap_rst_n_n = ~AESL_reset;
assign AESL_reset = dut_rst;
assign AESL_start = svtb_top.misc_if.tb2dut_ap_start;
assign AESL_ready = svtb_top.misc_if.dut2tb_ap_ready;
assign AESL_done  = svtb_top.misc_if.dut2tb_ap_done;
assign all_finish = svtb_top.misc_if.finished;
initial begin : initial_process
    integer proc_rand;
    rst = 0;
    # 100;
    repeat(0+3) @ (posedge AESL_clock);
    # 0.1;
    rst = 1;
end
initial begin : initial_process_for_dut_rst
    integer proc_rand;
    dut_rst = 0;
    # 100;
    repeat(3) @ (posedge AESL_clock);
    # 0.1;
    dut_rst = 1;
end
initial begin
    AESL_clock = 0;
    forever #`AUTOTB_CLOCK_PERIOD_DIV2 AESL_clock = ~AESL_clock;
end

    sv_module_top svtb_top();

////////////////////////////////////////////
// progress and performance
////////////////////////////////////////////

task wait_start();
    while (~AESL_start) begin
        @ (posedge AESL_clock);
    end
endtask

reg [31:0] clk_cnt = 0;
reg AESL_ready_p1;
reg AESL_start_p1;

always @ (posedge AESL_clock) begin
    if (AESL_reset == 0) begin
        clk_cnt <= 32'h0;
        AESL_ready_p1 <= 1'b0;
        AESL_start_p1 <= 1'b0;
    end
    else begin
        clk_cnt <= clk_cnt + 1;
        AESL_ready_p1 <= AESL_ready;
        AESL_start_p1 <= AESL_start;
    end
end

reg [31:0] start_timestamp [0:AUTOTB_TRANSACTION_NUM - 1];
reg [31:0] start_cnt;
reg [31:0] ready_timestamp [0:AUTOTB_TRANSACTION_NUM - 1];
reg [31:0] ap_ready_cnt;
reg [31:0] finish_timestamp [0:AUTOTB_TRANSACTION_NUM - 1];
reg [31:0] finish_cnt;
reg [31:0] lat_total;
event report_progress;

always @(posedge AESL_clock)
begin
    if (finish_cnt == AUTOTB_TRANSACTION_NUM - 1 && AESL_done == 1'b1)
        lat_total = clk_cnt - start_timestamp[0];
end

initial begin
    start_cnt = 0;
    finish_cnt = 0;
    ap_ready_cnt = 0;
    wait (AESL_reset == 1);
    wait_start();
    start_timestamp[start_cnt] = clk_cnt;
    start_cnt = start_cnt + 1;
    if (AESL_done) begin
        finish_timestamp[finish_cnt] = clk_cnt;
        finish_cnt = finish_cnt + 1;
    end
    -> report_progress;
    forever begin
        @ (posedge AESL_clock);
        if (start_cnt < AUTOTB_TRANSACTION_NUM) begin
            if ((AESL_start && AESL_ready_p1)||(AESL_start && ~AESL_start_p1)) begin
                start_timestamp[start_cnt] = clk_cnt;
                start_cnt = start_cnt + 1;
            end
        end
        if (ap_ready_cnt < AUTOTB_TRANSACTION_NUM) begin
            if (AESL_start_p1 && AESL_ready_p1) begin
                ready_timestamp[ap_ready_cnt] = clk_cnt;
                ap_ready_cnt = ap_ready_cnt + 1;
            end
        end
        if (finish_cnt < AUTOTB_TRANSACTION_NUM) begin
            if (AESL_done) begin
                finish_timestamp[finish_cnt] = clk_cnt;
                finish_cnt = finish_cnt + 1;
            end
        end
        -> report_progress;
    end
end

reg [31:0] progress_timeout;

initial begin : simulation_progress
    real intra_progress;
    wait (AESL_reset == 1);
    progress_timeout = PROGRESS_TIMEOUT;
    $display("////////////////////////////////////////////////////////////////////////////////////");
    $display("// Inter-Transaction Progress: Completed Transaction / Total Transaction");
    $display("// Intra-Transaction Progress: Measured Latency / Latency Estimation * 100%%");
    $display("//");
    $display("// RTL Simulation : \"Inter-Transaction Progress\" [\"Intra-Transaction Progress\"] @ \"Simulation Time\"");
    $display("////////////////////////////////////////////////////////////////////////////////////");
    print_progress();
    while (finish_cnt < AUTOTB_TRANSACTION_NUM) begin
        @ (report_progress);
        if (finish_cnt < AUTOTB_TRANSACTION_NUM) begin
            if (AESL_done) begin
                print_progress();
                progress_timeout = PROGRESS_TIMEOUT;
            end else begin
                if (progress_timeout == 0) begin
                    print_progress();
                    progress_timeout = PROGRESS_TIMEOUT;
                end else begin
                    progress_timeout = progress_timeout - 1;
                end
            end
        end
    end
    print_progress();
    $display("////////////////////////////////////////////////////////////////////////////////////");
    calculate_performance();
end

task get_intra_progress(output real intra_progress);
    begin
        if (start_cnt > finish_cnt) begin
            intra_progress = clk_cnt - start_timestamp[finish_cnt];
        end else if(finish_cnt > 0) begin
            intra_progress = LATENCY_ESTIMATION;
        end else begin
            intra_progress = 0;
        end
        intra_progress = intra_progress / LATENCY_ESTIMATION;
    end
endtask

task print_progress();
    real intra_progress;
    begin
        if (LATENCY_ESTIMATION > 0) begin
            get_intra_progress(intra_progress);
            $display("// RTL Simulation : %0d / %0d [%2.2f%%] @ \"%0t\"", finish_cnt, AUTOTB_TRANSACTION_NUM, intra_progress * 100, $time);
        end else begin
            $display("// RTL Simulation : %0d / %0d [n/a] @ \"%0t\"", finish_cnt, AUTOTB_TRANSACTION_NUM, $time);
        end
    end
endtask

task calculate_performance();
    integer i;
    integer fp;
    reg [31:0] latency [0:AUTOTB_TRANSACTION_NUM - 1];
    reg [31:0] latency_min;
    reg [31:0] latency_max;
    reg [31:0] latency_total;
    reg [31:0] latency_average;
    reg [31:0] interval [0:AUTOTB_TRANSACTION_NUM - 2];
    reg [31:0] interval_min;
    reg [31:0] interval_max;
    reg [31:0] interval_total;
    reg [31:0] interval_average;
    reg [31:0] total_execute_time;
    begin
        latency_min = -1;
        latency_max = 0;
        latency_total = 0;
        interval_min = -1;
        interval_max = 0;
        interval_total = 0;
        total_execute_time = lat_total;

        for (i = 0; i < AUTOTB_TRANSACTION_NUM; i = i + 1) begin
            // calculate latency
            latency[i] = finish_timestamp[i] - start_timestamp[i];
            if (latency[i] > latency_max) latency_max = latency[i];
            if (latency[i] < latency_min) latency_min = latency[i];
            latency_total = latency_total + latency[i];
            // calculate interval
            if (AUTOTB_TRANSACTION_NUM == 1) begin
                interval[i] = 0;
                interval_max = 0;
                interval_min = 0;
                interval_total = 0;
            end else if (i < AUTOTB_TRANSACTION_NUM - 1) begin
                interval[i] = start_timestamp[i + 1] - start_timestamp[i];
                if (interval[i] > interval_max) interval_max = interval[i];
                if (interval[i] < interval_min) interval_min = interval[i];
                interval_total = interval_total + interval[i];
            end
        end

        latency_average = latency_total / AUTOTB_TRANSACTION_NUM;
        if (AUTOTB_TRANSACTION_NUM == 1) begin
            interval_average = 0;
        end else begin
            interval_average = interval_total / (AUTOTB_TRANSACTION_NUM - 1);
        end

        fp = $fopen(`AUTOTB_LAT_RESULT_FILE, "w");

        $fdisplay(fp, "$MAX_LATENCY = \"%0d\"", latency_max);
        $fdisplay(fp, "$MIN_LATENCY = \"%0d\"", latency_min);
        $fdisplay(fp, "$AVER_LATENCY = \"%0d\"", latency_average);
        $fdisplay(fp, "$MAX_THROUGHPUT = \"%0d\"", interval_max);
        $fdisplay(fp, "$MIN_THROUGHPUT = \"%0d\"", interval_min);
        $fdisplay(fp, "$AVER_THROUGHPUT = \"%0d\"", interval_average);
        $fdisplay(fp, "$TOTAL_EXECUTE_TIME = \"%0d\"", total_execute_time);

        $fclose(fp);

        fp = $fopen(`AUTOTB_PER_RESULT_TRANS_FILE, "w");

        $fdisplay(fp, "%20s%16s%16s", "", "latency", "interval");
        if (AUTOTB_TRANSACTION_NUM == 1) begin
            i = 0;
            $fdisplay(fp, "transaction%8d:%16d%16d", i, latency[i], interval[i]);
        end else begin
            for (i = 0; i < AUTOTB_TRANSACTION_NUM; i = i + 1) begin
                if (i < AUTOTB_TRANSACTION_NUM - 1) begin
                    $fdisplay(fp, "transaction%8d:%16d%16d", i, latency[i], interval[i]);
                end else begin
                    $fdisplay(fp, "transaction%8d:%16d               x", i, latency[i]);
                end
            end
        end

        $fclose(fp);
    end
endtask


////////////////////////////////////////////
// Dependence Check
////////////////////////////////////////////

`ifndef POST_SYN

`endif

AESL_deadlock_detector deadlock_detector(
    .dl_reset(AESL_reset),
    .all_finish(all_finish),
    .dl_clock(AESL_clock));


AESL_deadlock_kernel_monitor_top kernel_monitor_top(
    .kernel_monitor_reset(~AESL_reset),
    .kernel_monitor_clock(AESL_clock));

///////////////////////////////////////////////////////
// dataflow status monitor
///////////////////////////////////////////////////////
dataflow_monitor U_dataflow_monitor(
    .clock(AESL_clock),
    .reset(~rst),
    .finish(all_finish));

`include "fifo_para.vh"

// External output backpressure only; no DUT arithmetic modification.
integer occ_peak_0 = 0;
always @(posedge AESL_clock) begin
  if (AESL_inst_op01_decode_one_kernel.grp_m89x_four_fu_317.result_U.num_data_cnt > occ_peak_0)
    occ_peak_0 = AESL_inst_op01_decode_one_kernel.grp_m89x_four_fu_317.result_U.num_data_cnt;
  if (AESL_inst_op01_decode_one_kernel.grp_m89x_four_fu_317.result_U.num_data_cnt > 8192)
    $fatal(1, "OP01_FIFO_OVERFLOW shard=0");
end
integer occ_peak_1 = 0;
always @(posedge AESL_clock) begin
  if (AESL_inst_op01_decode_one_kernel.grp_m89x_four_fu_317.result_1_U.num_data_cnt > occ_peak_1)
    occ_peak_1 = AESL_inst_op01_decode_one_kernel.grp_m89x_four_fu_317.result_1_U.num_data_cnt;
  if (AESL_inst_op01_decode_one_kernel.grp_m89x_four_fu_317.result_1_U.num_data_cnt > 8192)
    $fatal(1, "OP01_FIFO_OVERFLOW shard=1");
end
integer occ_peak_2 = 0;
always @(posedge AESL_clock) begin
  if (AESL_inst_op01_decode_one_kernel.grp_m89x_four_fu_317.result_2_U.num_data_cnt > occ_peak_2)
    occ_peak_2 = AESL_inst_op01_decode_one_kernel.grp_m89x_four_fu_317.result_2_U.num_data_cnt;
  if (AESL_inst_op01_decode_one_kernel.grp_m89x_four_fu_317.result_2_U.num_data_cnt > 8192)
    $fatal(1, "OP01_FIFO_OVERFLOW shard=2");
end
integer occ_peak_3 = 0;
always @(posedge AESL_clock) begin
  if (AESL_inst_op01_decode_one_kernel.grp_m89x_four_fu_317.result_3_U.num_data_cnt > occ_peak_3)
    occ_peak_3 = AESL_inst_op01_decode_one_kernel.grp_m89x_four_fu_317.result_3_U.num_data_cnt;
  if (AESL_inst_op01_decode_one_kernel.grp_m89x_four_fu_317.result_3_U.num_data_cnt > 8192)
    $fatal(1, "OP01_FIFO_OVERFLOW shard=3");
end
integer occ_tx;
initial begin
  for (occ_tx=0; occ_tx<4; occ_tx=occ_tx+1) begin
    if (occ_tx==0 || occ_tx==2) force rx_TREADY = 1'b0;
    wait (start_cnt > occ_tx);
    if (occ_tx==0 || occ_tx==2) begin
      wait (AESL_inst_op01_decode_one_kernel.grp_m89x_four_fu_317.result_3_U.num_data_cnt == 8192);
      $display("OP01_FIFO_FULL tx=%0d shard=3 occupancy=8192",occ_tx);
      repeat (256) @(posedge AESL_clock);
      release rx_TREADY;
    end
    wait (finish_cnt > occ_tx);
  end
  $display("OP01_FIFO_OCCUPANCY_PASS peaks=%0d,%0d,%0d,%0d",occ_peak_0,occ_peak_1,occ_peak_2,occ_peak_3);
end
initial begin
  wait (start_cnt > 0);
  repeat (12000000) @(posedge AESL_clock);
  if (finish_cnt != 4) $fatal(1,"OP01_OCCUPANCY_TIMEOUT");
end

endmodule
