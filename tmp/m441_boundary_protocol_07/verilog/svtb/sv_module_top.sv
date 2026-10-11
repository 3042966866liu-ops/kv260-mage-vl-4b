//==============================================================
//Vitis HLS - High-Level Synthesis from C, C++ and OpenCL v2026.1 (64-bit)
//Tool Version Limit: 2026.06
//Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
//Copyright 2022-2026 Advanced Micro Devices, Inc. All Rights Reserved.
//
//==============================================================

`ifndef SV_MODULE_TOP_SV
`define SV_MODULE_TOP_SV


`timescale 1ns/1ps


`include "uvm_macros.svh"
import uvm_pkg::*;
import file_agent_pkg::*;
import svr_pkg::*;
import m89x_runtime_kernel_subsystem_pkg::*;
`include "m89x_runtime_kernel_subsys_test_sequence_lib.sv"
`include "m89x_runtime_kernel_test_lib.sv"


module sv_module_top;


    misc_interface              misc_if ( .clock(apatb_m89x_runtime_kernel_top.AESL_clock), .reset(apatb_m89x_runtime_kernel_top.AESL_reset) );
    assign misc_if.tb2dut_ap_start_kernel = apatb_m89x_runtime_kernel_top.AESL_inst_m89x_runtime_kernel.ap_start;
    assign misc_if.dut2tb_ap_ready = apatb_m89x_runtime_kernel_top.AESL_inst_m89x_runtime_kernel.ap_ready;
    assign misc_if.dut2tb_ap_done_kernel = apatb_m89x_runtime_kernel_top.AESL_inst_m89x_runtime_kernel.ap_done;
    initial begin
        uvm_config_db #(virtual misc_interface)::set(null, "uvm_test_top.top_env.*", "misc_if", misc_if);
    end


    svr_if #(161)  svr_tx_if    (.clk  (apatb_m89x_runtime_kernel_top.AESL_clock), .rst(apatb_m89x_runtime_kernel_top.AESL_reset));
    assign svr_tx_if.ready = apatb_m89x_runtime_kernel_top.tx_TREADY;
    assign apatb_m89x_runtime_kernel_top.tx_TVALID = svr_tx_if.valid;
    assign apatb_m89x_runtime_kernel_top.tx_TDATA = svr_tx_if.data[127:0];
    assign apatb_m89x_runtime_kernel_top.tx_TKEEP = svr_tx_if.data[143:128];
    assign apatb_m89x_runtime_kernel_top.tx_TSTRB = svr_tx_if.data[159:144];
    assign apatb_m89x_runtime_kernel_top.tx_TLAST = svr_tx_if.data[160:160];
    initial begin
        uvm_config_db #( virtual svr_if#(161) )::set(null, "uvm_test_top.top_env.env_master_svr_tx.*", "vif", svr_tx_if);
    end


    svr_if #(81)  svr_rx_if    (.clk  (apatb_m89x_runtime_kernel_top.AESL_clock), .rst(apatb_m89x_runtime_kernel_top.AESL_reset));
    assign apatb_m89x_runtime_kernel_top.rx_TREADY = svr_rx_if.ready && !m441_max_monitor.tail_block;
    assign svr_rx_if.valid = apatb_m89x_runtime_kernel_top.rx_TVALID && !m441_max_monitor.tail_block;
    assign svr_rx_if.data[63:0] = apatb_m89x_runtime_kernel_top.rx_TDATA;
    assign svr_rx_if.data[71:64] = apatb_m89x_runtime_kernel_top.rx_TKEEP;
    assign svr_rx_if.data[79:72] = apatb_m89x_runtime_kernel_top.rx_TSTRB;
    assign svr_rx_if.data[80:80] = apatb_m89x_runtime_kernel_top.rx_TLAST;
    initial begin
        uvm_config_db #( virtual svr_if#(81) )::set(null, "uvm_test_top.top_env.env_slave_svr_rx.*", "vif", svr_rx_if);
    end


    axi_if #(64,16,8,3,1)  axi_w0_if (.clk  (apatb_m89x_runtime_kernel_top.AESL_clock), .rst(apatb_m89x_runtime_kernel_top.AESL_reset));
    assign axi_w0_if.AWVALID = apatb_m89x_runtime_kernel_top.w0_AWVALID;
    assign apatb_m89x_runtime_kernel_top.w0_AWREADY = axi_w0_if.AWREADY;
    assign axi_w0_if.AWADDR = apatb_m89x_runtime_kernel_top.w0_AWADDR;
    assign axi_w0_if.AWID = apatb_m89x_runtime_kernel_top.w0_AWID;
    assign axi_w0_if.AWLEN = apatb_m89x_runtime_kernel_top.w0_AWLEN;
    assign axi_w0_if.AWSIZE = apatb_m89x_runtime_kernel_top.w0_AWSIZE;
    assign axi_w0_if.AWBURST = apatb_m89x_runtime_kernel_top.w0_AWBURST;
    assign axi_w0_if.AWLOCK = apatb_m89x_runtime_kernel_top.w0_AWLOCK;
    assign axi_w0_if.AWCACHE = apatb_m89x_runtime_kernel_top.w0_AWCACHE;
    assign axi_w0_if.AWPROT = apatb_m89x_runtime_kernel_top.w0_AWPROT;
    assign axi_w0_if.AWQOS = apatb_m89x_runtime_kernel_top.w0_AWQOS;
    assign axi_w0_if.AWREGION = apatb_m89x_runtime_kernel_top.w0_AWREGION;
    assign axi_w0_if.AWUSER = apatb_m89x_runtime_kernel_top.w0_AWUSER;
    assign axi_w0_if.WVALID = apatb_m89x_runtime_kernel_top.w0_WVALID;
    assign apatb_m89x_runtime_kernel_top.w0_WREADY = axi_w0_if.WREADY;
    assign axi_w0_if.WDATA = apatb_m89x_runtime_kernel_top.w0_WDATA;
    assign axi_w0_if.WSTRB = apatb_m89x_runtime_kernel_top.w0_WSTRB;
    assign axi_w0_if.WLAST = apatb_m89x_runtime_kernel_top.w0_WLAST;
    assign axi_w0_if.WID = apatb_m89x_runtime_kernel_top.w0_WID;
    assign axi_w0_if.WUSER = apatb_m89x_runtime_kernel_top.w0_WUSER;
    assign axi_w0_if.ARVALID = apatb_m89x_runtime_kernel_top.w0_ARVALID;
    assign apatb_m89x_runtime_kernel_top.w0_ARREADY = axi_w0_if.ARREADY;
    assign axi_w0_if.ARADDR = apatb_m89x_runtime_kernel_top.w0_ARADDR;
    assign axi_w0_if.ARID = apatb_m89x_runtime_kernel_top.w0_ARID;
    assign axi_w0_if.ARLEN = apatb_m89x_runtime_kernel_top.w0_ARLEN;
    assign axi_w0_if.ARSIZE = apatb_m89x_runtime_kernel_top.w0_ARSIZE;
    assign axi_w0_if.ARBURST = apatb_m89x_runtime_kernel_top.w0_ARBURST;
    assign axi_w0_if.ARLOCK = apatb_m89x_runtime_kernel_top.w0_ARLOCK;
    assign axi_w0_if.ARCACHE = apatb_m89x_runtime_kernel_top.w0_ARCACHE;
    assign axi_w0_if.ARPROT = apatb_m89x_runtime_kernel_top.w0_ARPROT;
    assign axi_w0_if.ARQOS = apatb_m89x_runtime_kernel_top.w0_ARQOS;
    assign axi_w0_if.ARREGION = apatb_m89x_runtime_kernel_top.w0_ARREGION;
    assign axi_w0_if.ARUSER = apatb_m89x_runtime_kernel_top.w0_ARUSER;
    assign apatb_m89x_runtime_kernel_top.w0_RVALID = axi_w0_if.RVALID;
    assign axi_w0_if.RREADY = apatb_m89x_runtime_kernel_top.w0_RREADY;
    assign apatb_m89x_runtime_kernel_top.w0_RDATA = axi_w0_if.RDATA;
    assign apatb_m89x_runtime_kernel_top.w0_RLAST = axi_w0_if.RLAST;
    assign apatb_m89x_runtime_kernel_top.w0_RID = axi_w0_if.RID;
    assign apatb_m89x_runtime_kernel_top.w0_RUSER = axi_w0_if.RUSER;
    assign apatb_m89x_runtime_kernel_top.w0_RRESP = axi_w0_if.RRESP;
    assign apatb_m89x_runtime_kernel_top.w0_BVALID = axi_w0_if.BVALID;
    assign axi_w0_if.BREADY = apatb_m89x_runtime_kernel_top.w0_BREADY;
    assign apatb_m89x_runtime_kernel_top.w0_BRESP = axi_w0_if.BRESP;
    assign apatb_m89x_runtime_kernel_top.w0_BID = axi_w0_if.BID;
    assign apatb_m89x_runtime_kernel_top.w0_BUSER = axi_w0_if.BUSER;
    initial begin
        uvm_config_db #( virtual axi_if#(64,16,8,3,1) )::set(null, "uvm_test_top.top_env.axi_master_w0.*", "vif", axi_w0_if);
    end


    axi_if #(64,16,8,3,1)  axi_w1_if (.clk  (apatb_m89x_runtime_kernel_top.AESL_clock), .rst(apatb_m89x_runtime_kernel_top.AESL_reset));
    assign axi_w1_if.AWVALID = apatb_m89x_runtime_kernel_top.w1_AWVALID;
    assign apatb_m89x_runtime_kernel_top.w1_AWREADY = axi_w1_if.AWREADY;
    assign axi_w1_if.AWADDR = apatb_m89x_runtime_kernel_top.w1_AWADDR;
    assign axi_w1_if.AWID = apatb_m89x_runtime_kernel_top.w1_AWID;
    assign axi_w1_if.AWLEN = apatb_m89x_runtime_kernel_top.w1_AWLEN;
    assign axi_w1_if.AWSIZE = apatb_m89x_runtime_kernel_top.w1_AWSIZE;
    assign axi_w1_if.AWBURST = apatb_m89x_runtime_kernel_top.w1_AWBURST;
    assign axi_w1_if.AWLOCK = apatb_m89x_runtime_kernel_top.w1_AWLOCK;
    assign axi_w1_if.AWCACHE = apatb_m89x_runtime_kernel_top.w1_AWCACHE;
    assign axi_w1_if.AWPROT = apatb_m89x_runtime_kernel_top.w1_AWPROT;
    assign axi_w1_if.AWQOS = apatb_m89x_runtime_kernel_top.w1_AWQOS;
    assign axi_w1_if.AWREGION = apatb_m89x_runtime_kernel_top.w1_AWREGION;
    assign axi_w1_if.AWUSER = apatb_m89x_runtime_kernel_top.w1_AWUSER;
    assign axi_w1_if.WVALID = apatb_m89x_runtime_kernel_top.w1_WVALID;
    assign apatb_m89x_runtime_kernel_top.w1_WREADY = axi_w1_if.WREADY;
    assign axi_w1_if.WDATA = apatb_m89x_runtime_kernel_top.w1_WDATA;
    assign axi_w1_if.WSTRB = apatb_m89x_runtime_kernel_top.w1_WSTRB;
    assign axi_w1_if.WLAST = apatb_m89x_runtime_kernel_top.w1_WLAST;
    assign axi_w1_if.WID = apatb_m89x_runtime_kernel_top.w1_WID;
    assign axi_w1_if.WUSER = apatb_m89x_runtime_kernel_top.w1_WUSER;
    assign axi_w1_if.ARVALID = apatb_m89x_runtime_kernel_top.w1_ARVALID;
    assign apatb_m89x_runtime_kernel_top.w1_ARREADY = axi_w1_if.ARREADY;
    assign axi_w1_if.ARADDR = apatb_m89x_runtime_kernel_top.w1_ARADDR;
    assign axi_w1_if.ARID = apatb_m89x_runtime_kernel_top.w1_ARID;
    assign axi_w1_if.ARLEN = apatb_m89x_runtime_kernel_top.w1_ARLEN;
    assign axi_w1_if.ARSIZE = apatb_m89x_runtime_kernel_top.w1_ARSIZE;
    assign axi_w1_if.ARBURST = apatb_m89x_runtime_kernel_top.w1_ARBURST;
    assign axi_w1_if.ARLOCK = apatb_m89x_runtime_kernel_top.w1_ARLOCK;
    assign axi_w1_if.ARCACHE = apatb_m89x_runtime_kernel_top.w1_ARCACHE;
    assign axi_w1_if.ARPROT = apatb_m89x_runtime_kernel_top.w1_ARPROT;
    assign axi_w1_if.ARQOS = apatb_m89x_runtime_kernel_top.w1_ARQOS;
    assign axi_w1_if.ARREGION = apatb_m89x_runtime_kernel_top.w1_ARREGION;
    assign axi_w1_if.ARUSER = apatb_m89x_runtime_kernel_top.w1_ARUSER;
    assign apatb_m89x_runtime_kernel_top.w1_RVALID = axi_w1_if.RVALID;
    assign axi_w1_if.RREADY = apatb_m89x_runtime_kernel_top.w1_RREADY;
    assign apatb_m89x_runtime_kernel_top.w1_RDATA = axi_w1_if.RDATA;
    assign apatb_m89x_runtime_kernel_top.w1_RLAST = axi_w1_if.RLAST;
    assign apatb_m89x_runtime_kernel_top.w1_RID = axi_w1_if.RID;
    assign apatb_m89x_runtime_kernel_top.w1_RUSER = axi_w1_if.RUSER;
    assign apatb_m89x_runtime_kernel_top.w1_RRESP = axi_w1_if.RRESP;
    assign apatb_m89x_runtime_kernel_top.w1_BVALID = axi_w1_if.BVALID;
    assign axi_w1_if.BREADY = apatb_m89x_runtime_kernel_top.w1_BREADY;
    assign apatb_m89x_runtime_kernel_top.w1_BRESP = axi_w1_if.BRESP;
    assign apatb_m89x_runtime_kernel_top.w1_BID = axi_w1_if.BID;
    assign apatb_m89x_runtime_kernel_top.w1_BUSER = axi_w1_if.BUSER;
    initial begin
        uvm_config_db #( virtual axi_if#(64,16,8,3,1) )::set(null, "uvm_test_top.top_env.axi_master_w1.*", "vif", axi_w1_if);
    end


    axi_if #(64,16,8,3,1)  axi_w2_if (.clk  (apatb_m89x_runtime_kernel_top.AESL_clock), .rst(apatb_m89x_runtime_kernel_top.AESL_reset));
    assign axi_w2_if.AWVALID = apatb_m89x_runtime_kernel_top.w2_AWVALID;
    assign apatb_m89x_runtime_kernel_top.w2_AWREADY = axi_w2_if.AWREADY;
    assign axi_w2_if.AWADDR = apatb_m89x_runtime_kernel_top.w2_AWADDR;
    assign axi_w2_if.AWID = apatb_m89x_runtime_kernel_top.w2_AWID;
    assign axi_w2_if.AWLEN = apatb_m89x_runtime_kernel_top.w2_AWLEN;
    assign axi_w2_if.AWSIZE = apatb_m89x_runtime_kernel_top.w2_AWSIZE;
    assign axi_w2_if.AWBURST = apatb_m89x_runtime_kernel_top.w2_AWBURST;
    assign axi_w2_if.AWLOCK = apatb_m89x_runtime_kernel_top.w2_AWLOCK;
    assign axi_w2_if.AWCACHE = apatb_m89x_runtime_kernel_top.w2_AWCACHE;
    assign axi_w2_if.AWPROT = apatb_m89x_runtime_kernel_top.w2_AWPROT;
    assign axi_w2_if.AWQOS = apatb_m89x_runtime_kernel_top.w2_AWQOS;
    assign axi_w2_if.AWREGION = apatb_m89x_runtime_kernel_top.w2_AWREGION;
    assign axi_w2_if.AWUSER = apatb_m89x_runtime_kernel_top.w2_AWUSER;
    assign axi_w2_if.WVALID = apatb_m89x_runtime_kernel_top.w2_WVALID;
    assign apatb_m89x_runtime_kernel_top.w2_WREADY = axi_w2_if.WREADY;
    assign axi_w2_if.WDATA = apatb_m89x_runtime_kernel_top.w2_WDATA;
    assign axi_w2_if.WSTRB = apatb_m89x_runtime_kernel_top.w2_WSTRB;
    assign axi_w2_if.WLAST = apatb_m89x_runtime_kernel_top.w2_WLAST;
    assign axi_w2_if.WID = apatb_m89x_runtime_kernel_top.w2_WID;
    assign axi_w2_if.WUSER = apatb_m89x_runtime_kernel_top.w2_WUSER;
    assign axi_w2_if.ARVALID = apatb_m89x_runtime_kernel_top.w2_ARVALID;
    assign apatb_m89x_runtime_kernel_top.w2_ARREADY = axi_w2_if.ARREADY;
    assign axi_w2_if.ARADDR = apatb_m89x_runtime_kernel_top.w2_ARADDR;
    assign axi_w2_if.ARID = apatb_m89x_runtime_kernel_top.w2_ARID;
    assign axi_w2_if.ARLEN = apatb_m89x_runtime_kernel_top.w2_ARLEN;
    assign axi_w2_if.ARSIZE = apatb_m89x_runtime_kernel_top.w2_ARSIZE;
    assign axi_w2_if.ARBURST = apatb_m89x_runtime_kernel_top.w2_ARBURST;
    assign axi_w2_if.ARLOCK = apatb_m89x_runtime_kernel_top.w2_ARLOCK;
    assign axi_w2_if.ARCACHE = apatb_m89x_runtime_kernel_top.w2_ARCACHE;
    assign axi_w2_if.ARPROT = apatb_m89x_runtime_kernel_top.w2_ARPROT;
    assign axi_w2_if.ARQOS = apatb_m89x_runtime_kernel_top.w2_ARQOS;
    assign axi_w2_if.ARREGION = apatb_m89x_runtime_kernel_top.w2_ARREGION;
    assign axi_w2_if.ARUSER = apatb_m89x_runtime_kernel_top.w2_ARUSER;
    assign apatb_m89x_runtime_kernel_top.w2_RVALID = axi_w2_if.RVALID;
    assign axi_w2_if.RREADY = apatb_m89x_runtime_kernel_top.w2_RREADY;
    assign apatb_m89x_runtime_kernel_top.w2_RDATA = axi_w2_if.RDATA;
    assign apatb_m89x_runtime_kernel_top.w2_RLAST = axi_w2_if.RLAST;
    assign apatb_m89x_runtime_kernel_top.w2_RID = axi_w2_if.RID;
    assign apatb_m89x_runtime_kernel_top.w2_RUSER = axi_w2_if.RUSER;
    assign apatb_m89x_runtime_kernel_top.w2_RRESP = axi_w2_if.RRESP;
    assign apatb_m89x_runtime_kernel_top.w2_BVALID = axi_w2_if.BVALID;
    assign axi_w2_if.BREADY = apatb_m89x_runtime_kernel_top.w2_BREADY;
    assign apatb_m89x_runtime_kernel_top.w2_BRESP = axi_w2_if.BRESP;
    assign apatb_m89x_runtime_kernel_top.w2_BID = axi_w2_if.BID;
    assign apatb_m89x_runtime_kernel_top.w2_BUSER = axi_w2_if.BUSER;
    initial begin
        uvm_config_db #( virtual axi_if#(64,16,8,3,1) )::set(null, "uvm_test_top.top_env.axi_master_w2.*", "vif", axi_w2_if);
    end


    axi_if #(64,16,8,3,1)  axi_w3_if (.clk  (apatb_m89x_runtime_kernel_top.AESL_clock), .rst(apatb_m89x_runtime_kernel_top.AESL_reset));
    assign axi_w3_if.AWVALID = apatb_m89x_runtime_kernel_top.w3_AWVALID;
    assign apatb_m89x_runtime_kernel_top.w3_AWREADY = axi_w3_if.AWREADY;
    assign axi_w3_if.AWADDR = apatb_m89x_runtime_kernel_top.w3_AWADDR;
    assign axi_w3_if.AWID = apatb_m89x_runtime_kernel_top.w3_AWID;
    assign axi_w3_if.AWLEN = apatb_m89x_runtime_kernel_top.w3_AWLEN;
    assign axi_w3_if.AWSIZE = apatb_m89x_runtime_kernel_top.w3_AWSIZE;
    assign axi_w3_if.AWBURST = apatb_m89x_runtime_kernel_top.w3_AWBURST;
    assign axi_w3_if.AWLOCK = apatb_m89x_runtime_kernel_top.w3_AWLOCK;
    assign axi_w3_if.AWCACHE = apatb_m89x_runtime_kernel_top.w3_AWCACHE;
    assign axi_w3_if.AWPROT = apatb_m89x_runtime_kernel_top.w3_AWPROT;
    assign axi_w3_if.AWQOS = apatb_m89x_runtime_kernel_top.w3_AWQOS;
    assign axi_w3_if.AWREGION = apatb_m89x_runtime_kernel_top.w3_AWREGION;
    assign axi_w3_if.AWUSER = apatb_m89x_runtime_kernel_top.w3_AWUSER;
    assign axi_w3_if.WVALID = apatb_m89x_runtime_kernel_top.w3_WVALID;
    assign apatb_m89x_runtime_kernel_top.w3_WREADY = axi_w3_if.WREADY;
    assign axi_w3_if.WDATA = apatb_m89x_runtime_kernel_top.w3_WDATA;
    assign axi_w3_if.WSTRB = apatb_m89x_runtime_kernel_top.w3_WSTRB;
    assign axi_w3_if.WLAST = apatb_m89x_runtime_kernel_top.w3_WLAST;
    assign axi_w3_if.WID = apatb_m89x_runtime_kernel_top.w3_WID;
    assign axi_w3_if.WUSER = apatb_m89x_runtime_kernel_top.w3_WUSER;
    assign axi_w3_if.ARVALID = apatb_m89x_runtime_kernel_top.w3_ARVALID;
    assign apatb_m89x_runtime_kernel_top.w3_ARREADY = axi_w3_if.ARREADY;
    assign axi_w3_if.ARADDR = apatb_m89x_runtime_kernel_top.w3_ARADDR;
    assign axi_w3_if.ARID = apatb_m89x_runtime_kernel_top.w3_ARID;
    assign axi_w3_if.ARLEN = apatb_m89x_runtime_kernel_top.w3_ARLEN;
    assign axi_w3_if.ARSIZE = apatb_m89x_runtime_kernel_top.w3_ARSIZE;
    assign axi_w3_if.ARBURST = apatb_m89x_runtime_kernel_top.w3_ARBURST;
    assign axi_w3_if.ARLOCK = apatb_m89x_runtime_kernel_top.w3_ARLOCK;
    assign axi_w3_if.ARCACHE = apatb_m89x_runtime_kernel_top.w3_ARCACHE;
    assign axi_w3_if.ARPROT = apatb_m89x_runtime_kernel_top.w3_ARPROT;
    assign axi_w3_if.ARQOS = apatb_m89x_runtime_kernel_top.w3_ARQOS;
    assign axi_w3_if.ARREGION = apatb_m89x_runtime_kernel_top.w3_ARREGION;
    assign axi_w3_if.ARUSER = apatb_m89x_runtime_kernel_top.w3_ARUSER;
    assign apatb_m89x_runtime_kernel_top.w3_RVALID = axi_w3_if.RVALID;
    assign axi_w3_if.RREADY = apatb_m89x_runtime_kernel_top.w3_RREADY;
    assign apatb_m89x_runtime_kernel_top.w3_RDATA = axi_w3_if.RDATA;
    assign apatb_m89x_runtime_kernel_top.w3_RLAST = axi_w3_if.RLAST;
    assign apatb_m89x_runtime_kernel_top.w3_RID = axi_w3_if.RID;
    assign apatb_m89x_runtime_kernel_top.w3_RUSER = axi_w3_if.RUSER;
    assign apatb_m89x_runtime_kernel_top.w3_RRESP = axi_w3_if.RRESP;
    assign apatb_m89x_runtime_kernel_top.w3_BVALID = axi_w3_if.BVALID;
    assign axi_w3_if.BREADY = apatb_m89x_runtime_kernel_top.w3_BREADY;
    assign apatb_m89x_runtime_kernel_top.w3_BRESP = axi_w3_if.BRESP;
    assign apatb_m89x_runtime_kernel_top.w3_BID = axi_w3_if.BID;
    assign apatb_m89x_runtime_kernel_top.w3_BUSER = axi_w3_if.BUSER;
    initial begin
        uvm_config_db #( virtual axi_if#(64,16,8,3,1) )::set(null, "uvm_test_top.top_env.axi_master_w3.*", "vif", axi_w3_if);
    end


    axi_if #(8,4,4,3,1)  axi_control_if (.clk  (apatb_m89x_runtime_kernel_top.AESL_clock), .rst(apatb_m89x_runtime_kernel_top.AESL_reset));
    assign apatb_m89x_runtime_kernel_top.control_AWADDR = axi_control_if.AWADDR;
    assign apatb_m89x_runtime_kernel_top.control_AWVALID = axi_control_if.AWVALID;
    assign axi_control_if.AWREADY = apatb_m89x_runtime_kernel_top.control_AWREADY;
    assign apatb_m89x_runtime_kernel_top.control_WVALID = axi_control_if.WVALID;
    assign axi_control_if.WREADY = apatb_m89x_runtime_kernel_top.control_WREADY;
    assign apatb_m89x_runtime_kernel_top.control_WDATA = axi_control_if.WDATA;
    assign apatb_m89x_runtime_kernel_top.control_WSTRB = axi_control_if.WSTRB;
    assign apatb_m89x_runtime_kernel_top.control_ARADDR = axi_control_if.ARADDR;
    assign apatb_m89x_runtime_kernel_top.control_ARVALID = axi_control_if.ARVALID;
    assign axi_control_if.ARREADY = apatb_m89x_runtime_kernel_top.control_ARREADY;
    assign axi_control_if.RVALID = apatb_m89x_runtime_kernel_top.control_RVALID;
    assign apatb_m89x_runtime_kernel_top.control_RREADY = axi_control_if.RREADY;
    assign axi_control_if.RDATA = apatb_m89x_runtime_kernel_top.control_RDATA;
    assign axi_control_if.RRESP = apatb_m89x_runtime_kernel_top.control_RRESP;
    assign axi_control_if.BVALID = apatb_m89x_runtime_kernel_top.control_BVALID;
    assign apatb_m89x_runtime_kernel_top.control_BREADY = axi_control_if.BREADY;
    assign axi_control_if.BRESP = apatb_m89x_runtime_kernel_top.control_BRESP;
    assign axi_control_if.BID = 0;
    assign axi_control_if.RID = 0;
    assign axi_control_if.RLAST = 1;
    initial begin
        uvm_config_db #( virtual axi_if#(8,4,4,3,1) )::set(null, "uvm_test_top.top_env.axi_lite_control.*", "vif", axi_control_if);
    end


    initial begin
        run_test();
    end
endmodule
`endif
