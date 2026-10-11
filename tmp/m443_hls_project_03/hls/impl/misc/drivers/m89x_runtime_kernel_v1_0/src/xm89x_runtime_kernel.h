// ==============================================================
// Vitis HLS - High-Level Synthesis from C, C++ and OpenCL v2026.1 (64-bit)
// Tool Version Limit: 2026.06
// Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
// Copyright 2022-2026 Advanced Micro Devices, Inc. All Rights Reserved.
// 
// ==============================================================
#ifndef XM89X_RUNTIME_KERNEL_H
#define XM89X_RUNTIME_KERNEL_H

#ifdef __cplusplus
extern "C" {
#endif

/***************************** Include Files *********************************/
#ifndef __linux__
#include "xil_types.h"
#include "xil_assert.h"
#include "xstatus.h"
#include "xil_io.h"
#else
#include <stdint.h>
#include <assert.h>
#include <dirent.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <unistd.h>
#include <stddef.h>
#endif
#include "xm89x_runtime_kernel_hw.h"

/**************************** Type Definitions ******************************/
#ifdef __linux__
typedef uint8_t u8;
typedef uint16_t u16;
typedef uint32_t u32;
typedef uint64_t u64;
#else
typedef struct {
#ifdef SDT
    char *Name;
#else
    u16 DeviceId;
#endif
    u64 Control_BaseAddress;
} XM89x_runtime_kernel_Config;
#endif

typedef struct {
    u64 Control_BaseAddress;
    u32 IsReady;
} XM89x_runtime_kernel;

typedef u32 word_type;

/***************** Macros (Inline Functions) Definitions *********************/
#ifndef __linux__
#define XM89x_runtime_kernel_WriteReg(BaseAddress, RegOffset, Data) \
    Xil_Out32((BaseAddress) + (RegOffset), (u32)(Data))
#define XM89x_runtime_kernel_ReadReg(BaseAddress, RegOffset) \
    Xil_In32((BaseAddress) + (RegOffset))
#else
#define XM89x_runtime_kernel_WriteReg(BaseAddress, RegOffset, Data) \
    *(volatile u32*)((BaseAddress) + (RegOffset)) = (u32)(Data)
#define XM89x_runtime_kernel_ReadReg(BaseAddress, RegOffset) \
    *(volatile u32*)((BaseAddress) + (RegOffset))

#define Xil_AssertVoid(expr)    assert(expr)
#define Xil_AssertNonvoid(expr) assert(expr)

#define XST_SUCCESS             0
#define XST_DEVICE_NOT_FOUND    2
#define XST_OPEN_DEVICE_FAILED  3
#define XIL_COMPONENT_IS_READY  1
#endif

/************************** Function Prototypes *****************************/
#ifndef __linux__
#ifdef SDT
int XM89x_runtime_kernel_Initialize(XM89x_runtime_kernel *InstancePtr, UINTPTR BaseAddress);
XM89x_runtime_kernel_Config* XM89x_runtime_kernel_LookupConfig(UINTPTR BaseAddress);
#else
int XM89x_runtime_kernel_Initialize(XM89x_runtime_kernel *InstancePtr, u16 DeviceId);
XM89x_runtime_kernel_Config* XM89x_runtime_kernel_LookupConfig(u16 DeviceId);
#endif
int XM89x_runtime_kernel_CfgInitialize(XM89x_runtime_kernel *InstancePtr, XM89x_runtime_kernel_Config *ConfigPtr);
#else
int XM89x_runtime_kernel_Initialize(XM89x_runtime_kernel *InstancePtr, const char* InstanceName);
int XM89x_runtime_kernel_Release(XM89x_runtime_kernel *InstancePtr);
#endif

void XM89x_runtime_kernel_Start(XM89x_runtime_kernel *InstancePtr);
u32 XM89x_runtime_kernel_IsDone(XM89x_runtime_kernel *InstancePtr);
u32 XM89x_runtime_kernel_IsIdle(XM89x_runtime_kernel *InstancePtr);
u32 XM89x_runtime_kernel_IsReady(XM89x_runtime_kernel *InstancePtr);
void XM89x_runtime_kernel_EnableAutoRestart(XM89x_runtime_kernel *InstancePtr);
void XM89x_runtime_kernel_DisableAutoRestart(XM89x_runtime_kernel *InstancePtr);
u32 XM89x_runtime_kernel_Get_return(XM89x_runtime_kernel *InstancePtr);

void XM89x_runtime_kernel_Set_s0(XM89x_runtime_kernel *InstancePtr, u64 Data);
u64 XM89x_runtime_kernel_Get_s0(XM89x_runtime_kernel *InstancePtr);
void XM89x_runtime_kernel_Set_s1(XM89x_runtime_kernel *InstancePtr, u64 Data);
u64 XM89x_runtime_kernel_Get_s1(XM89x_runtime_kernel *InstancePtr);
void XM89x_runtime_kernel_Set_s2(XM89x_runtime_kernel *InstancePtr, u64 Data);
u64 XM89x_runtime_kernel_Get_s2(XM89x_runtime_kernel *InstancePtr);
void XM89x_runtime_kernel_Set_s3(XM89x_runtime_kernel *InstancePtr, u64 Data);
u64 XM89x_runtime_kernel_Get_s3(XM89x_runtime_kernel *InstancePtr);
void XM89x_runtime_kernel_Set_config_r(XM89x_runtime_kernel *InstancePtr, u32 Data);
u32 XM89x_runtime_kernel_Get_config_r(XM89x_runtime_kernel *InstancePtr);

void XM89x_runtime_kernel_InterruptGlobalEnable(XM89x_runtime_kernel *InstancePtr);
void XM89x_runtime_kernel_InterruptGlobalDisable(XM89x_runtime_kernel *InstancePtr);
void XM89x_runtime_kernel_InterruptEnable(XM89x_runtime_kernel *InstancePtr, u32 Mask);
void XM89x_runtime_kernel_InterruptDisable(XM89x_runtime_kernel *InstancePtr, u32 Mask);
void XM89x_runtime_kernel_InterruptClear(XM89x_runtime_kernel *InstancePtr, u32 Mask);
u32 XM89x_runtime_kernel_InterruptGetEnabled(XM89x_runtime_kernel *InstancePtr);
u32 XM89x_runtime_kernel_InterruptGetStatus(XM89x_runtime_kernel *InstancePtr);

#ifdef __cplusplus
}
#endif

#endif
