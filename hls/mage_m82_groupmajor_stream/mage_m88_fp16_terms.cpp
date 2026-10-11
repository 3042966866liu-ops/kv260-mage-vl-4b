#include "mage_m88_fp16_terms.hpp"
#include "mage_m86_activation_prefetch.hpp"

static void m88_terms(
    ap_int<24> dot0, ap_int<24> dot1, ap_uint<16> activation_scale,
    ap_uint<16> tagged0, ap_uint<16> tagged1, float &term0_out,
    float &term1_out);

#define M86_TERM_FUNCTION m88_terms
#define M86_EXPECT_BUILD_ID M88_EXPECT_BUILD_ID
#define mage_m86_activation_prefetch mage_m88_fp16_terms
#include "mage_m86_activation_prefetch.cpp"
#undef mage_m86_activation_prefetch
#undef M86_EXPECT_BUILD_ID
#undef M86_TERM_FUNCTION

static void m88_terms(
    ap_int<24> dot0, ap_int<24> dot1, ap_uint<16> activation_scale,
    ap_uint<16> tagged0, ap_uint<16> tagged1, float &term0_out,
    float &term1_out) {
#pragma HLS INLINE off
    m86_inline_terms(dot0, dot1, activation_scale, tagged0, tagged1, term0_out, term1_out);
}
