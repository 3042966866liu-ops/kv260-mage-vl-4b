#pragma once

#include <ap_int.h>

static const ap_uint<32> MAGE_PACKED_MAC2_BUILD_ID = 0x4D470042U;

void mage_packed_mac2(
    ap_int<8> activation,
    ap_int<5> weight0,
    ap_int<5> weight1,
    ap_int<16> &product0,
    ap_int<16> &product1,
    ap_uint<32> &build_id);
