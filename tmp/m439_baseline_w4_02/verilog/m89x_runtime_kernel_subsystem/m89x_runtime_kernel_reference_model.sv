//==============================================================
//Vitis HLS - High-Level Synthesis from C, C++ and OpenCL v2026.1 (64-bit)
//Tool Version Limit: 2026.06
//Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
//Copyright 2022-2026 Advanced Micro Devices, Inc. All Rights Reserved.
//
//==============================================================

`ifndef M89X_RUNTIME_KERNEL_REFERENCE_MODEL_SV
`define M89X_RUNTIME_KERNEL_REFERENCE_MODEL_SV
typedef class m89x_runtime_kernel_reference_model;
class memaccess_axi_state_cbs extends axi_pkg::axi_state_cbs;
    m89x_runtime_kernel_reference_model refm;
    string memid;
    //function new(string name="memaccess_axi_state_cbs");
    //    super.new(name);
    //endfunction
    virtual function void memmodel_read_fromar(ref logic[7:0] data[$], input longint addr, input longint len);
        if(memid=="w0") refm.mem_blk_pages_w0.read_elems_pipepage(data, addr, len);
        if(memid=="w1") refm.mem_blk_pages_w1.read_elems_pipepage(data, addr, len);
        if(memid=="w2") refm.mem_blk_pages_w2.read_elems_pipepage(data, addr, len);
        if(memid=="w3") refm.mem_blk_pages_w3.read_elems_pipepage(data, addr, len);
    endfunction
endclass

class m89x_runtime_kernel_reference_model extends uvm_component;
`define TV_IN_w0 "../tv/cdatafile/c.m89x_runtime_kernel.autotvin_w0.dat"
`define TV_OUT_w0 "../tv/rtldatafile/rtl.m89x_runtime_kernel.autotvout_w0.dat"
`define TV_IN_OFFSET_s0 "../tv/cdatafile/c.m89x_runtime_kernel.autotvin_s0.dat"
`define TV_IN_w1 "../tv/cdatafile/c.m89x_runtime_kernel.autotvin_w1.dat"
`define TV_OUT_w1 "../tv/rtldatafile/rtl.m89x_runtime_kernel.autotvout_w1.dat"
`define TV_IN_OFFSET_s1 "../tv/cdatafile/c.m89x_runtime_kernel.autotvin_s1.dat"
`define TV_IN_w2 "../tv/cdatafile/c.m89x_runtime_kernel.autotvin_w2.dat"
`define TV_OUT_w2 "../tv/rtldatafile/rtl.m89x_runtime_kernel.autotvout_w2.dat"
`define TV_IN_OFFSET_s2 "../tv/cdatafile/c.m89x_runtime_kernel.autotvin_s2.dat"
`define TV_IN_w3 "../tv/cdatafile/c.m89x_runtime_kernel.autotvin_w3.dat"
`define TV_OUT_w3 "../tv/rtldatafile/rtl.m89x_runtime_kernel.autotvout_w3.dat"
`define TV_IN_OFFSET_s3 "../tv/cdatafile/c.m89x_runtime_kernel.autotvin_s3.dat"
`define TV_IN_s0 "../tv/cdatafile/c.m89x_runtime_kernel.autotvin_s0.dat"
`define TV_OUT_s0 ""
`define TV_IN_s1 "../tv/cdatafile/c.m89x_runtime_kernel.autotvin_s1.dat"
`define TV_OUT_s1 ""
`define TV_IN_s2 "../tv/cdatafile/c.m89x_runtime_kernel.autotvin_s2.dat"
`define TV_OUT_s2 ""
`define TV_IN_s3 "../tv/cdatafile/c.m89x_runtime_kernel.autotvin_s3.dat"
`define TV_OUT_s3 ""
`define TV_IN_config_r "../tv/cdatafile/c.m89x_runtime_kernel.autotvin_config_r.dat"
`define TV_OUT_config_r ""
`define TV_IN_ap_return ""
`define TV_OUT_ap_return "../tv/rtldatafile/rtl.m89x_runtime_kernel.autotvout_ap_return.dat"
    bit  read_data_finish_control;
    bit  write_data_finish_control;
    event allaxilite_read_data_finish;
    event allaxilite_write_data_finish;
    event allsvr_input_done;
    event allsvr_output_done;
    event write_start_finish;
    int trans_num_total = 1;
    int trans_num_idx;
    int ap_done_cnt=1;
    event dut2tb_ap_ready;
    event dut2tb_ap_done;
    event ap_ready_for_nexttrans;
    event ap_done_for_nexttrans;
    event finish;
    m89x_runtime_kernel_config m89x_runtime_kernel_cfg;
    virtual interface misc_interface misc_if;

    mem_model_pages_with_diffofst#(128,8) mem_blk_pages_w0;
    int blk_id_w0 = 0;
    memaccess_axi_state_cbs axi_memaccess_cb_w0;

    mem_model_pages_with_diffofst#(128,8) mem_blk_pages_w1;
    int blk_id_w1 = 0;
    memaccess_axi_state_cbs axi_memaccess_cb_w1;

    mem_model_pages_with_diffofst#(128,8) mem_blk_pages_w2;
    int blk_id_w2 = 0;
    memaccess_axi_state_cbs axi_memaccess_cb_w2;

    mem_model_pages_with_diffofst#(128,8) mem_blk_pages_w3;
    int blk_id_w3 = 0;
    memaccess_axi_state_cbs axi_memaccess_cb_w3;

    mem_model_pages#(32,8) mem_blk_pages_control_config_r;
    mem_model_pages#(32,8) mem_blk_pages_control_ap_return;
    int svr_tx_delay;
    covergroup svr_tx_cov;
        delay: coverpoint svr_tx_delay
        {
            bins norm[257] = { [0 : 256] };
        }
    endgroup
    int svr_rx_delay;
    covergroup svr_rx_cov;
        delay: coverpoint svr_rx_delay
        {
            bins norm[257] = { [0 : 256] };
        }
    endgroup
    
    `uvm_component_utils_begin(m89x_runtime_kernel_reference_model)
        `uvm_field_int (trans_num_idx, UVM_DEFAULT)
    `uvm_component_utils_end

    virtual function void build_phase(uvm_phase phase);
        super.build_phase(phase);
        if(!uvm_config_db#(virtual misc_interface)::get(this, "", "misc_if", misc_if))
            `uvm_fatal(this.get_full_name(), "No misc_if from high level")
        axi_memaccess_cb_w0 = new;
        axi_memaccess_cb_w0.refm = this;
        axi_memaccess_cb_w0.memid = "w0";
        axi_memaccess_cb_w1 = new;
        axi_memaccess_cb_w1.refm = this;
        axi_memaccess_cb_w1.memid = "w1";
        axi_memaccess_cb_w2 = new;
        axi_memaccess_cb_w2.refm = this;
        axi_memaccess_cb_w2.memid = "w2";
        axi_memaccess_cb_w3 = new;
        axi_memaccess_cb_w3.refm = this;
        axi_memaccess_cb_w3.memid = "w3";
    endfunction

    function new (string name = "", uvm_component parent = null);
        super.new (name, parent);
        svr_tx_cov = new;
        svr_rx_cov = new;
        trans_num_idx= 0;
    endfunction

    virtual task run_phase(uvm_phase phase);
        string fpath[$];
misc_if.dut2tb_ap_done = 0;

        fpath.push_back(`TV_IN_config_r);
        mem_blk_pages_control_config_r = mem_model_pages#(32,8)::type_id::create("mem_blk_pages_control_config_r");
        mem_blk_pages_control_config_r.tvinload_pagechk_atinit(fpath, 1*((32+7)/8), 0, 128);
        fpath.delete;


        mem_blk_pages_control_ap_return = mem_model_pages#(32,8)::type_id::create("mem_blk_pages_control_ap_return");
        mem_blk_pages_control_ap_return.init_pages(trans_num_total, 1*((32+7)/8), 16);
        mem_blk_pages_control_ap_return.tvoutdump_atinit(`TV_OUT_ap_return);

        fpath.push_back(`TV_IN_w0);
        mem_blk_pages_w0 = mem_model_pages_with_diffofst#(128,8)::type_id::create("mem_blk_pages_w0");
        mem_blk_pages_w0.whole_page_size=8388864;
        mem_blk_pages_w0.maxi_bundlevar_fpath["s0"]=`TV_IN_OFFSET_s0;
        mem_blk_pages_w0.set_binary(1);
        mem_blk_pages_w0.tvinload_pagechk_atinit(fpath, 524288*((128+7)/8), 0, 0);
        fpath.delete();

        fpath.push_back(`TV_IN_w1);
        mem_blk_pages_w1 = mem_model_pages_with_diffofst#(128,8)::type_id::create("mem_blk_pages_w1");
        mem_blk_pages_w1.whole_page_size=8388864;
        mem_blk_pages_w1.maxi_bundlevar_fpath["s1"]=`TV_IN_OFFSET_s1;
        mem_blk_pages_w1.set_binary(1);
        mem_blk_pages_w1.tvinload_pagechk_atinit(fpath, 524288*((128+7)/8), 0, 0);
        fpath.delete();

        fpath.push_back(`TV_IN_w2);
        mem_blk_pages_w2 = mem_model_pages_with_diffofst#(128,8)::type_id::create("mem_blk_pages_w2");
        mem_blk_pages_w2.whole_page_size=8388864;
        mem_blk_pages_w2.maxi_bundlevar_fpath["s2"]=`TV_IN_OFFSET_s2;
        mem_blk_pages_w2.set_binary(1);
        mem_blk_pages_w2.tvinload_pagechk_atinit(fpath, 524288*((128+7)/8), 0, 0);
        fpath.delete();

        fpath.push_back(`TV_IN_w3);
        mem_blk_pages_w3 = mem_model_pages_with_diffofst#(128,8)::type_id::create("mem_blk_pages_w3");
        mem_blk_pages_w3.whole_page_size=8388864;
        mem_blk_pages_w3.maxi_bundlevar_fpath["s3"]=`TV_IN_OFFSET_s3;
        mem_blk_pages_w3.set_binary(1);
        mem_blk_pages_w3.tvinload_pagechk_atinit(fpath, 524288*((128+7)/8), 0, 0);
        fpath.delete();

        fork
            forever begin
                fork
                    begin
                        wait(write_data_finish_control);
                    end
                join
                `uvm_info("", "trigger_allaxilite_write_data_finish", UVM_LOW)
                @(posedge misc_if.clock);
                write_data_finish_control = 0;
                -> allaxilite_write_data_finish;
            end
            forever begin
                fork
                    begin
                        wait(read_data_finish_control);
                    end
                join
                `uvm_info("", "trigger_allaxilite_read_data_finish", UVM_LOW)
                @(posedge misc_if.clock);
                read_data_finish_control = 0;
                -> allaxilite_read_data_finish;
            end
            forever begin
                //this is non-pipeline case
                forever begin
                    @(negedge misc_if.clock);
                    if(misc_if.dut2tb_ap_done===1) break;
                end
                @(posedge misc_if.clock);
                @allaxilite_read_data_finish;
                @(posedge misc_if.clock);
                @allaxilite_write_data_finish;
                @(posedge misc_if.clock);
                -> ap_ready_for_nexttrans;
                `uvm_info(this.get_full_name(), "trigger event ap_ready_for_nexttrans", UVM_LOW)
                fork
                    begin
                        misc_if.ap_ready_for_nexttrans = 1;
                        @(posedge misc_if.clock);
                        misc_if.ap_ready_for_nexttrans = 0;
                    end
                join_none
            end
            forever begin
                forever begin
                    @(negedge misc_if.clock);
                    if(misc_if.dut2tb_ap_done===1) break;
                end
                @(posedge misc_if.clock);
                fork
                    begin
                        @(negedge misc_if.clock);
                        -> misc_if.dut2tb_ap_done_evt;
                        #0;
                        -> misc_if.dut2tb_ap_ready_evt;
                    end
                join_none
                @allaxilite_read_data_finish;
                @(posedge misc_if.clock);
                -> ap_done_for_nexttrans;
                `uvm_info(this.get_full_name(), "trigger event ap_done_for_nexttrans", UVM_LOW)
                fork
                    begin
                        misc_if.ap_done_for_nexttrans = 1;
                        @(posedge misc_if.clock);
                        misc_if.ap_done_for_nexttrans = 0;
                    end
                join_none
            end

            for(int i=1; i<1; i++) begin
                @dut2tb_ap_ready;
                mem_blk_pages_w0.incr_rd_page_idx() ;
                mem_blk_pages_w1.incr_rd_page_idx() ;
                mem_blk_pages_w2.incr_rd_page_idx() ;
                mem_blk_pages_w3.incr_rd_page_idx() ;
            end
            forever begin
                forever begin
                    @(negedge misc_if.clock);
                    if (misc_if.dut2tb_ap_ready === 1)   break;
                end
                @(posedge misc_if.clock);
                `uvm_info(this.get_full_name(), "trigger event DUT2TB_AP_READY", UVM_LOW)
                -> dut2tb_ap_ready;
                 misc_if.tb2dut_ap_start = 0;
            end
            forever begin
                forever begin
                    @(negedge misc_if.clock);
                    if (misc_if.dut2tb_ap_done_kernel === 1)   break;
                end
                @(posedge misc_if.clock);
                fork
                    begin
                        @(negedge misc_if.clock);
                        `uvm_info(this.get_full_name(), "trigger event dut2tb_ap_done_kernel_evt", UVM_LOW)
                        -> misc_if.dut2tb_ap_done_kernel_evt;
                    end
                join_none
            end
        join
    endtask

    virtual function void write_svr_master_tx(svr_transfer#(161) tr);
    //  trans_size++;
        svr_tx_delay = tr.delay;
        svr_tx_cov.sample();
        `uvm_info(this.get_full_name(), "port a collected one pkt", UVM_DEBUG);
    endfunction

    virtual function void write_svr_slave_rx(svr_transfer#(81) tr);
    //  trans_size++;
        svr_rx_delay = tr.delay;
        svr_rx_cov.sample();
        `uvm_info(this.get_full_name(), "port a collected one pkt", UVM_DEBUG);
    endfunction

    virtual function void write_axi_wtr_w0(axi_pkg::axi_transfer tr);
        mem_blk_pages_w0.write_elems_pipepage(tr.data,tr.byte_addr);
    endfunction

    virtual function void write_axi_rtr_w0(axi_pkg::axi_transfer tr);
    endfunction

    virtual function void write_axi_wtr_w1(axi_pkg::axi_transfer tr);
        mem_blk_pages_w1.write_elems_pipepage(tr.data,tr.byte_addr);
    endfunction

    virtual function void write_axi_rtr_w1(axi_pkg::axi_transfer tr);
    endfunction

    virtual function void write_axi_wtr_w2(axi_pkg::axi_transfer tr);
        mem_blk_pages_w2.write_elems_pipepage(tr.data,tr.byte_addr);
    endfunction

    virtual function void write_axi_rtr_w2(axi_pkg::axi_transfer tr);
    endfunction

    virtual function void write_axi_wtr_w3(axi_pkg::axi_transfer tr);
        mem_blk_pages_w3.write_elems_pipepage(tr.data,tr.byte_addr);
    endfunction

    virtual function void write_axi_rtr_w3(axi_pkg::axi_transfer tr);
    endfunction

    virtual function void write_axi_wtr_control(axi_pkg::axi_transfer tr);
        if(tr.addr == 0 && tr.len == 0 && tr.data[0][0]==1) begin //addr 0 and bit 0 are parameter
            -> write_start_finish;
            misc_if.tb2dut_ap_start = 1;
        end
    endfunction
    virtual function void write_axi_rtr_control(axi_pkg::axi_transfer tr);
            `uvm_info("receive axi read data", tr.sprint(), UVM_HIGH)
        if(tr.addr == 0 && tr.len == 0) begin
            if(tr.data[0][1]==1) begin  //bit 1 is parameter
                `uvm_info("status polling", "ap_done is polled", UVM_LOW);
                fork
                    begin
                        misc_if.dut2tb_ap_done = 1;
                        @(posedge misc_if.clock);
                        #0;
                        misc_if.dut2tb_ap_done = 0;
                        misc_if.tb2dut_ap_continue = 0;
                        -> dut2tb_ap_done;
                    end
                join_none
            end
            begin
                misc_if.dut2tb_ap_idle = tr.data[0][2];
            end
        end else begin
            mem_blk_pages_control_ap_return.write_elems_frontpage(tr.data, tr.byte_addr);
        end
    endfunction
endclass
`endif
