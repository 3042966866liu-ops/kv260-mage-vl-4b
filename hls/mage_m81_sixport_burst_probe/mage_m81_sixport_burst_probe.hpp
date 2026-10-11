#pragma once

#include <ap_int.h>

static const unsigned M81_MAX_WORDS = 262144;
static const ap_uint<32> M81_BUILD_ID = 0x4D383142U;  // "M81B"

void mage_m81_sixport_burst_probe(
    const ap_uint<128> *weights0,
    const ap_uint<128> *weights1,
    const ap_uint<128> *weights2,
    const ap_uint<128> *weights3,
    const ap_uint<128> *weights4,
    const ap_uint<128> *weights5,
    unsigned word_count,
    ap_uint<64> &checksum0,
    ap_uint<64> &checksum1,
    ap_uint<64> &checksum2,
    ap_uint<64> &checksum3,
    ap_uint<64> &checksum4,
    ap_uint<64> &checksum5,
    ap_uint<32> &status,
    ap_uint<32> &build_id,
    ap_uint<32> &completed_words_per_port);
