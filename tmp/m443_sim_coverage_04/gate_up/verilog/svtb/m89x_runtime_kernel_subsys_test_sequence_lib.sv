//==============================================================
//Vitis HLS - High-Level Synthesis from C, C++ and OpenCL v2026.1 (64-bit)
//Tool Version Limit: 2026.06
//Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
//Copyright 2022-2026 Advanced Micro Devices, Inc. All Rights Reserved.
//
//==============================================================
`ifndef M89X_RUNTIME_KERNEL_SUBSYS_TEST_SEQUENCE_LIB__SV                                              
    `define M89X_RUNTIME_KERNEL_SUBSYS_TEST_SEQUENCE_LIB__SV                                          
                                                                                                    
    `define AUTOTB_TVIN_tx_tx_TDATA  "../tv/cdatafile/c.m89x_runtime_kernel.autotvin_tx_V_data_V.dat" 
    `define AUTOTB_TVIN_tx_tx_TKEEP  "../tv/cdatafile/c.m89x_runtime_kernel.autotvin_tx_V_keep_V.dat" 
    `define AUTOTB_TVIN_tx_tx_TSTRB  "../tv/cdatafile/c.m89x_runtime_kernel.autotvin_tx_V_strb_V.dat" 
    `define AUTOTB_TVIN_tx_tx_TLAST  "../tv/cdatafile/c.m89x_runtime_kernel.autotvin_tx_V_last_V.dat" 
                                                                                                    
    `include "uvm_macros.svh"                                                                     
                                                                                                    
    // Delay kinds used in this test sequence                                                       
    typedef enum int {                                                                              
        TB_DELAY_NONE,                                                                              
        DELAY_DIRECTIO_BEFORE_FORCE,  // delay before force used in directio on s_axilite           
        DELAY_MAXI                    // delay for m_axi to make sure mem incr_rd_page_idx is called first
    } tb_delay_e;                                                                                   
                                                                                                    
    // Delay application task                                                                       
    task automatic tb_apply_delay(tb_delay_e kind);                                                 
        case (kind)                                                                                 
            TB_DELAY_NONE:                     ;         // no delay                                
            DELAY_DIRECTIO_BEFORE_FORCE: #0.001;                                                    
            DELAY_MAXI:                  #0.001;                                                    
            default:                           ;                                                    
        endcase                                                                                     
    endtask                                                                                         
                                                                                                    
    class m89x_runtime_kernel_subsys_test_sequence_lib extends uvm_sequence;                                
                                                                                                    
        function new (string name = "m89x_runtime_kernel_subsys_test_sequence_lib");                      
            super.new(name);                                                                        
            `uvm_info(this.get_full_name(), "new is called", UVM_LOW)                             
        endfunction                                                                                 
                                                                                                    
        `uvm_object_utils(m89x_runtime_kernel_subsys_test_sequence_lib)                                     
        `uvm_declare_p_sequencer(m89x_runtime_kernel_virtual_sequencer)                                     
                                                                                                    
        virtual task body();                                                                        
            uvm_phase starting_phase;                                                               
            virtual interface misc_interface misc_if;                                               
            m89x_runtime_kernel_reference_model refm;                                                       
                                                                                                    
            string file_queue_tx [$];                                                         
            integer bitwidth_queue_tx [$];                                                    
                                                                                                               
            svr_pkg::svr_master_sequence#(161) svr_port_tx_seq;            
            svr_pkg::svr_random_sequence#(161) svr_port_random_port_tx_seq;

            svr_pkg::svr_slave_sequence #(81) svr_port_rx_seq;            

            axi_pkg::axi_slave_sequence#(64,16,8,3,1) axi_slave_w0_seq;
            axi_pkg::axi_slave_sequence#(64,16,8,3,1) axi_slave_w1_seq;
            axi_pkg::axi_slave_sequence#(64,16,8,3,1) axi_slave_w2_seq;
            axi_pkg::axi_slave_sequence#(64,16,8,3,1) axi_slave_w3_seq;
            axi_pkg::axi_busdatas_master_sequence#(8, 32) axi_master_wr_control_seq;
            axi_pkg::axi_busdatas_master_sequence#(8, 32) axi_master_rd_control_seq;
            axi_pkg::axi_busdatas_master_sequence#(8, 32) axi_master_poll_control_seq;

            if (!uvm_config_db#(m89x_runtime_kernel_reference_model)::get(p_sequencer,"", "refm", refm))
                `uvm_fatal(this.get_full_name(), "No reference model")
            `uvm_info(this.get_full_name(), "get reference model by uvm_config_db", UVM_LOW)

            `uvm_info(this.get_full_name(), "body is called", UVM_LOW)
            starting_phase = this.get_starting_phase();
            if (starting_phase != null) begin
                `uvm_info(this.get_full_name(), "starting_phase not null", UVM_LOW)
                starting_phase.raise_objection(this);
            end
            else
                `uvm_info(this.get_full_name(), "starting_phase null" , UVM_LOW)

            misc_if = refm.misc_if;


            //phase_done.set_drain_time(this, 0ns);
            wait(refm.misc_if.reset === 1);
            ->refm.misc_if.initialed_evt;

            fork
                begin
                    fork
                        begin
                            string keystr_delay;
                            file_queue_tx.push_back(`AUTOTB_TVIN_tx_tx_TDATA);
                            bitwidth_queue_tx.push_back(128);

                            file_queue_tx.push_back(`AUTOTB_TVIN_tx_tx_TKEEP);
                            bitwidth_queue_tx.push_back(16);

                            file_queue_tx.push_back(`AUTOTB_TVIN_tx_tx_TSTRB);
                            bitwidth_queue_tx.push_back(16);

                            file_queue_tx.push_back(`AUTOTB_TVIN_tx_tx_TLAST);
                            bitwidth_queue_tx.push_back(1);

                            `uvm_create_on(svr_port_tx_seq, p_sequencer.svr_port_tx_sqr);
                            svr_port_tx_seq.misc_if = refm.misc_if;
                            svr_port_tx_seq.ap_done  = refm.ap_done_for_nexttrans ;
                            svr_port_tx_seq.ap_ready = refm.ap_ready_for_nexttrans;
                            svr_port_tx_seq.finish   = refm.finish;
                            svr_port_tx_seq.file_rd.config_file(file_queue_tx, bitwidth_queue_tx);
                            if( refm.m89x_runtime_kernel_cfg.port_tx_cfg.prt_type == AP_VLD ) wait(refm.misc_if.tb2dut_ap_start === 1'b1);
                            svr_port_tx_seq.isusr_delay = svr_pkg::NO_DELAY;
                            `uvm_send(svr_port_tx_seq);     
                        end                                               
                        begin
                            string keystr_delay;
                            `uvm_create_on(svr_port_rx_seq, p_sequencer.svr_port_rx_sqr);
                            svr_port_rx_seq.misc_if = refm.misc_if;
                            svr_port_rx_seq.ap_done  = refm.ap_done_for_nexttrans ;
                            svr_port_rx_seq.ap_ready = refm.ap_ready_for_nexttrans;
                            svr_port_rx_seq.finish   = refm.finish;
                            svr_port_rx_seq.isusr_delay = svr_pkg::NO_DELAY;
                            `uvm_send(svr_port_rx_seq);     
                        end                                               
                        begin //axi slave sequence. loop delays
                            `uvm_create_on(axi_slave_w0_seq, p_sequencer.w0_sqr);
                            axi_slave_w0_seq.misc_if = refm.misc_if;
                            axi_slave_w0_seq.ap_done    = refm.ap_done_for_nexttrans   ;
                            axi_slave_w0_seq.ap_ready   = refm.ap_ready_for_nexttrans  ;
                            axi_slave_w0_seq.finish     = refm.finish ;
                            axi_slave_w0_seq.isusr_delay = axi_pkg::NO_DELAY;
                            `uvm_send(axi_slave_w0_seq);
                        end
                        begin //axi slave sequence. loop delays
                            `uvm_create_on(axi_slave_w1_seq, p_sequencer.w1_sqr);
                            axi_slave_w1_seq.misc_if = refm.misc_if;
                            axi_slave_w1_seq.ap_done    = refm.ap_done_for_nexttrans   ;
                            axi_slave_w1_seq.ap_ready   = refm.ap_ready_for_nexttrans  ;
                            axi_slave_w1_seq.finish     = refm.finish ;
                            axi_slave_w1_seq.isusr_delay = axi_pkg::NO_DELAY;
                            `uvm_send(axi_slave_w1_seq);
                        end
                        begin //axi slave sequence. loop delays
                            `uvm_create_on(axi_slave_w2_seq, p_sequencer.w2_sqr);
                            axi_slave_w2_seq.misc_if = refm.misc_if;
                            axi_slave_w2_seq.ap_done    = refm.ap_done_for_nexttrans   ;
                            axi_slave_w2_seq.ap_ready   = refm.ap_ready_for_nexttrans  ;
                            axi_slave_w2_seq.finish     = refm.finish ;
                            axi_slave_w2_seq.isusr_delay = axi_pkg::NO_DELAY;
                            `uvm_send(axi_slave_w2_seq);
                        end
                        begin //axi slave sequence. loop delays
                            `uvm_create_on(axi_slave_w3_seq, p_sequencer.w3_sqr);
                            axi_slave_w3_seq.misc_if = refm.misc_if;
                            axi_slave_w3_seq.ap_done    = refm.ap_done_for_nexttrans   ;
                            axi_slave_w3_seq.ap_ready   = refm.ap_ready_for_nexttrans  ;
                            axi_slave_w3_seq.finish     = refm.finish ;
                            axi_slave_w3_seq.isusr_delay = axi_pkg::NO_DELAY;
                            `uvm_send(axi_slave_w3_seq);
                        end
                        begin
                            int control_page_idx_bak;
                            `uvm_create_on(axi_master_wr_control_seq, p_sequencer.control_sqr);
                            axi_master_wr_control_seq.misc_if = refm.misc_if;
                            axi_master_wr_control_seq.ap_done    = refm.ap_done_for_nexttrans   ;
                            axi_master_wr_control_seq.ap_ready   = refm.ap_ready_for_nexttrans  ;
                            axi_master_wr_control_seq.finish     = refm.finish ;
                            axi_master_wr_control_seq.isusr_delay = axi_pkg::NO_DELAY;
                            for(int i=0; i<1; i++) begin
                                logic[63:0] data64bit_s0[$];
                                logic[32-1:0] databusbit_s0[$];
                                logic[63:0] data64bit_s1[$];
                                logic[32-1:0] databusbit_s1[$];
                                logic[63:0] data64bit_s2[$];
                                logic[32-1:0] databusbit_s2[$];
                                logic[63:0] data64bit_s3[$];
                                logic[32-1:0] databusbit_s3[$];
                                logic[63:0] data64bit_config_r[$];
                                logic[32-1:0] databusbit_config_r[$];
                                data64bit_s0.delete(); databusbit_s0.delete();
                                axi_master_wr_control_seq.StableAxiliteNoUpdate=0;
                                for(int j=0; j < (64+32-1)/32; j++) begin
                                    data64bit_s0.push_back( ((refm.mem_blk_pages_w0.maxi_bundlevar_offset["s0"]+refm.mem_blk_pages_w0.page_ofst[refm.mem_blk_pages_w0.rd_page_idx])>>(j*32)) & (2**32-1) );
                                end
                                foreach(data64bit_s0[s]) databusbit_s0[s]=data64bit_s0[s][32-1:0];
                                axi_master_wr_control_seq.StableAxiliteNoUpdate=1;
                                axi_master_wr_control_seq.datamerge_inavg(databusbit_s0, 0, 24, 1);
                                data64bit_s1.delete(); databusbit_s1.delete();
                                axi_master_wr_control_seq.StableAxiliteNoUpdate=0;
                                for(int j=0; j < (64+32-1)/32; j++) begin
                                    data64bit_s1.push_back( ((refm.mem_blk_pages_w1.maxi_bundlevar_offset["s1"]+refm.mem_blk_pages_w1.page_ofst[refm.mem_blk_pages_w1.rd_page_idx])>>(j*32)) & (2**32-1) );
                                end
                                foreach(data64bit_s1[s]) databusbit_s1[s]=data64bit_s1[s][32-1:0];
                                axi_master_wr_control_seq.StableAxiliteNoUpdate=1;
                                axi_master_wr_control_seq.datamerge_inavg(databusbit_s1, 0, 36, 1);
                                data64bit_s2.delete(); databusbit_s2.delete();
                                axi_master_wr_control_seq.StableAxiliteNoUpdate=0;
                                for(int j=0; j < (64+32-1)/32; j++) begin
                                    data64bit_s2.push_back( ((refm.mem_blk_pages_w2.maxi_bundlevar_offset["s2"]+refm.mem_blk_pages_w2.page_ofst[refm.mem_blk_pages_w2.rd_page_idx])>>(j*32)) & (2**32-1) );
                                end
                                foreach(data64bit_s2[s]) databusbit_s2[s]=data64bit_s2[s][32-1:0];
                                axi_master_wr_control_seq.StableAxiliteNoUpdate=1;
                                axi_master_wr_control_seq.datamerge_inavg(databusbit_s2, 0, 48, 1);
                                data64bit_s3.delete(); databusbit_s3.delete();
                                axi_master_wr_control_seq.StableAxiliteNoUpdate=0;
                                for(int j=0; j < (64+32-1)/32; j++) begin
                                    data64bit_s3.push_back( ((refm.mem_blk_pages_w3.maxi_bundlevar_offset["s3"]+refm.mem_blk_pages_w3.page_ofst[refm.mem_blk_pages_w3.rd_page_idx])>>(j*32)) & (2**32-1) );
                                end
                                foreach(data64bit_s3[s]) databusbit_s3[s]=data64bit_s3[s][32-1:0];
                                axi_master_wr_control_seq.StableAxiliteNoUpdate=1;
                                axi_master_wr_control_seq.datamerge_inavg(databusbit_s3, 0, 60, 1);
                                data64bit_config_r.delete(); databusbit_config_r.delete();
                                axi_master_wr_control_seq.StableAxiliteNoUpdate=0;
                                refm.mem_blk_pages_control_config_r.tobusdata(data64bit_config_r, refm.mem_blk_pages_control_config_r.rd_page_idx, 32);
                                foreach(data64bit_config_r[s]) databusbit_config_r[s]=data64bit_config_r[s][32-1:0];
                                axi_master_wr_control_seq.StableAxiliteNoUpdate=1;
                                axi_master_wr_control_seq.datamerge_inavg(databusbit_config_r, 0, 128, 1);
                                `uvm_send(axi_master_wr_control_seq);
                                refm.write_data_finish_control = 1;
                                `uvm_info("control data writting thread", $sformatf("%0dth(total 1): waiting for all write data finish event",i), UVM_LOW)
                                wait(refm.allaxilite_write_data_finish.triggered);
                                refm.write_data_finish_control = 0;
                                fork
                                    begin // configure start to enable DUT
                                        axi_master_wr_control_seq.wr_addr_data.push_back( (1<<0)+(0<<32) );
                                        `uvm_info("control start dut by axilite", $sformatf("%0dth(total 1): begin to set start bit",i), UVM_LOW)
                                        `uvm_send(axi_master_wr_control_seq);
                                    end // end of configuration loop
                                    begin
                                        `uvm_info("control wait for ap_ready for next trans", $sformatf("%0dth(total 1): begin to wait",i), UVM_LOW)
                                        wait(refm.dut2tb_ap_ready.triggered);
                                        wait(refm.ap_done_for_nexttrans.triggered);
                                        tb_apply_delay(DELAY_MAXI); //make sure mem incr_rd_page_idx is called first
                                    end
                                join
                            end
                        end
                        begin
                            for(int j=0; j<1; j=j+refm.ap_done_cnt) begin
                                wait(misc_if.dut2tb_ap_done_kernel == 1);
                                `uvm_info("test finish control", $sformatf("ap_done of kernel is triggered"), UVM_LOW)
                                @(posedge misc_if.clock);
                                fork
                                    forever begin
                                        `uvm_create_on(axi_master_poll_control_seq, p_sequencer.control_sqr);
                                        axi_master_poll_control_seq.isusr_delay = axi_pkg::NO_DELAY;
                                        axi_master_poll_control_seq.misc_if = refm.misc_if;
                                        axi_master_poll_control_seq.rd_addr.push_back(0);
                                        `uvm_send(axi_master_poll_control_seq)
                                        repeat(2) @(posedge misc_if.clock);
                                    end
                                    begin
                                        `uvm_info("test finish control", $sformatf("%0dth(total 1) ap_done_for_nexttrans begin to wait",j), UVM_LOW)
                                        @refm.dut2tb_ap_done;
                                    end
                                join_any
                                disable fork;
                                wait(refm.ap_ready_for_nexttrans.triggered);
                            end
                        end
                        begin
                            `uvm_create_on(axi_master_rd_control_seq, p_sequencer.control_sqr)
                            axi_master_rd_control_seq.misc_if = refm.misc_if;
                            axi_master_rd_control_seq.ap_done    = refm.ap_done_for_nexttrans   ;
                            axi_master_rd_control_seq.ap_ready   = refm.ap_ready_for_nexttrans  ;
                            axi_master_rd_control_seq.finish     = refm.finish ;
                            axi_master_rd_control_seq.isusr_delay = axi_pkg::NO_DELAY;
                            for(int j=0; j<1; j=j+refm.ap_done_cnt) begin
                                logic[32-1:0] databusbit[$];
                                @refm.dut2tb_ap_done;
                                axi_master_rd_control_seq.datamerge_inavg(databusbit, (1*32+32-1)/32, 16, 0);
                                    `uvm_info("axilite data read", $sformatf("%0dth(total 1) data read sequence is started",j), UVM_LOW)
                                `uvm_send(axi_master_rd_control_seq);
                                @(posedge refm.misc_if.clock); //wait address 2 rdata rsp done
                                @(posedge refm.misc_if.clock);
                                refm.read_data_finish_control = 1;
                                wait(refm.allaxilite_read_data_finish.triggered);
                            end
                        end
                        begin
                            wait(svr_port_tx_seq);
                            forever begin
                                wait(svr_port_tx_seq.one_sect_read);
                                svr_port_tx_seq.one_sect_read = 0;
                                -> refm.allsvr_input_done;
                            end
                        end
                    join
                end

                begin
                    for(int j=0; j<1; j=j+refm.ap_done_cnt) @refm.ap_done_for_nexttrans;
                    `uvm_info(this.get_full_name(), "autotb finished", UVM_LOW)
                    -> refm.finish;
                    refm.misc_if.finished = 1;
                    @(posedge refm.misc_if.clock);
                    refm.misc_if.finished = 0;
                    @(posedge refm.misc_if.clock);
                    -> refm.misc_if.finished_evt;
                end
            join_any
            repeat(5) @(posedge refm.misc_if.clock); //5 cycles delay for finish stuff. 5 is haphazard value

            p_sequencer.svr_port_tx_sqr.stop_sequences();
            p_sequencer.svr_port_rx_sqr.stop_sequences();
            p_sequencer.w0_sqr.stop_sequences();
            p_sequencer.w1_sqr.stop_sequences();
            p_sequencer.w2_sqr.stop_sequences();
            p_sequencer.w3_sqr.stop_sequences();
            p_sequencer.control_sqr.stop_sequences();
            disable fork;
                                                                                                    
            starting_phase.drop_objection(this);                                                    
                                                                                                    
        endtask                                                                                     
    endclass                                                                                        
                                                                                                    
`endif                                                                                              
