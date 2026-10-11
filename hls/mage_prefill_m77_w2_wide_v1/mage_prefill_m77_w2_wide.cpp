#include "mage_prefill_m77_w2_wide.hpp"

#include "../mage_prefill_t6_runtime_wrapper_m75b/mage_prefill_t6_arith.cpp"

static ap_int<5> m77_qmin(ap_uint<16> tagged_scale) {
#pragma HLS INLINE
    return tagged_scale[15] ? (ap_int<5>)-1 : (ap_int<5>)-2;
}

static void m77_load_activation(
    hls::stream<m77_axis128_t> &activation_tx,
    ap_uint<128> activation[M77_MAX_GROUPS][M77_TOKEN_LANES][4],
    unsigned input_groups,
    ap_uint<32> &status) {
#pragma HLS INLINE off
load_group:
    for (unsigned group = 0; group < input_groups; ++group) {
    load_token:
        for (unsigned token = 0; token < M77_TOKEN_LANES; ++token) {
        load_word:
            for (unsigned word = 0; word < 4; ++word) {
#pragma HLS PIPELINE II=1
                const m77_axis128_t item = activation_tx.read();
                const bool expected_last = group == input_groups - 1 &&
                    token == M77_TOKEN_LANES - 1 && word == 3;
                if ((bool)item.last != expected_last) status = 2;
                activation[group][token][word] = item.data;
            }
        }
    }
}

static void m77_dot_pair_w2(
    ap_uint<128> codes0,
    ap_uint<128> codes1,
    ap_uint<16> tagged0,
    ap_uint<16> tagged1,
    const ap_uint<128> activation_words[4],
    ap_int<24> &dot0,
    ap_int<24> &dot1) {
#pragma HLS INLINE
    ap_int<24> sum0 = 0;
    ap_int<24> sum1 = 0;
    const ap_int<5> qmin0 = m77_qmin(tagged0);
    const ap_int<5> qmin1 = m77_qmin(tagged1);
lane_loop:
    for (unsigned lane = 0; lane < M77_GROUP_SIZE; ++lane) {
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

struct m77_pair_t { ap_uint<64> data; };
struct m77_pair_block_t {
    ap_uint<128> scale;
    ap_uint<128> codes0;
    ap_uint<128> codes1;
    ap_uint<6> group;
    ap_uint<8> pair_index;
};

static void m77_read_pairs(
    const ap_uint<128> *memory,
    hls::stream<m77_pair_block_t> &pairs_out,
    unsigned input_groups,
    unsigned blocks) {
#pragma HLS INLINE off
read_group:
    for (unsigned group = 0; group < input_groups; ++group) {
    read_block:
        for (unsigned block = 0; block < blocks; ++block) {
            const unsigned base = group * blocks * 9 + block * 9;
            const ap_uint<128> scale = memory[base];
        read_pair:
            for (unsigned pair = 0; pair < 4; ++pair) {
#pragma HLS PIPELINE II=1
                m77_pair_block_t item;
                item.scale = scale;
                item.codes0 = memory[base + 1 + 2 * pair];
                item.codes1 = memory[base + 2 + 2 * pair];
                item.group = group;
                item.pair_index = 4 * block + pair;
                pairs_out.write(item);
            }
        }
    }
}

static void m77_compute_pairs(
    hls::stream<m77_pair_block_t> &pairs_in,
    const ap_uint<128> activation[M77_MAX_GROUPS][M77_TOKEN_LANES][4],
    hls::stream<m77_pair_t> &result,
    unsigned input_groups,
    unsigned rows_per_shard) {
#pragma HLS INLINE off
    // Separate even/odd banks remove the two-write conflict that forced M77-A
    // to II=2 in the pair loop.
    ap_int<32> accum_even[M77_TOKEN_LANES][M77_MAX_ROWS_PER_SHARD / 2];
    ap_int<32> accum_odd[M77_TOKEN_LANES][M77_MAX_ROWS_PER_SHARD / 2];
#pragma HLS ARRAY_PARTITION variable=accum_even complete dim=1
#pragma HLS ARRAY_PARTITION variable=accum_odd complete dim=1
#pragma HLS BIND_STORAGE variable=accum_even type=ram_2p impl=bram latency=2
#pragma HLS BIND_STORAGE variable=accum_odd type=ram_2p impl=bram latency=2
clear_token:
    for (unsigned token = 0; token < M77_TOKEN_LANES; ++token) {
    clear_row:
        for (unsigned row = 0; row < rows_per_shard / 2; ++row) {
#pragma HLS PIPELINE II=1
            accum_even[token][row] = 0;
            accum_odd[token][row] = 0;
        }
    }
    // pair_index walks 0..rows/2-1 once per group.  The same slot is not
    // revisited until a complete group (at least 256 iterations in the
    // intended 512-row geometry) has finished, so there is no loop-carried
    // RAW/WAW hazard at the seven-cycle consume pipeline distance.
#pragma HLS DEPENDENCE variable=accum_even inter false
#pragma HLS DEPENDENCE variable=accum_odd inter false
consume_pair:
    for (unsigned n = 0; n < input_groups * rows_per_shard / 2; ++n) {
#pragma HLS PIPELINE II=1
        const m77_pair_block_t data = pairs_in.read();
        const ap_uint<16> tagged0 = data.scale.range(32 * (data.pair_index & 3) + 15, 32 * (data.pair_index & 3));
        const ap_uint<16> tagged1 = data.scale.range(32 * (data.pair_index & 3) + 31, 32 * (data.pair_index & 3) + 16);
    token_loop:
        for (unsigned token = 0; token < M77_TOKEN_LANES; ++token) {
#pragma HLS UNROLL
            ap_int<24> dot0;
            ap_int<24> dot1;
            m77_dot_pair_w2(data.codes0, data.codes1, tagged0, tagged1, activation[data.group][token], dot0, dot1);
            accum_even[token][data.pair_index] += dot0;
            accum_odd[token][data.pair_index] += dot1;
        }
    }
emit_token:
    for (unsigned token = 0; token < M77_TOKEN_LANES; ++token) {
    emit_pair:
        for (unsigned pair = 0; pair < rows_per_shard / 2; ++pair) {
#pragma HLS PIPELINE II=1
            m77_pair_t item;
            item.data.range(31, 0) = (ap_uint<32>)accum_even[token][pair];
            item.data.range(63, 32) = (ap_uint<32>)accum_odd[token][pair];
            result.write(item);
        }
    }
}

template <int SHARD_ID>
static void m77_run_shard(
    const ap_uint<128> *memory,
    const ap_uint<128> activation[M77_MAX_GROUPS][M77_TOKEN_LANES][4],
    hls::stream<m77_pair_t> &result,
    unsigned input_groups,
    unsigned rows_per_shard) {
#pragma HLS INLINE off
    const unsigned blocks = rows_per_shard / 8;
    hls::stream<m77_pair_block_t> pairs_fifo;
#pragma HLS STREAM variable=pairs_fifo depth=2
#pragma HLS DATAFLOW
    m77_read_pairs(memory, pairs_fifo, input_groups, blocks);
    m77_compute_pairs(pairs_fifo, activation, result, input_groups, rows_per_shard);
}

static void m77_merge(
    hls::stream<m77_pair_t> result[M77_SHARDS],
    hls::stream<m77_axis64_t> &rx,
    unsigned rows_per_shard) {
#pragma HLS INLINE off
#pragma HLS ARRAY_PARTITION variable=result complete dim=1
merge_token:
    for (unsigned token = 0; token < M77_TOKEN_LANES; ++token) {
    merge_shard:
        for (unsigned shard = 0; shard < M77_SHARDS; ++shard) {
        merge_pair:
            for (unsigned row = 0; row < rows_per_shard; row += 2) {
#pragma HLS PIPELINE II=1
                m77_axis64_t item;
                item.data = result[shard].read().data;
                item.keep = -1;
                item.strb = -1;
                item.last = token == M77_TOKEN_LANES - 1 && shard == M77_SHARDS - 1 && row + 2 == rows_per_shard;
                rx.write(item);
            }
        }
    }
}

static void m77_six_shards(
    const ap_uint<128> *shard0,
    const ap_uint<128> *shard1,
    const ap_uint<128> *shard2,
    const ap_uint<128> *shard3,
    const ap_uint<128> *shard4,
    const ap_uint<128> *shard5,
    const ap_uint<128> activation[M77_MAX_GROUPS][M77_TOKEN_LANES][4],
    hls::stream<m77_axis64_t> &rx,
    unsigned input_groups,
    unsigned rows_per_shard) {
#pragma HLS INLINE off
#pragma HLS DATAFLOW
    hls::stream<m77_pair_t> results[M77_SHARDS];
#pragma HLS ARRAY_PARTITION variable=results complete dim=1
#pragma HLS STREAM variable=results depth=64
    m77_run_shard<0>(shard0, activation, results[0], input_groups, rows_per_shard);
    m77_run_shard<1>(shard1, activation, results[1], input_groups, rows_per_shard);
    m77_run_shard<2>(shard2, activation, results[2], input_groups, rows_per_shard);
    m77_run_shard<3>(shard3, activation, results[3], input_groups, rows_per_shard);
    m77_run_shard<4>(shard4, activation, results[4], input_groups, rows_per_shard);
    m77_run_shard<5>(shard5, activation, results[5], input_groups, rows_per_shard);
    m77_merge(results, rx, rows_per_shard);
}

void m77_w2_wide(
    hls::stream<m77_axis128_t> &activation_tx,
    const ap_uint<128> *shard0,
    const ap_uint<128> *shard1,
    const ap_uint<128> *shard2,
    const ap_uint<128> *shard3,
    const ap_uint<128> *shard4,
    const ap_uint<128> *shard5,
    hls::stream<m77_axis64_t> &rx,
    unsigned input_groups,
    unsigned rows_per_shard,
    ap_uint<32> &status,
    ap_uint<32> &build_id,
    ap_uint<32> &call_count,
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
    build_id = M77_BUILD_ID;
    call_count = calls;
    processed_macros = macros;
    if (input_groups < 1 || input_groups > M77_MAX_GROUPS || rows_per_shard < 8 ||
        rows_per_shard > M77_MAX_ROWS_PER_SHARD || (rows_per_shard & 7U) != 0) {
        status = 1;
        return;
    }
    ap_uint<128> activation[M77_MAX_GROUPS][M77_TOKEN_LANES][4];
#pragma HLS BIND_STORAGE variable=activation type=ram_2p impl=uram latency=2
    m77_load_activation(activation_tx, activation, input_groups, status);
    m77_six_shards(
        shard0, shard1, shard2, shard3, shard4, shard5, activation, rx,
        input_groups, rows_per_shard);
    calls += 1;
    macros += input_groups * rows_per_shard * M77_SHARDS * M77_TOKEN_LANES;
    call_count = calls;
    processed_macros = macros;
}
