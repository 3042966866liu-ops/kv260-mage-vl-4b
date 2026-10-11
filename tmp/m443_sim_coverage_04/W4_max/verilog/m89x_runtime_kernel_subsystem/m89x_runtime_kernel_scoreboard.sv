//==============================================================
//Vitis HLS - High-Level Synthesis from C, C++ and OpenCL v2026.1 (64-bit)
//Tool Version Limit: 2026.06
//Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
//Copyright 2022-2026 Advanced Micro Devices, Inc. All Rights Reserved.
//
//==============================================================
`ifndef M89X_RUNTIME_KERNEL_SCOREBOARD__SV                                                       
    `define M89X_RUNTIME_KERNEL_SCOREBOARD__SV                                                   
                                                                                               
    `define AUTOTB_TVOUT_rx_rx_TDATA_wrapc  "../tv/rtldatafile/rtl.m89x_runtime_kernel.autotvout_rx_V_data_V.dat"
    `define AUTOTB_TVOUT_rx_rx_TKEEP_wrapc  "../tv/rtldatafile/rtl.m89x_runtime_kernel.autotvout_rx_V_keep_V.dat"
    `define AUTOTB_TVOUT_rx_rx_TSTRB_wrapc  "../tv/rtldatafile/rtl.m89x_runtime_kernel.autotvout_rx_V_strb_V.dat"
    `define AUTOTB_TVOUT_rx_rx_TLAST_wrapc  "../tv/rtldatafile/rtl.m89x_runtime_kernel.autotvout_rx_V_last_V.dat"
    `define STREAM_SIZE_OUT_rx_rx_TDATA  "../tv/stream_size/stream_size_out_rx_V_data_V.dat"
    `define STREAM_SIZE_OUT_rx_rx_TKEEP  "../tv/stream_size/stream_size_out_rx_V_keep_V.dat"
    `define STREAM_SIZE_OUT_rx_rx_TSTRB  "../tv/stream_size/stream_size_out_rx_V_strb_V.dat"
    `define STREAM_SIZE_OUT_rx_rx_TLAST  "../tv/stream_size/stream_size_out_rx_V_last_V.dat"
                                                                                               
    class m89x_runtime_kernel_scoreboard extends uvm_component;                                        
                                                                                               
        m89x_runtime_kernel_reference_model refm;                                                      
                                                                                               
        typedef integer TRANS_SIZE_QUEUE_TYPE [$];                                      
        TRANS_SIZE_QUEUE_TYPE TVOUT_transaction_size_queue;                                
        int write_file_done_rx_rx_TDATA;                                                          
        int write_file_done_rx_rx_TKEEP;                                                          
        int write_file_done_rx_rx_TSTRB;                                                          
        int write_file_done_rx_rx_TLAST;                                                          
        int write_section_done_rx_rx_TDATA = 0;                                                   
        int write_section_done_rx_rx_TKEEP = 0;                                                   
        int write_section_done_rx_rx_TSTRB = 0;                                                   
        int write_section_done_rx_rx_TLAST = 0;                                                   
                                                                                           
        file_agent_pkg::file_read_agent#(32) file_rd_TVOUT_transaction_size;               
        file_agent_pkg::file_write_agent#(64) file_wr_port_rx_rx_TDATA;
        file_agent_pkg::file_write_agent#(8) file_wr_port_rx_rx_TKEEP;
        file_agent_pkg::file_write_agent#(8) file_wr_port_rx_rx_TSTRB;
        file_agent_pkg::file_write_agent#(1) file_wr_port_rx_rx_TLAST;
                                                                                               
        `uvm_component_utils_begin(m89x_runtime_kernel_scoreboard)                                     
        `uvm_field_object(refm  , UVM_DEFAULT)                                                 
        `uvm_field_object(file_rd_TVOUT_transaction_size, UVM_DEFAULT)
        `uvm_field_queue_int(TVOUT_transaction_size_queue, UVM_DEFAULT)                    
        `uvm_field_object(file_wr_port_rx_rx_TDATA, UVM_DEFAULT)
        `uvm_field_int(write_file_done_rx_rx_TDATA, UVM_DEFAULT)
        `uvm_field_int(write_section_done_rx_rx_TDATA, UVM_DEFAULT)
        `uvm_field_object(file_wr_port_rx_rx_TKEEP, UVM_DEFAULT)
        `uvm_field_int(write_file_done_rx_rx_TKEEP, UVM_DEFAULT)
        `uvm_field_int(write_section_done_rx_rx_TKEEP, UVM_DEFAULT)
        `uvm_field_object(file_wr_port_rx_rx_TSTRB, UVM_DEFAULT)
        `uvm_field_int(write_file_done_rx_rx_TSTRB, UVM_DEFAULT)
        `uvm_field_int(write_section_done_rx_rx_TSTRB, UVM_DEFAULT)
        `uvm_field_object(file_wr_port_rx_rx_TLAST, UVM_DEFAULT)
        `uvm_field_int(write_file_done_rx_rx_TLAST, UVM_DEFAULT)
        `uvm_field_int(write_section_done_rx_rx_TLAST, UVM_DEFAULT)
        `uvm_component_utils_end                                                               
                                                                                               
        virtual function void build_phase(uvm_phase phase);                                    
            if (!uvm_config_db #(m89x_runtime_kernel_reference_model)::get(this, "", "refm", refm))
                `uvm_fatal(this.get_full_name(), "No refm from high level")                  
            `uvm_info(this.get_full_name(), "get reference model by uvm_config_db", UVM_MEDIUM) 
            file_rd_TVOUT_transaction_size = file_agent_pkg::file_read_agent#(32)::type_id::create("file_rd_TVOUT_transaction_size", this);
                                                                                               
            file_wr_port_rx_rx_TDATA = file_agent_pkg::file_write_agent#(64)::type_id::create("file_wr_port_rx_rx_TDATA", this);
            file_wr_port_rx_rx_TKEEP = file_agent_pkg::file_write_agent#(8)::type_id::create("file_wr_port_rx_rx_TKEEP", this);
            file_wr_port_rx_rx_TSTRB = file_agent_pkg::file_write_agent#(8)::type_id::create("file_wr_port_rx_rx_TSTRB", this);
            file_wr_port_rx_rx_TLAST = file_agent_pkg::file_write_agent#(1)::type_id::create("file_wr_port_rx_rx_TLAST", this);
        endfunction                                                                            
                                                                                               
        function new (string name = "", uvm_component parent = null);                        
            super.new(name, parent);                                                           
            write_file_done_rx_rx_TDATA = 0;                                                          
            write_file_done_rx_rx_TKEEP = 0;                                                          
            write_file_done_rx_rx_TSTRB = 0;                                                          
            write_file_done_rx_rx_TLAST = 0;                                                          
        endfunction                                                                            
                                                                                               
        virtual task run_phase(uvm_phase phase);                                               
            create_TVOUT_transaction_size_queue_by_file(`STREAM_SIZE_OUT_rx_rx_TDATA);
            file_wr_port_rx_rx_TDATA.config_file(   
                    `AUTOTB_TVOUT_rx_rx_TDATA_wrapc,
                    TVOUT_transaction_size_queue                            
                );                                                          
                                                                            
            create_TVOUT_transaction_size_queue_by_file(`STREAM_SIZE_OUT_rx_rx_TKEEP);
            file_wr_port_rx_rx_TKEEP.config_file(   
                    `AUTOTB_TVOUT_rx_rx_TKEEP_wrapc,
                    TVOUT_transaction_size_queue                            
                );                                                          
                                                                            
            create_TVOUT_transaction_size_queue_by_file(`STREAM_SIZE_OUT_rx_rx_TSTRB);
            file_wr_port_rx_rx_TSTRB.config_file(   
                    `AUTOTB_TVOUT_rx_rx_TSTRB_wrapc,
                    TVOUT_transaction_size_queue                            
                );                                                          
                                                                            
            create_TVOUT_transaction_size_queue_by_file(`STREAM_SIZE_OUT_rx_rx_TLAST);
            file_wr_port_rx_rx_TLAST.config_file(   
                    `AUTOTB_TVOUT_rx_rx_TLAST_wrapc,
                    TVOUT_transaction_size_queue                            
                );                                                          
                                                                            

            fork                                                                               
                forever begin
                    @refm.allaxilite_write_data_finish;
                    `uvm_info(this.get_full_name(), "receive allaxilite_write_finish axilite write_mem_page_process", UVM_LOW)
                    void'(refm.mem_blk_pages_control_config_r.pages.pop_front());
                end
                forever begin
                    @refm.allaxilite_read_data_finish;
                    `uvm_info(this.get_full_name(), "receive allaxilite_read_data_finish axilite_read_mem_page_process", UVM_LOW)
                    refm.mem_blk_pages_control_ap_return.tvout_dump_frontpage(1);
                end
                                                                                               
                forever begin
                    @refm.dut2tb_ap_done;
                    `uvm_info(this.get_full_name(), "receive dut2tb_ap_done and do axim dump", UVM_LOW)
                            refm.mem_blk_pages_w0.tvout_dump_frontpage(0);
                            refm.mem_blk_pages_w1.tvout_dump_frontpage(0);
                            refm.mem_blk_pages_w2.tvout_dump_frontpage(0);
                            refm.mem_blk_pages_w3.tvout_dump_frontpage(0);
                    file_wr_port_rx_rx_TDATA.receive_ap_done();
                    file_wr_port_rx_rx_TKEEP.receive_ap_done();
                    file_wr_port_rx_rx_TSTRB.receive_ap_done();
                    file_wr_port_rx_rx_TLAST.receive_ap_done();
                end                                                                            
                begin                                                                          
                    @refm.finish;                                                              
                    `uvm_info(this.get_full_name(), "receive FINISH", UVM_LOW)               
                    file_wr_port_rx_rx_TDATA.wait_write_file_done();
                    file_wr_port_rx_rx_TKEEP.wait_write_file_done();
                    file_wr_port_rx_rx_TSTRB.wait_write_file_done();
                    file_wr_port_rx_rx_TLAST.wait_write_file_done();
                end                                                                            
                begin                                                                      
                    forever begin                                                              
                        wait(write_section_done_rx_rx_TDATA && write_section_done_rx_rx_TKEEP && write_section_done_rx_rx_TSTRB && write_section_done_rx_rx_TLAST);                          
                        write_section_done_rx_rx_TDATA = 0;                                               
                        write_section_done_rx_rx_TKEEP = 0;                                               
                        write_section_done_rx_rx_TSTRB = 0;                                               
                        write_section_done_rx_rx_TLAST = 0;                                               
                        -> refm.allsvr_output_done;                                         
                    end                                                                        
                end                                                                        
            join                                                                               
        endtask                                                                                
                                                                                               
         virtual function void create_TVOUT_transaction_size_queue_by_file(string TVOUT_file); 
             typedef bit [31: 0] DATA_QUEUE_TYPE [$];                                     
             DATA_QUEUE_TYPE TV_Queue [$];                                                  
             DATA_QUEUE_TYPE TV;                                                               
             string file_queue [$];                                                         
             integer bitwidth_queue [$];                                                    
             file_queue.push_back(TVOUT_file);                                                 
             bitwidth_queue.push_back(32);                                                     
                                                                                               
             file_rd_TVOUT_transaction_size.config_file(                                       
                 file_queue,                                                                   
                 bitwidth_queue                                                                
             );                                                                                
                                                                                               
             file_rd_TVOUT_transaction_size.read_TVIN_file();                                  
                                                                                               
             TV_Queue = file_rd_TVOUT_transaction_size.TV_Queue;                               
             TVOUT_transaction_size_queue.delete();                                            
             while (TV_Queue.size() > 0) begin                                                 
                 TV = TV_Queue.pop_front();                                                    
                 if (TV.size() != 1)                                                           
                         `uvm_fatal(this.get_full_name(), $sformatf("number of each transaction size should be 1, read %0d in file %0s   ", TV.size(), TVOUT_file))
                 `uvm_info(this.get_full_name(), $sformatf("get transaction size %0d", TV[0]), UVM_MEDIUM)
                 TVOUT_transaction_size_queue.push_back(TV.pop_front());                       
             end                                                                               
         endfunction                                                                           
                                                                                               
        virtual function void write_svr_master_tx(svr_transfer#(161) tr);
            `uvm_info(this.get_full_name(), "port tx collected one pkt", UVM_DEBUG);          
        endfunction
                   
        virtual function void write_svr_slave_rx(svr_transfer#(81) tr);
            `uvm_info(this.get_full_name(), "port rx collected one pkt", UVM_DEBUG);          
            file_wr_port_rx_rx_TDATA.write_TVOUT_data(tr.data[63: 0]);
            write_file_done_rx_rx_TDATA = file_wr_port_rx_rx_TDATA.is_write_file_done();
            write_section_done_rx_rx_TDATA = file_wr_port_rx_rx_TDATA.is_write_section_done();
            if(write_section_done_rx_rx_TDATA) 
                `uvm_info("rx rx data done", "signal name:rx_TDATA", UVM_MEDIUM)
            file_wr_port_rx_rx_TKEEP.write_TVOUT_data(tr.data[71: 64]);
            write_file_done_rx_rx_TKEEP = file_wr_port_rx_rx_TKEEP.is_write_file_done();
            write_section_done_rx_rx_TKEEP = file_wr_port_rx_rx_TKEEP.is_write_section_done();
            if(write_section_done_rx_rx_TKEEP) 
                `uvm_info("rx rx data done", "signal name:rx_TKEEP", UVM_MEDIUM)
            file_wr_port_rx_rx_TSTRB.write_TVOUT_data(tr.data[79: 72]);
            write_file_done_rx_rx_TSTRB = file_wr_port_rx_rx_TSTRB.is_write_file_done();
            write_section_done_rx_rx_TSTRB = file_wr_port_rx_rx_TSTRB.is_write_section_done();
            if(write_section_done_rx_rx_TSTRB) 
                `uvm_info("rx rx data done", "signal name:rx_TSTRB", UVM_MEDIUM)
            file_wr_port_rx_rx_TLAST.write_TVOUT_data(tr.data[80: 80]);
            write_file_done_rx_rx_TLAST = file_wr_port_rx_rx_TLAST.is_write_file_done();
            write_section_done_rx_rx_TLAST = file_wr_port_rx_rx_TLAST.is_write_section_done();
            if(write_section_done_rx_rx_TLAST) 
                `uvm_info("rx rx data done", "signal name:rx_TLAST", UVM_MEDIUM)
        endfunction
                   
        virtual function void write_axi_wtr_w0(axi_pkg::axi_transfer tr);
        endfunction

        virtual function void write_axi_rtr_w0(axi_pkg::axi_transfer tr);
        endfunction

        virtual function void write_axi_wtr_w1(axi_pkg::axi_transfer tr);
        endfunction

        virtual function void write_axi_rtr_w1(axi_pkg::axi_transfer tr);
        endfunction

        virtual function void write_axi_wtr_w2(axi_pkg::axi_transfer tr);
        endfunction

        virtual function void write_axi_rtr_w2(axi_pkg::axi_transfer tr);
        endfunction

        virtual function void write_axi_wtr_w3(axi_pkg::axi_transfer tr);
        endfunction

        virtual function void write_axi_rtr_w3(axi_pkg::axi_transfer tr);
        endfunction

        virtual function void write_axi_wtr_control(axi_pkg::axi_transfer tr);
        endfunction

        virtual function void write_axi_rtr_control(axi_pkg::axi_transfer tr);
        endfunction

    endclass                                                                                   
                                                                                               
`endif                                                                                         
