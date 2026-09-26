#include "mage_prefill_m89_t32_reuse.hpp"

#include "../mage_prefill_t6_runtime_wrapper_m75b/mage_prefill_t6_arith.cpp"

static ap_int<5> m89_qmin(ap_uint<16> tagged_scale) {
#pragma HLS INLINE
    return tagged_scale[15] ? (ap_int<5>)-1 : (ap_int<5>)-2;
}

static void m89_load_activation(
    hls::stream<m89_axis128_t> &activation_tx,
    ap_uint<128> activation[M89_MAX_GROUPS][M89_TOKEN_LANES][4],
    unsigned input_groups, ap_uint<32> &status) {
#pragma HLS INLINE off
    for (unsigned group = 0; group < input_groups; ++group)
        for (unsigned token = 0; token < M89_TOKEN_LANES; ++token)
            for (unsigned word = 0; word < 4; ++word) {
#pragma HLS PIPELINE II=1
                const m89_axis128_t item = activation_tx.read();
                const bool expected_last = group + 1 == input_groups &&
                    token + 1 == M89_TOKEN_LANES && word == 3;
                if ((bool)item.last != expected_last) status = 2;
                activation[group][token][word] = item.data;
            }
}

static void m89_dot_pair_w2(
    ap_uint<128> codes0, ap_uint<128> codes1,
    ap_uint<16> tagged0, ap_uint<16> tagged1,
    const ap_uint<128> activation_words[4],
    ap_int<24> &dot0, ap_int<24> &dot1) {
#pragma HLS INLINE
    ap_int<24> sum0 = 0;
    ap_int<24> sum1 = 0;
    const ap_int<5> qmin0 = m89_qmin(tagged0);
    const ap_int<5> qmin1 = m89_qmin(tagged1);
    for (unsigned lane = 0; lane < M89_GROUP_SIZE; ++lane) {
#pragma HLS UNROLL
        const ap_uint<128> packed = activation_words[lane >> 4];
        const ap_int<8> input = (ap_int<8>)packed.range(8 * (lane & 15U) + 7, 8 * (lane & 15U));
        const ap_int<5> weight0 = (ap_uint<2>)codes0.range(2 * lane + 1, 2 * lane) + qmin0;
        const ap_int<5> weight1 = (ap_uint<2>)codes1.range(2 * lane + 1, 2 * lane) + qmin1;
        ap_int<16> product0;
        ap_int<16> product1;
        t6_packed_mac2(input, weight0, weight1, product0, product1);
        sum0 += product0;
        sum1 += product1;
    }
    dot0 = sum0;
    dot1 = sum1;
}

struct m89_pair_t { ap_uint<64> data; };

static void m89_compute_shard(
    const ap_uint<128> *memory,
    const ap_uint<128> activation[M89_MAX_GROUPS][M89_TOKEN_LANES][4],
    hls::stream<m89_pair_t> &result,
    unsigned input_groups, unsigned rows_per_shard) {
#pragma HLS INLINE off
    // A token dimension is physically banked.  Consecutive T32 pair passes
    // therefore update different rows of the banked accumulator, so a weight
    // record can remain live while the original ordered sums are preserved.
    ap_int<32> accum_even[M89_TOKEN_LANES][M89_MAX_ROWS_PER_SHARD / 2];
    ap_int<32> accum_odd[M89_TOKEN_LANES][M89_MAX_ROWS_PER_SHARD / 2];
#pragma HLS ARRAY_PARTITION variable=accum_even complete dim=1
#pragma HLS ARRAY_PARTITION variable=accum_odd complete dim=1
#pragma HLS BIND_STORAGE variable=accum_even type=ram_2p impl=bram latency=2
#pragma HLS BIND_STORAGE variable=accum_odd type=ram_2p impl=bram latency=2
    for (unsigned token = 0; token < M89_TOKEN_LANES; ++token)
        for (unsigned row = 0; row < rows_per_shard / 2; ++row) {
#pragma HLS PIPELINE II=1
            accum_even[token][row] = 0;
            accum_odd[token][row] = 0;
        }

    const unsigned blocks = rows_per_shard / 8;
    for (unsigned group = 0; group < input_groups; ++group)
        for (unsigned block = 0; block < blocks; ++block) {
            const unsigned base = group * blocks * 9 + block * 9;
            const ap_uint<128> scale = memory[base];
            for (unsigned pair = 0; pair < 4; ++pair) {
                // The two code words are read exactly once.  They remain in
                // scalar registers throughout all sixteen token-pair passes.
                const ap_uint<128> codes0 = memory[base + 1 + 2 * pair];
                const ap_uint<128> codes1 = memory[base + 2 + 2 * pair];
                const ap_uint<16> tagged0 = scale.range(32 * pair + 15, 32 * pair);
                const ap_uint<16> tagged1 = scale.range(32 * pair + 31, 32 * pair + 16);
                const unsigned row = 4 * block + pair;
                for (unsigned token_pair = 0; token_pair < M89_TOKEN_PAIRS; ++token_pair) {
#pragma HLS PIPELINE II=1
#pragma HLS DEPENDENCE variable=accum_even inter false
#pragma HLS DEPENDENCE variable=accum_odd inter false
                    const unsigned token0 = 2 * token_pair;
                    const unsigned token1 = token0 + 1;
                    ap_int<24> dot00, dot01, dot10, dot11;
                    m89_dot_pair_w2(codes0, codes1, tagged0, tagged1,
                                    activation[group][token0], dot00, dot01);
                    m89_dot_pair_w2(codes0, codes1, tagged0, tagged1,
                                    activation[group][token1], dot10, dot11);
                    accum_even[token0][row] += dot00;
                    accum_odd[token0][row] += dot01;
                    accum_even[token1][row] += dot10;
                    accum_odd[token1][row] += dot11;
                }
            }
        }

    for (unsigned token = 0; token < M89_TOKEN_LANES; ++token)
        for (unsigned pair = 0; pair < rows_per_shard / 2; ++pair) {
#pragma HLS PIPELINE II=1
            m89_pair_t item;
            item.data.range(31, 0) = (ap_uint<32>)accum_even[token][pair];
            item.data.range(63, 32) = (ap_uint<32>)accum_odd[token][pair];
            result.write(item);
        }
}

static void m89_merge(hls::stream<m89_pair_t> result[M89_SHARDS],
                      hls::stream<m89_axis64_t> &rx, unsigned rows_per_shard) {
#pragma HLS INLINE off
#pragma HLS ARRAY_PARTITION variable=result complete dim=1
    for (unsigned token = 0; token < M89_TOKEN_LANES; ++token)
        for (unsigned shard = 0; shard < M89_SHARDS; ++shard)
            for (unsigned row = 0; row < rows_per_shard; row += 2) {
#pragma HLS PIPELINE II=1
                m89_axis64_t item;
                item.data = result[shard].read().data;
                item.keep = -1;
                item.strb = -1;
                item.last = token + 1 == M89_TOKEN_LANES && shard + 1 == M89_SHARDS && row + 2 == rows_per_shard;
                rx.write(item);
            }
}

static void m89_six_shards(
    const ap_uint<128> *shard0, const ap_uint<128> *shard1,
    const ap_uint<128> *shard2, const ap_uint<128> *shard3,
    const ap_uint<128> *shard4, const ap_uint<128> *shard5,
    const ap_uint<128> activation[M89_MAX_GROUPS][M89_TOKEN_LANES][4],
    hls::stream<m89_axis64_t> &rx, unsigned input_groups, unsigned rows_per_shard) {
#pragma HLS INLINE off
#pragma HLS DATAFLOW
    hls::stream<m89_pair_t> results[M89_SHARDS];
#pragma HLS ARRAY_PARTITION variable=results complete dim=1
#pragma HLS STREAM variable=results depth=64
    m89_compute_shard(shard0, activation, results[0], input_groups, rows_per_shard);
    m89_compute_shard(shard1, activation, results[1], input_groups, rows_per_shard);
    m89_compute_shard(shard2, activation, results[2], input_groups, rows_per_shard);
    m89_compute_shard(shard3, activation, results[3], input_groups, rows_per_shard);
    m89_compute_shard(shard4, activation, results[4], input_groups, rows_per_shard);
    m89_compute_shard(shard5, activation, results[5], input_groups, rows_per_shard);
    m89_merge(results, rx, rows_per_shard);
}

void m89_t32_reuse(
    hls::stream<m89_axis128_t> &activation_tx,
    const ap_uint<128> *shard0, const ap_uint<128> *shard1,
    const ap_uint<128> *shard2, const ap_uint<128> *shard3,
    const ap_uint<128> *shard4, const ap_uint<128> *shard5,
    hls::stream<m89_axis64_t> &rx, unsigned input_groups, unsigned rows_per_shard,
    ap_uint<32> &status, ap_uint<32> &build_id, ap_uint<32> &call_count,
    ap_uint<32> &processed_macros) {
#pragma HLS INTERFACE axis port=activation_tx
#pragma HLS INTERFACE m_axi port=shard0 offset=slave bundle=weights0 depth=524288 max_read_burst_length=64 num_read_outstanding=32
#pragma HLS INTERFACE m_axi port=shard1 offset=slave bundle=weights1 depth=524288 max_read_burst_length=64 num_read_outstanding=32
#pragma HLS INTERFACE m_axi port=shard2 offset=slave bundle=weights2 depth=524288 max_read_burst_length=64 num_read_outstanding=32
#pragma HLS INTERFACE m_axi port=shard3 offset=slave bundle=weights3 depth=524288 max_read_burst_length=64 num_read_outstanding=32
#pragma HLS INTERFACE m_axi port=shard4 offset=slave bundle=weights4 depth=524288 max_read_burst_length=64 num_read_outstanding=32
#pragma HLS INTERFACE m_axi port=shard5 offset=slave bundle=weights5 depth=524288 max_read_burst_length=64 num_read_outstanding=32
#pragma HLS INTERFACE axis port=rx
#pragma HLS INTERFACE s_axilite port=shard0 bundle=control
#pragma HLS INTERFACE s_axilite port=shard1 bundle=control
#pragma HLS INTERFACE s_axilite port=shard2 bundle=control
#pragma HLS INTERFACE s_axilite port=shard3 bundle=control
#pragma HLS INTERFACE s_axilite port=shard4 bundle=control
#pragma HLS INTERFACE s_axilite port=shard5 bundle=control
#pragma HLS INTERFACE s_axilite port=input_groups bundle=control
#pragma HLS INTERFACE s_axilite port=rows_per_shard bundle=control
#pragma HLS INTERFACE s_axilite port=status bundle=control
#pragma HLS INTERFACE s_axilite port=build_id bundle=control
#pragma HLS INTERFACE s_axilite port=call_count bundle=control
#pragma HLS INTERFACE s_axilite port=processed_macros bundle=control
#pragma HLS INTERFACE s_axilite port=return bundle=control
    static ap_uint<32> calls = 0;
    static ap_uint<32> macros = 0;
    status = 0;
    build_id = M89_BUILD_ID;
    call_count = calls;
    processed_macros = macros;
    if (input_groups < 1 || input_groups > M89_MAX_GROUPS || rows_per_shard < 8 ||
        rows_per_shard > M89_MAX_ROWS_PER_SHARD || (rows_per_shard & 7U) != 0) {
        status = 1;
        return;
    }
    ap_uint<128> activation[M89_MAX_GROUPS][M89_TOKEN_LANES][4];
#pragma HLS BIND_STORAGE variable=activation type=ram_2p impl=uram latency=2
    m89_load_activation(activation_tx, activation, input_groups, status);
    m89_six_shards(shard0, shard1, shard2, shard3, shard4, shard5,
                   activation, rx, input_groups, rows_per_shard);
    calls += 1;
    macros += input_groups * rows_per_shard * M89_SHARDS * M89_TOKEN_LANES;
    call_count = calls;
    processed_macros = macros;
}
