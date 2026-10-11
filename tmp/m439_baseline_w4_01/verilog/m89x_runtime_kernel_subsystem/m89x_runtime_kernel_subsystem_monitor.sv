//==============================================================
//Vitis HLS - High-Level Synthesis from C, C++ and OpenCL v2026.1 (64-bit)
//Tool Version Limit: 2026.06
//Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
//Copyright 2022-2026 Advanced Micro Devices, Inc. All Rights Reserved.
//
//==============================================================

`ifndef M89X_RUNTIME_KERNEL_SUBSYSTEM_MONITOR_SV
`define M89X_RUNTIME_KERNEL_SUBSYSTEM_MONITOR_SV

`uvm_analysis_imp_decl(_svr_master_tx)
`uvm_analysis_imp_decl(_svr_slave_rx)
`uvm_analysis_imp_decl(_axi_wtr_w0)
`uvm_analysis_imp_decl(_axi_rtr_w0)
`uvm_analysis_imp_decl(_axi_wtr_w1)
`uvm_analysis_imp_decl(_axi_rtr_w1)
`uvm_analysis_imp_decl(_axi_wtr_w2)
`uvm_analysis_imp_decl(_axi_rtr_w2)
`uvm_analysis_imp_decl(_axi_wtr_w3)
`uvm_analysis_imp_decl(_axi_rtr_w3)
`uvm_analysis_imp_decl(_axi_wtr_control)
`uvm_analysis_imp_decl(_axi_rtr_control)

class m89x_runtime_kernel_subsystem_monitor extends uvm_component;

    m89x_runtime_kernel_reference_model refm;
    m89x_runtime_kernel_scoreboard scbd;

    `uvm_component_utils_begin(m89x_runtime_kernel_subsystem_monitor)
    `uvm_component_utils_end

    uvm_analysis_imp_svr_master_tx#(svr_pkg::svr_transfer#(161), m89x_runtime_kernel_subsystem_monitor) svr_master_tx_imp;
    uvm_analysis_imp_svr_slave_rx#(svr_pkg::svr_transfer#(81), m89x_runtime_kernel_subsystem_monitor) svr_slave_rx_imp;
    uvm_analysis_imp_axi_wtr_w0#(axi_pkg::axi_transfer, m89x_runtime_kernel_subsystem_monitor) w0_wtr_imp;
    uvm_analysis_imp_axi_rtr_w0#(axi_pkg::axi_transfer, m89x_runtime_kernel_subsystem_monitor) w0_rtr_imp;
    uvm_analysis_imp_axi_wtr_w1#(axi_pkg::axi_transfer, m89x_runtime_kernel_subsystem_monitor) w1_wtr_imp;
    uvm_analysis_imp_axi_rtr_w1#(axi_pkg::axi_transfer, m89x_runtime_kernel_subsystem_monitor) w1_rtr_imp;
    uvm_analysis_imp_axi_wtr_w2#(axi_pkg::axi_transfer, m89x_runtime_kernel_subsystem_monitor) w2_wtr_imp;
    uvm_analysis_imp_axi_rtr_w2#(axi_pkg::axi_transfer, m89x_runtime_kernel_subsystem_monitor) w2_rtr_imp;
    uvm_analysis_imp_axi_wtr_w3#(axi_pkg::axi_transfer, m89x_runtime_kernel_subsystem_monitor) w3_wtr_imp;
    uvm_analysis_imp_axi_rtr_w3#(axi_pkg::axi_transfer, m89x_runtime_kernel_subsystem_monitor) w3_rtr_imp;
    uvm_analysis_imp_axi_wtr_control#(axi_pkg::axi_transfer, m89x_runtime_kernel_subsystem_monitor) control_wtr_imp;
    uvm_analysis_imp_axi_rtr_control#(axi_pkg::axi_transfer, m89x_runtime_kernel_subsystem_monitor) control_rtr_imp;

    virtual function void build_phase(uvm_phase phase);
        super.build_phase(phase);
        if (!uvm_config_db#(m89x_runtime_kernel_reference_model)::get(this, "", "refm", refm))
            `uvm_fatal(this.get_full_name(), "No refm from high level")
        `uvm_info(this.get_full_name(), "get reference model by uvm_config_db", UVM_MEDIUM)
        scbd = m89x_runtime_kernel_scoreboard::type_id::create("scbd", this);
    endfunction

    virtual function void connect_phase(uvm_phase phase);
        super.connect_phase(phase);
    endfunction

    function new (string name = "", uvm_component parent = null);
        super.new(name, parent);
        svr_master_tx_imp = new("svr_master_tx_imp", this);
        svr_slave_rx_imp = new("svr_slave_rx_imp", this);
        w0_wtr_imp = new("w0_wtr_imp", this);
        w0_rtr_imp = new("w0_rtr_imp", this);
        w1_wtr_imp = new("w1_wtr_imp", this);
        w1_rtr_imp = new("w1_rtr_imp", this);
        w2_wtr_imp = new("w2_wtr_imp", this);
        w2_rtr_imp = new("w2_rtr_imp", this);
        w3_wtr_imp = new("w3_wtr_imp", this);
        w3_rtr_imp = new("w3_rtr_imp", this);
        control_wtr_imp = new("control_wtr_imp", this);
        control_rtr_imp = new("control_rtr_imp", this);
    endfunction

    virtual function void write_svr_master_tx(svr_transfer#(161) tr);
        refm.write_svr_master_tx(tr);
        scbd.write_svr_master_tx(tr);
    endfunction

    virtual function void write_svr_slave_rx(svr_transfer#(81) tr);
        refm.write_svr_slave_rx(tr);
        scbd.write_svr_slave_rx(tr);
    endfunction

    virtual function void write_axi_wtr_w0(axi_transfer tr);
        refm.write_axi_wtr_w0(tr);
        scbd.write_axi_wtr_w0(tr);
    endfunction

    virtual function void write_axi_rtr_w0(axi_transfer tr);
        refm.write_axi_rtr_w0(tr);
        scbd.write_axi_rtr_w0(tr);
    endfunction

    virtual function void write_axi_wtr_w1(axi_transfer tr);
        refm.write_axi_wtr_w1(tr);
        scbd.write_axi_wtr_w1(tr);
    endfunction

    virtual function void write_axi_rtr_w1(axi_transfer tr);
        refm.write_axi_rtr_w1(tr);
        scbd.write_axi_rtr_w1(tr);
    endfunction

    virtual function void write_axi_wtr_w2(axi_transfer tr);
        refm.write_axi_wtr_w2(tr);
        scbd.write_axi_wtr_w2(tr);
    endfunction

    virtual function void write_axi_rtr_w2(axi_transfer tr);
        refm.write_axi_rtr_w2(tr);
        scbd.write_axi_rtr_w2(tr);
    endfunction

    virtual function void write_axi_wtr_w3(axi_transfer tr);
        refm.write_axi_wtr_w3(tr);
        scbd.write_axi_wtr_w3(tr);
    endfunction

    virtual function void write_axi_rtr_w3(axi_transfer tr);
        refm.write_axi_rtr_w3(tr);
        scbd.write_axi_rtr_w3(tr);
    endfunction

    virtual function void write_axi_wtr_control(axi_transfer tr);
        refm.write_axi_wtr_control(tr);
        scbd.write_axi_wtr_control(tr);
    endfunction

    virtual function void write_axi_rtr_control(axi_transfer tr);
        refm.write_axi_rtr_control(tr);
        scbd.write_axi_rtr_control(tr);
    endfunction
endclass
`endif
