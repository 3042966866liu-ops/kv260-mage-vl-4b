// ==============================================================
// Vitis HLS - High-Level Synthesis from C, C++ and OpenCL v2026.1 (64-bit)
// Tool Version Limit: 2026.06
// Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
// Copyright 2022-2026 Advanced Micro Devices, Inc. All Rights Reserved.
// 
// ==============================================================
// control
// 0x00 : Control signals
//        bit 0  - ap_start (Read/Write/COH)
//        bit 1  - ap_done (Read/COR)
//        bit 2  - ap_idle (Read)
//        bit 3  - ap_ready (Read/COR)
//        bit 7  - auto_restart (Read/Write)
//        bit 9  - interrupt (Read)
//        others - reserved
// 0x04 : Global Interrupt Enable Register
//        bit 0  - Global Interrupt Enable (Read/Write)
//        others - reserved
// 0x08 : IP Interrupt Enable Register (Read/Write)
//        bit 0 - enable ap_done interrupt (Read/Write)
//        bit 1 - enable ap_ready interrupt (Read/Write)
//        others - reserved
// 0x0c : IP Interrupt Status Register (Read/TOW)
//        bit 0 - ap_done (Read/TOW)
//        bit 1 - ap_ready (Read/TOW)
//        others - reserved
// 0x10 : Data signal of ap_return
//        bit 31~0 - ap_return[31:0] (Read)
// 0x18 : Data signal of s0
//        bit 31~0 - s0[31:0] (Read/Write)
// 0x1c : Data signal of s0
//        bit 31~0 - s0[63:32] (Read/Write)
// 0x20 : reserved
// 0x24 : Data signal of s1
//        bit 31~0 - s1[31:0] (Read/Write)
// 0x28 : Data signal of s1
//        bit 31~0 - s1[63:32] (Read/Write)
// 0x2c : reserved
// 0x30 : Data signal of s2
//        bit 31~0 - s2[31:0] (Read/Write)
// 0x34 : Data signal of s2
//        bit 31~0 - s2[63:32] (Read/Write)
// 0x38 : reserved
// 0x3c : Data signal of s3
//        bit 31~0 - s3[31:0] (Read/Write)
// 0x40 : Data signal of s3
//        bit 31~0 - s3[63:32] (Read/Write)
// 0x44 : reserved
// 0x80 : Data signal of config_r
//        bit 31~0 - config_r[31:0] (Read/Write)
// 0x84 : reserved
// (SC = Self Clear, COR = Clear on Read, TOW = Toggle on Write, COH = Clear on Handshake)

#define XM89X_RUNTIME_KERNEL_CONTROL_ADDR_AP_CTRL       0x00
#define XM89X_RUNTIME_KERNEL_CONTROL_ADDR_GIE           0x04
#define XM89X_RUNTIME_KERNEL_CONTROL_ADDR_IER           0x08
#define XM89X_RUNTIME_KERNEL_CONTROL_ADDR_ISR           0x0c
#define XM89X_RUNTIME_KERNEL_CONTROL_ADDR_AP_RETURN     0x10
#define XM89X_RUNTIME_KERNEL_CONTROL_BITS_AP_RETURN     32
#define XM89X_RUNTIME_KERNEL_CONTROL_ADDR_S0_DATA       0x18
#define XM89X_RUNTIME_KERNEL_CONTROL_BITS_S0_DATA       64
#define XM89X_RUNTIME_KERNEL_CONTROL_ADDR_S1_DATA       0x24
#define XM89X_RUNTIME_KERNEL_CONTROL_BITS_S1_DATA       64
#define XM89X_RUNTIME_KERNEL_CONTROL_ADDR_S2_DATA       0x30
#define XM89X_RUNTIME_KERNEL_CONTROL_BITS_S2_DATA       64
#define XM89X_RUNTIME_KERNEL_CONTROL_ADDR_S3_DATA       0x3c
#define XM89X_RUNTIME_KERNEL_CONTROL_BITS_S3_DATA       64
#define XM89X_RUNTIME_KERNEL_CONTROL_ADDR_CONFIG_R_DATA 0x80
#define XM89X_RUNTIME_KERNEL_CONTROL_BITS_CONFIG_R_DATA 32

