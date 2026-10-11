#include "mage_m87_dot_module.hpp"
#include "mage_m86_activation_prefetch.hpp"

// Declaration first lets the M86-derived exact consumer call a separately
// synthesized dot module. The definition below still delegates to the
// validated M82 arithmetic without changing order, bits or rounding.
static void m87_dot_pair(
    const ap_uint<512> &codes,
    const ap_uint<128> activation[MAGE_T6_TOKENS][4],
    unsigned token, unsigned bits, ap_int<24> &dot0, ap_int<24> &dot1,
    ap_uint<16> tagged0, ap_uint<16> tagged1);

#define M86_DOT_FUNCTION m87_dot_pair
#define M86_EXPECT_BUILD_ID M87_EXPECT_BUILD_ID
#define mage_m86_activation_prefetch mage_m87_dot_module
#include "mage_m86_activation_prefetch.cpp"
#undef mage_m86_activation_prefetch
#undef M86_EXPECT_BUILD_ID
#undef M86_DOT_FUNCTION

static void m87_dot_pair(
    const ap_uint<512> &codes,
    const ap_uint<128> activation[MAGE_T6_TOKENS][4],
    unsigned token, unsigned bits, ap_int<24> &dot0, ap_int<24> &dot1,
    ap_uint<16> tagged0, ap_uint<16> tagged1) {
#pragma HLS INLINE off
    m82_dot_pair(codes, activation, token, bits, dot0, dot1, tagged0, tagged1);
}
