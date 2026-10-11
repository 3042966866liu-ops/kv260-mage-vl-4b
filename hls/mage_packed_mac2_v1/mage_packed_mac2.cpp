#include "mage_packed_mac2.hpp"

// Pack two signed low-bit weights into the 27-bit DSP input.  The lower field
// is two's-complement modulo 2^13; decrementing the upper field when weight0
// is negative makes the complete packed integer equal to
// weight1 * 2^13 + weight0 without introducing a cross-field bias.
static ap_int<27> pack_weights(ap_int<5> weight0, ap_int<5> weight1) {
#pragma HLS INLINE
    const ap_int<14> upper = (ap_int<14>)weight1 - (weight0 < 0 ? 1 : 0);
    ap_int<27> packed = (ap_int<27>)upper << 13;
    packed.range(12, 0) = (ap_uint<13>)weight0;
    return packed;
}

void mage_packed_mac2(
    ap_int<8> activation,
    ap_int<5> weight0,
    ap_int<5> weight1,
    ap_int<16> &product0,
    ap_int<16> &product1,
    ap_uint<32> &build_id) {
#pragma HLS INTERFACE s_axilite port=activation bundle=control
#pragma HLS INTERFACE s_axilite port=weight0 bundle=control
#pragma HLS INTERFACE s_axilite port=weight1 bundle=control
#pragma HLS INTERFACE s_axilite port=product0 bundle=control
#pragma HLS INTERFACE s_axilite port=product1 bundle=control
#pragma HLS INTERFACE s_axilite port=build_id bundle=control
#pragma HLS INTERFACE s_axilite port=return bundle=control

    const ap_int<27> packed_weights = pack_weights(weight0, weight1);
    const ap_int<45> packed_product = packed_weights * activation;
#pragma HLS BIND_OP variable=packed_product op=mul impl=dsp

    const ap_int<13> low_product = (ap_int<13>)packed_product.range(12, 0);
    ap_int<32> high_product = (ap_int<32>)(packed_product >> 13);
    // Arithmetic right shift rounds a negative low product toward -infinity.
    // Undo that one-count borrow to recover weight1 * activation exactly.
    if (low_product < 0) high_product += 1;
    product0 = low_product;
    product1 = high_product;
    build_id = MAGE_PACKED_MAC2_BUILD_ID;
}
