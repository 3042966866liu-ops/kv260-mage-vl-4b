//==============================================================
//Vitis HLS - High-Level Synthesis from C, C++ and OpenCL v2026.1 (64-bit)
//Tool Version Limit: 2026.06
//Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
//Copyright 2022-2026 Advanced Micro Devices, Inc. All Rights Reserved.
//
//==============================================================
`ifndef M89X_RUNTIME_KERNEL_ENV__SV                                                                                   
    `define M89X_RUNTIME_KERNEL_ENV__SV                                                                               
                                                                                                                    
    class svr_latency_tx extends svr_latency;
        rand int    transfer_latency;
        `uvm_object_utils_begin(svr_latency_tx)
        `uvm_object_utils_end
        function new ( string name = "svr_latency_tx" );
            super.new(name);
        endfunction
        virtual function int get_transfer_lat();
            int delay;
            void'(std::randomize(delay) with {
				delay dist {0:=8, 0:=1, 256:=1, [0:256]:/2};
				delay inside {[0:256]};
				});
            transfer_latency = delay;
            return transfer_latency;
        endfunction
    endclass

    class svr_latency_rx extends svr_latency;
        rand int    transfer_latency;
        `uvm_object_utils_begin(svr_latency_rx)
        `uvm_object_utils_end
        function new ( string name = "svr_latency_rx" );
            super.new(name);
        endfunction
        virtual function int get_transfer_lat();
            int delay;
            void'(std::randomize(delay) with {
				delay dist {0:=8, 0:=1, 256:=1, [0:256]:/2};
				delay inside {[0:256]};
				});
            transfer_latency = delay;
            return transfer_latency;
        endfunction
    endclass

    class axi_latency_w0 extends axi_latency;
        rand int    wctrl_latency;
        rand int    wdata_latency;
        rand int    wbrsp_latency;
        rand int    rctrl_latency;
        rand int    rdata_latency;
        `uvm_object_utils_begin(axi_latency_w0)
        `uvm_object_utils_end
        function new ( string name = "axi_latency_w0" );
            super.new(name);
        endfunction
        virtual function int get_wctrl_lat();
            int delay;
            void'(std::randomize(delay) with {
				delay dist {0:=8, 0:=1, 256:=1, [0:256]:/2};
				delay inside {[0:256]};
				});
            wctrl_latency = delay;
            return wctrl_latency;
        endfunction
        virtual function int get_wdata_lat();
            int delay;
            void'(std::randomize(delay) with {
				delay dist {0:=8, 0:=1, 256:=1, [0:256]:/2};
				delay inside {[0:256]};
				});
            wdata_latency = delay;
            return wdata_latency;
        endfunction
        virtual function int get_wbrsp_lat();
            int delay;
            void'(std::randomize(delay) with {
				delay dist {0:=8, 0:=1, 256:=1, [0:256]:/2};
				delay inside {[0:256]};
				});
            wbrsp_latency = delay;
            return wbrsp_latency;
        endfunction
        virtual function int get_rctrl_lat();
            int delay;
            void'(std::randomize(delay) with {
				delay dist {0:=8, 0:=1, 256:=1, [0:256]:/2};
				delay inside {[0:256]};
				});
            rctrl_latency = delay;
            return rctrl_latency;
        endfunction
        virtual function int get_rdata_lat();
            int delay;
            void'(std::randomize(delay) with {
				delay dist {0:=8, 0:=1, 256:=1, [0:256]:/2};
				delay inside {[0:256]};
				});
            rdata_latency = delay;
            return rdata_latency;
        endfunction
    endclass

    class axi_latency_w1 extends axi_latency;
        rand int    wctrl_latency;
        rand int    wdata_latency;
        rand int    wbrsp_latency;
        rand int    rctrl_latency;
        rand int    rdata_latency;
        `uvm_object_utils_begin(axi_latency_w1)
        `uvm_object_utils_end
        function new ( string name = "axi_latency_w1" );
            super.new(name);
        endfunction
        virtual function int get_wctrl_lat();
            int delay;
            void'(std::randomize(delay) with {
				delay dist {0:=8, 0:=1, 256:=1, [0:256]:/2};
				delay inside {[0:256]};
				});
            wctrl_latency = delay;
            return wctrl_latency;
        endfunction
        virtual function int get_wdata_lat();
            int delay;
            void'(std::randomize(delay) with {
				delay dist {0:=8, 0:=1, 256:=1, [0:256]:/2};
				delay inside {[0:256]};
				});
            wdata_latency = delay;
            return wdata_latency;
        endfunction
        virtual function int get_wbrsp_lat();
            int delay;
            void'(std::randomize(delay) with {
				delay dist {0:=8, 0:=1, 256:=1, [0:256]:/2};
				delay inside {[0:256]};
				});
            wbrsp_latency = delay;
            return wbrsp_latency;
        endfunction
        virtual function int get_rctrl_lat();
            int delay;
            void'(std::randomize(delay) with {
				delay dist {0:=8, 0:=1, 256:=1, [0:256]:/2};
				delay inside {[0:256]};
				});
            rctrl_latency = delay;
            return rctrl_latency;
        endfunction
        virtual function int get_rdata_lat();
            int delay;
            void'(std::randomize(delay) with {
				delay dist {0:=8, 0:=1, 256:=1, [0:256]:/2};
				delay inside {[0:256]};
				});
            rdata_latency = delay;
            return rdata_latency;
        endfunction
    endclass

    class axi_latency_w2 extends axi_latency;
        rand int    wctrl_latency;
        rand int    wdata_latency;
        rand int    wbrsp_latency;
        rand int    rctrl_latency;
        rand int    rdata_latency;
        `uvm_object_utils_begin(axi_latency_w2)
        `uvm_object_utils_end
        function new ( string name = "axi_latency_w2" );
            super.new(name);
        endfunction
        virtual function int get_wctrl_lat();
            int delay;
            void'(std::randomize(delay) with {
				delay dist {0:=8, 0:=1, 256:=1, [0:256]:/2};
				delay inside {[0:256]};
				});
            wctrl_latency = delay;
            return wctrl_latency;
        endfunction
        virtual function int get_wdata_lat();
            int delay;
            void'(std::randomize(delay) with {
				delay dist {0:=8, 0:=1, 256:=1, [0:256]:/2};
				delay inside {[0:256]};
				});
            wdata_latency = delay;
            return wdata_latency;
        endfunction
        virtual function int get_wbrsp_lat();
            int delay;
            void'(std::randomize(delay) with {
				delay dist {0:=8, 0:=1, 256:=1, [0:256]:/2};
				delay inside {[0:256]};
				});
            wbrsp_latency = delay;
            return wbrsp_latency;
        endfunction
        virtual function int get_rctrl_lat();
            int delay;
            void'(std::randomize(delay) with {
				delay dist {0:=8, 0:=1, 256:=1, [0:256]:/2};
				delay inside {[0:256]};
				});
            rctrl_latency = delay;
            return rctrl_latency;
        endfunction
        virtual function int get_rdata_lat();
            int delay;
            void'(std::randomize(delay) with {
				delay dist {0:=8, 0:=1, 256:=1, [0:256]:/2};
				delay inside {[0:256]};
				});
            rdata_latency = delay;
            return rdata_latency;
        endfunction
    endclass

    class axi_latency_w3 extends axi_latency;
        rand int    wctrl_latency;
        rand int    wdata_latency;
        rand int    wbrsp_latency;
        rand int    rctrl_latency;
        rand int    rdata_latency;
        `uvm_object_utils_begin(axi_latency_w3)
        `uvm_object_utils_end
        function new ( string name = "axi_latency_w3" );
            super.new(name);
        endfunction
        virtual function int get_wctrl_lat();
            int delay;
            void'(std::randomize(delay) with {
				delay dist {0:=8, 0:=1, 256:=1, [0:256]:/2};
				delay inside {[0:256]};
				});
            wctrl_latency = delay;
            return wctrl_latency;
        endfunction
        virtual function int get_wdata_lat();
            int delay;
            void'(std::randomize(delay) with {
				delay dist {0:=8, 0:=1, 256:=1, [0:256]:/2};
				delay inside {[0:256]};
				});
            wdata_latency = delay;
            return wdata_latency;
        endfunction
        virtual function int get_wbrsp_lat();
            int delay;
            void'(std::randomize(delay) with {
				delay dist {0:=8, 0:=1, 256:=1, [0:256]:/2};
				delay inside {[0:256]};
				});
            wbrsp_latency = delay;
            return wbrsp_latency;
        endfunction
        virtual function int get_rctrl_lat();
            int delay;
            void'(std::randomize(delay) with {
				delay dist {0:=8, 0:=1, 256:=1, [0:256]:/2};
				delay inside {[0:256]};
				});
            rctrl_latency = delay;
            return rctrl_latency;
        endfunction
        virtual function int get_rdata_lat();
            int delay;
            void'(std::randomize(delay) with {
				delay dist {0:=8, 0:=1, 256:=1, [0:256]:/2};
				delay inside {[0:256]};
				});
            rdata_latency = delay;
            return rdata_latency;
        endfunction
    endclass

    class axi_latency_control extends axi_latency;
        rand int    wctrl_latency;
        rand int    wdata_latency;
        rand int    wbrsp_latency;
        rand int    rctrl_latency;
        rand int    rdata_latency;
        `uvm_object_utils_begin(axi_latency_control)
        `uvm_object_utils_end
        function new ( string name = "axi_latency_control" );
            super.new(name);
        endfunction
        virtual function int get_wctrl_lat();
            int delay;
            void'(std::randomize(delay) with {
				delay dist {0:=8, 0:=1, 256:=1, [0:256]:/2};
				delay inside {[0:256]};
				});
            wctrl_latency = delay;
            return wctrl_latency;
        endfunction
        virtual function int get_wdata_lat();
            int delay;
            void'(std::randomize(delay) with {
				delay dist {0:=8, 0:=1, 256:=1, [0:256]:/2};
				delay inside {[0:256]};
				});
            wdata_latency = delay;
            return wdata_latency;
        endfunction
        virtual function int get_wbrsp_lat();
            int delay;
            void'(std::randomize(delay) with {
				delay dist {0:=8, 0:=1, 256:=1, [0:256]:/2};
				delay inside {[0:256]};
				});
            wbrsp_latency = delay;
            return wbrsp_latency;
        endfunction
        virtual function int get_rctrl_lat();
            int delay;
            void'(std::randomize(delay) with {
				delay dist {0:=8, 0:=1, 256:=1, [0:256]:/2};
				delay inside {[0:256]};
				});
            rctrl_latency = delay;
            return rctrl_latency;
        endfunction
        virtual function int get_rdata_lat();
            int delay;
            void'(std::randomize(delay) with {
				delay dist {0:=8, 0:=1, 256:=1, [0:256]:/2};
				delay inside {[0:256]};
				});
            rdata_latency = delay;
            return rdata_latency;
        endfunction
    endclass

                                                                                                                    
    class m89x_runtime_kernel_env extends uvm_env;                                                                          
                                                                                                                    
        svr_latency_tx    lat_tx;
        svr_latency_rx    lat_rx;
        axi_latency_w0    lat_w0;
        axi_latency_w1    lat_w1;
        axi_latency_w2    lat_w2;
        axi_latency_w3    lat_w3;
        axi_latency_control    lat_control;
        m89x_runtime_kernel_virtual_sequencer m89x_runtime_kernel_virtual_sqr;                                                      
        m89x_runtime_kernel_config m89x_runtime_kernel_cfg;                                                                         
                                                                                                                    
        svr_pkg::svr_env#(161) env_master_svr_tx;
        svr_pkg::svr_env#(81) env_slave_svr_rx;
        axi_pkg::axi_env#(64,16,8,3,1) axi_master_w0;
        axi_pkg::axi_env#(64,16,8,3,1) axi_master_w1;
        axi_pkg::axi_env#(64,16,8,3,1) axi_master_w2;
        axi_pkg::axi_env#(64,16,8,3,1) axi_master_w3;
        axi_pkg::axi_env#(8,4,4,3,1) axi_lite_control;
                                                                                                                    
        m89x_runtime_kernel_reference_model   refm;                                                                         
                                                                                                                    
        m89x_runtime_kernel_subsystem_monitor subsys_mon;                                                                   
                                                                                                                    
        `uvm_component_utils_begin(m89x_runtime_kernel_env)                                                                 
        `uvm_field_object (env_master_svr_tx,  UVM_DEFAULT | UVM_REFERENCE)
        `uvm_field_object (env_slave_svr_rx,  UVM_DEFAULT | UVM_REFERENCE)
        `uvm_field_object (refm, UVM_DEFAULT | UVM_REFERENCE)                                                       
        `uvm_field_object (m89x_runtime_kernel_virtual_sqr, UVM_DEFAULT | UVM_REFERENCE)                                    
        `uvm_field_object (m89x_runtime_kernel_cfg        , UVM_DEFAULT)                                                    
        `uvm_component_utils_end                                                                                    
                                                                                                                    
        function new (string name = "m89x_runtime_kernel_env", uvm_component parent = null);                              
            super.new(name, parent);                                                                                
        endfunction                                                                                                 
                                                                                                                    
        extern virtual function void build_phase(uvm_phase phase);                                                  
        extern virtual function void connect_phase(uvm_phase phase);                                                
        extern virtual task          run_phase(uvm_phase phase);                                                    
                                                                                                                    
    endclass                                                                                                        
                                                                                                                    
    function void m89x_runtime_kernel_env::build_phase(uvm_phase phase);                                                    
        super.build_phase(phase);                                                                                   
        m89x_runtime_kernel_cfg = m89x_runtime_kernel_config::type_id::create("m89x_runtime_kernel_cfg", this);                           
                                                                                                                    
        m89x_runtime_kernel_cfg.port_tx_cfg.svr_type = svr_pkg::SVR_MASTER ;
        env_master_svr_tx  = svr_env#(161)::type_id::create("env_master_svr_tx", this);
        uvm_config_db#(svr_pkg::svr_config)::set(this, "env_master_svr_tx*", "cfg", m89x_runtime_kernel_cfg.port_tx_cfg);
        m89x_runtime_kernel_cfg.port_tx_cfg.prt_type = svr_pkg::AXIS;
        m89x_runtime_kernel_cfg.port_tx_cfg.is_active = svr_pkg::SVR_ACTIVE;
        m89x_runtime_kernel_cfg.port_tx_cfg.spec_cfg = svr_pkg::NORMAL;
        m89x_runtime_kernel_cfg.port_tx_cfg.reset_level = svr_pkg::RESET_LEVEL_LOW;
 
        m89x_runtime_kernel_cfg.port_rx_cfg.svr_type = svr_pkg::SVR_SLAVE ;
        env_slave_svr_rx  = svr_env#(81)::type_id::create("env_slave_svr_rx", this);
        uvm_config_db#(svr_pkg::svr_config)::set(this, "env_slave_svr_rx*", "cfg", m89x_runtime_kernel_cfg.port_rx_cfg);
        m89x_runtime_kernel_cfg.port_rx_cfg.prt_type = svr_pkg::AXIS;
        m89x_runtime_kernel_cfg.port_rx_cfg.is_active = svr_pkg::SVR_ACTIVE;
        m89x_runtime_kernel_cfg.port_rx_cfg.spec_cfg = svr_pkg::NORMAL;
        m89x_runtime_kernel_cfg.port_rx_cfg.reset_level = svr_pkg::RESET_LEVEL_LOW;
 
        lat_tx = svr_latency_tx::type_id::create("lat_tx", this);
        m89x_runtime_kernel_cfg.port_tx_cfg.clatency = lat_tx;
        lat_rx = svr_latency_rx::type_id::create("lat_rx", this);
        m89x_runtime_kernel_cfg.port_rx_cfg.clatency = lat_rx;

        m89x_runtime_kernel_cfg.w0_cfg.set_default();
        m89x_runtime_kernel_cfg.w0_cfg.drv_type = axi_pkg::SLAVE;
        m89x_runtime_kernel_cfg.w0_cfg.reset_level = axi_pkg::RESET_LEVEL_LOW;
        lat_w0 = axi_latency_w0::type_id::create("lat_w0", this);
        m89x_runtime_kernel_cfg.w0_cfg.clatency = lat_w0;
        uvm_config_db#(axi_pkg::axi_cfg)::set(this, "axi_master_w0*", "cfg", m89x_runtime_kernel_cfg.w0_cfg);
        axi_master_w0 = axi_pkg::axi_env#(64,16,8,3,1)::type_id::create("axi_master_w0", this);

        m89x_runtime_kernel_cfg.w1_cfg.set_default();
        m89x_runtime_kernel_cfg.w1_cfg.drv_type = axi_pkg::SLAVE;
        m89x_runtime_kernel_cfg.w1_cfg.reset_level = axi_pkg::RESET_LEVEL_LOW;
        lat_w1 = axi_latency_w1::type_id::create("lat_w1", this);
        m89x_runtime_kernel_cfg.w1_cfg.clatency = lat_w1;
        uvm_config_db#(axi_pkg::axi_cfg)::set(this, "axi_master_w1*", "cfg", m89x_runtime_kernel_cfg.w1_cfg);
        axi_master_w1 = axi_pkg::axi_env#(64,16,8,3,1)::type_id::create("axi_master_w1", this);

        m89x_runtime_kernel_cfg.w2_cfg.set_default();
        m89x_runtime_kernel_cfg.w2_cfg.drv_type = axi_pkg::SLAVE;
        m89x_runtime_kernel_cfg.w2_cfg.reset_level = axi_pkg::RESET_LEVEL_LOW;
        lat_w2 = axi_latency_w2::type_id::create("lat_w2", this);
        m89x_runtime_kernel_cfg.w2_cfg.clatency = lat_w2;
        uvm_config_db#(axi_pkg::axi_cfg)::set(this, "axi_master_w2*", "cfg", m89x_runtime_kernel_cfg.w2_cfg);
        axi_master_w2 = axi_pkg::axi_env#(64,16,8,3,1)::type_id::create("axi_master_w2", this);

        m89x_runtime_kernel_cfg.w3_cfg.set_default();
        m89x_runtime_kernel_cfg.w3_cfg.drv_type = axi_pkg::SLAVE;
        m89x_runtime_kernel_cfg.w3_cfg.reset_level = axi_pkg::RESET_LEVEL_LOW;
        lat_w3 = axi_latency_w3::type_id::create("lat_w3", this);
        m89x_runtime_kernel_cfg.w3_cfg.clatency = lat_w3;
        uvm_config_db#(axi_pkg::axi_cfg)::set(this, "axi_master_w3*", "cfg", m89x_runtime_kernel_cfg.w3_cfg);
        axi_master_w3 = axi_pkg::axi_env#(64,16,8,3,1)::type_id::create("axi_master_w3", this);

        m89x_runtime_kernel_cfg.control_cfg.set_default();
        m89x_runtime_kernel_cfg.control_cfg.drv_type = axi_pkg::MASTER;
        m89x_runtime_kernel_cfg.control_cfg.reset_level = axi_pkg::RESET_LEVEL_LOW;
        lat_control = axi_latency_control::type_id::create("lat_control", this);
        m89x_runtime_kernel_cfg.control_cfg.clatency = lat_control;
        uvm_config_db#(axi_pkg::axi_cfg)::set(this, "axi_lite_control*", "cfg", m89x_runtime_kernel_cfg.control_cfg);
        axi_lite_control = axi_pkg::axi_env#(8,4,4,3,1)::type_id::create("axi_lite_control", this);



        refm = m89x_runtime_kernel_reference_model::type_id::create("refm", this);


        uvm_config_db#(m89x_runtime_kernel_reference_model)::set(this, "*", "refm", refm);


        `uvm_info(this.get_full_name(), "set reference model by uvm_config_db", UVM_LOW)


        subsys_mon = m89x_runtime_kernel_subsystem_monitor::type_id::create("subsys_mon", this);


        m89x_runtime_kernel_virtual_sqr = m89x_runtime_kernel_virtual_sequencer::type_id::create("m89x_runtime_kernel_virtual_sqr", this);
        `uvm_info(this.get_full_name(), "build_phase done", UVM_LOW)
    endfunction


    function void m89x_runtime_kernel_env::connect_phase(uvm_phase phase);
        super.connect_phase(phase);


        m89x_runtime_kernel_virtual_sqr.svr_port_tx_sqr = env_master_svr_tx.m_agt.sqr;
        env_master_svr_tx.m_agt.mon.item_collect_port.connect(subsys_mon.svr_master_tx_imp);
 
        m89x_runtime_kernel_virtual_sqr.svr_port_rx_sqr = env_slave_svr_rx.s_agt.sqr;
        env_slave_svr_rx.s_agt.mon.item_collect_port.connect(subsys_mon.svr_slave_rx_imp);
 
        if(m89x_runtime_kernel_cfg.w0_cfg.drv_type==axi_pkg::MASTER ||m89x_runtime_kernel_cfg.w0_cfg.drv_type==axi_pkg::SLAVE)
            m89x_runtime_kernel_virtual_sqr.w0_sqr = axi_master_w0.vsqr;
        axi_master_w0.item_wtr_port.connect(subsys_mon.w0_wtr_imp);
        axi_master_w0.item_rtr_port.connect(subsys_mon.w0_rtr_imp);
        uvm_callbacks#(axi_pkg::axi_state, axi_pkg::axi_state_cbs)::add(axi_master_w0.state, refm.axi_memaccess_cb_w0);
        if(m89x_runtime_kernel_cfg.w1_cfg.drv_type==axi_pkg::MASTER ||m89x_runtime_kernel_cfg.w1_cfg.drv_type==axi_pkg::SLAVE)
            m89x_runtime_kernel_virtual_sqr.w1_sqr = axi_master_w1.vsqr;
        axi_master_w1.item_wtr_port.connect(subsys_mon.w1_wtr_imp);
        axi_master_w1.item_rtr_port.connect(subsys_mon.w1_rtr_imp);
        uvm_callbacks#(axi_pkg::axi_state, axi_pkg::axi_state_cbs)::add(axi_master_w1.state, refm.axi_memaccess_cb_w1);
        if(m89x_runtime_kernel_cfg.w2_cfg.drv_type==axi_pkg::MASTER ||m89x_runtime_kernel_cfg.w2_cfg.drv_type==axi_pkg::SLAVE)
            m89x_runtime_kernel_virtual_sqr.w2_sqr = axi_master_w2.vsqr;
        axi_master_w2.item_wtr_port.connect(subsys_mon.w2_wtr_imp);
        axi_master_w2.item_rtr_port.connect(subsys_mon.w2_rtr_imp);
        uvm_callbacks#(axi_pkg::axi_state, axi_pkg::axi_state_cbs)::add(axi_master_w2.state, refm.axi_memaccess_cb_w2);
        if(m89x_runtime_kernel_cfg.w3_cfg.drv_type==axi_pkg::MASTER ||m89x_runtime_kernel_cfg.w3_cfg.drv_type==axi_pkg::SLAVE)
            m89x_runtime_kernel_virtual_sqr.w3_sqr = axi_master_w3.vsqr;
        axi_master_w3.item_wtr_port.connect(subsys_mon.w3_wtr_imp);
        axi_master_w3.item_rtr_port.connect(subsys_mon.w3_rtr_imp);
        uvm_callbacks#(axi_pkg::axi_state, axi_pkg::axi_state_cbs)::add(axi_master_w3.state, refm.axi_memaccess_cb_w3);
        if(m89x_runtime_kernel_cfg.control_cfg.drv_type==axi_pkg::MASTER ||m89x_runtime_kernel_cfg.control_cfg.drv_type==axi_pkg::SLAVE)
            m89x_runtime_kernel_virtual_sqr.control_sqr = axi_lite_control.vsqr;
        axi_lite_control.item_wtr_port.connect(subsys_mon.control_wtr_imp);
        axi_lite_control.item_rtr_port.connect(subsys_mon.control_rtr_imp);
        refm.m89x_runtime_kernel_cfg = m89x_runtime_kernel_cfg;
        `uvm_info(this.get_full_name(), "connect phase done", UVM_LOW)
    endfunction


    task m89x_runtime_kernel_env::run_phase(uvm_phase phase);
        `uvm_info(this.get_full_name(), "m89x_runtime_kernel_env is running", UVM_LOW)
    endtask


`endif
