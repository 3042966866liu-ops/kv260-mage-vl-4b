//==============================================================
//Vitis HLS - High-Level Synthesis from C, C++ and OpenCL v2026.1 (64-bit)
//Tool Version Limit: 2026.06
//Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
//Copyright 2022-2026 Advanced Micro Devices, Inc. All Rights Reserved.
//
//==============================================================
`ifndef M89X_RUNTIME_KERNEL_CONFIG__SV                        
    `define M89X_RUNTIME_KERNEL_CONFIG__SV                    
                                                            
    class m89x_runtime_kernel_config extends uvm_object;            
                                                            
        int check_ena;                                      
        int cover_ena;                                      
        svr_pkg::svr_config port_tx_cfg;
        svr_pkg::svr_config port_rx_cfg;
        axi_pkg::axi_cfg w0_cfg;
        axi_pkg::axi_cfg w1_cfg;
        axi_pkg::axi_cfg w2_cfg;
        axi_pkg::axi_cfg w3_cfg;
        axi_pkg::axi_cfg control_cfg;

        `uvm_object_utils_begin(m89x_runtime_kernel_config)         
        `uvm_field_object(port_tx_cfg, UVM_DEFAULT)
        `uvm_field_object(port_rx_cfg, UVM_DEFAULT)
        `uvm_field_object(w0_cfg, UVM_DEFAULT);
        `uvm_field_object(w1_cfg, UVM_DEFAULT);
        `uvm_field_object(w2_cfg, UVM_DEFAULT);
        `uvm_field_object(w3_cfg, UVM_DEFAULT);
        `uvm_field_object(control_cfg, UVM_DEFAULT);
        `uvm_field_int   (check_ena , UVM_DEFAULT)          
        `uvm_field_int   (cover_ena , UVM_DEFAULT)          
        `uvm_object_utils_end                               

        function new (string name = "m89x_runtime_kernel_config");
            super.new(name);                                
            port_tx_cfg = svr_pkg::svr_config::type_id::create("port_tx_cfg");
            port_rx_cfg = svr_pkg::svr_config::type_id::create("port_rx_cfg");
            w0_cfg = new("w0_cfg", 1);
            w1_cfg = new("w1_cfg", 1);
            w2_cfg = new("w2_cfg", 1);
            w3_cfg = new("w3_cfg", 1);
            control_cfg = axi_pkg::axi_cfg::type_id::create("control_cfg");
        endfunction                                         
                                                            
    endclass                                                
                                                            
`endif                                                      
