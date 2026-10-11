#include "mage_m81_sixport_burst_probe.hpp"

// This deliberately has no model arithmetic.  It is the minimum compatible
// six-port 128-bit traffic kernel needed to measure whether the actual PL/PS
// path can sustain long independent bursts before a full 4B kernel is widened.
static void m81_stream_xor(
    const ap_uint<128> *memory,
    unsigned word_count,
    ap_uint<64> &folded) {
#pragma HLS INLINE off
    folded = 0;
read_words:
    for (unsigned word = 0; word < word_count; ++word) {
#pragma HLS PIPELINE II=1
        const ap_uint<128> value = memory[word];
        folded ^= value.range(63, 0) ^ value.range(127, 64);
    }
}

static void m81_parallel_readers(
    const ap_uint<128> *weights0,
    const ap_uint<128> *weights1,
    const ap_uint<128> *weights2,
    const ap_uint<128> *weights3,
    const ap_uint<128> *weights4,
    const ap_uint<128> *weights5,
    unsigned word_count,
    ap_uint<64> &folded0,
    ap_uint<64> &folded1,
    ap_uint<64> &folded2,
    ap_uint<64> &folded3,
    ap_uint<64> &folded4,
    ap_uint<64> &folded5) {
#pragma HLS INLINE off
#pragma HLS DATAFLOW
    m81_stream_xor(weights0, word_count, folded0);
    m81_stream_xor(weights1, word_count, folded1);
    m81_stream_xor(weights2, word_count, folded2);
    m81_stream_xor(weights3, word_count, folded3);
    m81_stream_xor(weights4, word_count, folded4);
    m81_stream_xor(weights5, word_count, folded5);
}

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
    ap_uint<32> &completed_words_per_port) {
#pragma HLS INTERFACE m_axi port=weights0 offset=slave bundle=weights0 depth=M81_MAX_WORDS max_read_burst_length=64 num_read_outstanding=32
#pragma HLS INTERFACE m_axi port=weights1 offset=slave bundle=weights1 depth=M81_MAX_WORDS max_read_burst_length=64 num_read_outstanding=32
#pragma HLS INTERFACE m_axi port=weights2 offset=slave bundle=weights2 depth=M81_MAX_WORDS max_read_burst_length=64 num_read_outstanding=32
#pragma HLS INTERFACE m_axi port=weights3 offset=slave bundle=weights3 depth=M81_MAX_WORDS max_read_burst_length=64 num_read_outstanding=32
#pragma HLS INTERFACE m_axi port=weights4 offset=slave bundle=weights4 depth=M81_MAX_WORDS max_read_burst_length=64 num_read_outstanding=32
#pragma HLS INTERFACE m_axi port=weights5 offset=slave bundle=weights5 depth=M81_MAX_WORDS max_read_burst_length=64 num_read_outstanding=32
#pragma HLS INTERFACE s_axilite port=weights0 bundle=control
#pragma HLS INTERFACE s_axilite port=weights1 bundle=control
#pragma HLS INTERFACE s_axilite port=weights2 bundle=control
#pragma HLS INTERFACE s_axilite port=weights3 bundle=control
#pragma HLS INTERFACE s_axilite port=weights4 bundle=control
#pragma HLS INTERFACE s_axilite port=weights5 bundle=control
#pragma HLS INTERFACE s_axilite port=word_count bundle=control
#pragma HLS INTERFACE s_axilite port=checksum0 bundle=control
#pragma HLS INTERFACE s_axilite port=checksum1 bundle=control
#pragma HLS INTERFACE s_axilite port=checksum2 bundle=control
#pragma HLS INTERFACE s_axilite port=checksum3 bundle=control
#pragma HLS INTERFACE s_axilite port=checksum4 bundle=control
#pragma HLS INTERFACE s_axilite port=checksum5 bundle=control
#pragma HLS INTERFACE s_axilite port=status bundle=control
#pragma HLS INTERFACE s_axilite port=build_id bundle=control
#pragma HLS INTERFACE s_axilite port=completed_words_per_port bundle=control
#pragma HLS INTERFACE s_axilite port=return bundle=control
    build_id = M81_BUILD_ID;
    completed_words_per_port = 0;
    if (word_count == 0 || word_count > M81_MAX_WORDS) {
        status = 1;
        checksum0 = checksum1 = checksum2 = checksum3 = checksum4 = checksum5 = 0;
        return;
    }
    ap_uint<64> folded0;
    ap_uint<64> folded1;
    ap_uint<64> folded2;
    ap_uint<64> folded3;
    ap_uint<64> folded4;
    ap_uint<64> folded5;
    m81_parallel_readers(weights0, weights1, weights2, weights3, weights4, weights5,
        word_count, folded0, folded1, folded2, folded3, folded4, folded5);
    checksum0 = folded0;
    checksum1 = folded1;
    checksum2 = folded2;
    checksum3 = folded3;
    checksum4 = folded4;
    checksum5 = folded5;
    status = 0;
    completed_words_per_port = word_count;
}
