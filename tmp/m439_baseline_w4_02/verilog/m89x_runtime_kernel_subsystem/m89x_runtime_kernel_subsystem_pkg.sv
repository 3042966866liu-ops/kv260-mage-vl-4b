//==============================================================
//Vitis HLS - High-Level Synthesis from C, C++ and OpenCL v2026.1 (64-bit)
//Tool Version Limit: 2026.06
//Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
//Copyright 2022-2026 Advanced Micro Devices, Inc. All Rights Reserved.
//
//==============================================================
`timescale 1ns/1ps 

`ifndef M89X_RUNTIME_KERNEL_SUBSYSTEM_PKG__SV          
    `define M89X_RUNTIME_KERNEL_SUBSYSTEM_PKG__SV      
                                                     
    package m89x_runtime_kernel_subsystem_pkg;               
                                                     
        import uvm_pkg::*;                           
        import file_agent_pkg::*;                    
        import svr_pkg::*;
        import axi_pkg::*;
                                                     
        `include "uvm_macros.svh"                  
                                                     
        `include "m89x_runtime_kernel_config.sv"           
        `include "m89x_runtime_kernel_reference_model.sv"  
        `include "m89x_runtime_kernel_scoreboard.sv"       
        `include "m89x_runtime_kernel_subsystem_monitor.sv"
        `include "m89x_runtime_kernel_virtual_sequencer.sv"
        `include "m89x_runtime_kernel_pkg_sequence_lib.sv" 
        `include "m89x_runtime_kernel_env.sv"              
                                                     
    endpackage                                       
                                                     
`endif                                               
