#include "mage_m83_registered_lane.hpp"

// Reuse the golden packed decode, FP16 bit operations, activation loader,
// burst reader and output converter from the M82-A reference. M83 changes
// scheduling only: its dot and FP16 accumulation are separate HLS processes.
#include "mage_m82_groupmajor_stream.cpp"

struct m83_slot_t {
    ap_uint<512> codes;
    ap_uint<16> tagged0;
    ap_uint<16> tagged1;
    ap_uint<9> group;
    ap_uint<2> pair;
    ap_uint<3> shard;
};

struct m83_result_t {
    ap_int<24> dot0;
    ap_int<24> dot1;
    ap_uint<16> tagged0;
    ap_uint<16> tagged1;
    ap_uint<16> activation_scale;
    ap_uint<2> pair;
    ap_uint<3> local_shard;
    ap_uint<3> token;
};

static void m83_clear_triple(
    float even[3][MAGE_T6_TOKENS][M82_PAIRS_PER_SHARD],
    float odd[3][MAGE_T6_TOKENS][M82_PAIRS_PER_SHARD]) {
#pragma HLS INLINE off
clear_local_shard:
    for (unsigned shard = 0; shard < 3; ++shard) {
    clear_token:
        for (unsigned token = 0; token < MAGE_T6_TOKENS; ++token) {
        clear_pair:
            for (unsigned pair = 0; pair < M82_PAIRS_PER_SHARD; ++pair) {
#pragma HLS PIPELINE II=1
                even[shard][token][pair] = 0.0f;
                odd[shard][token][pair] = 0.0f;
            }
        }
    }
}

static void m83_issue_one_group(
    hls::stream<ap_uint<128> > &words, unsigned group, unsigned local_shard,
    unsigned bits, hls::stream<m83_slot_t> &slot_tx) {
#pragma HLS INLINE off
    const ap_uint<128> scale_word = words.read();
issue_slot:
    for (unsigned slot = 0; slot < 4; ++slot) {
        m83_slot_t item;
        item.codes = 0;
issue_code_word:
        for (unsigned word = 0; word < 4; ++word) {
#pragma HLS PIPELINE II=1
            if (word < bits) item.codes.range(128 * word + 127, 128 * word) = words.read();
        }
        item.tagged0 = scale_word.range(32 * slot + 15, 32 * slot);
        item.tagged1 = scale_word.range(32 * slot + 31, 32 * slot + 16);
        item.group = group;
        item.pair = slot;
        item.shard = local_shard;
        slot_tx.write(item);
    }
}

static void m83_issue_triple(
    hls::stream<ap_uint<128> > &words0, hls::stream<ap_uint<128> > &words1,
    hls::stream<ap_uint<128> > &words2, unsigned input_groups, unsigned bits,
    hls::stream<m83_slot_t> &slot_tx) {
#pragma HLS INLINE off
issue_group:
    for (unsigned group = 0; group < input_groups; ++group) {
        m83_issue_one_group(words0, group, 0, bits, slot_tx);
        m83_issue_one_group(words1, group, 1, bits, slot_tx);
        m83_issue_one_group(words2, group, 2, bits, slot_tx);
    }
}

static void m83_dot_lane(
    hls::stream<m83_slot_t> &slot_rx,
    const ap_uint<128> activations[M82_MAX_INPUT_GROUPS][MAGE_T6_TOKENS][4],
    const ap_uint<16> activation_scales[M82_MAX_INPUT_GROUPS][MAGE_T6_TOKENS],
    unsigned input_groups, unsigned bits, hls::stream<m83_result_t> &result_tx) {
#pragma HLS INLINE off
dot_slot:
    for (unsigned index = 0; index < input_groups * 3 * 4; ++index) {
        const m83_slot_t slot = slot_rx.read();
    dot_token:
        for (unsigned token = 0; token < MAGE_T6_TOKENS; ++token) {
#pragma HLS PIPELINE II=2 style=flp
            m83_result_t result;
            m82_dot_pair(slot.codes, activations[slot.group], token, bits,
                         result.dot0, result.dot1, slot.tagged0, slot.tagged1);
            result.tagged0 = slot.tagged0;
            result.tagged1 = slot.tagged1;
            result.activation_scale = activation_scales[slot.group][token];
            result.pair = slot.pair;
            result.local_shard = slot.shard;
            result.token = token;
            result_tx.write(result);
        }
    }
}

static void m83_scale_accumulate(
    hls::stream<m83_result_t> &result_rx,
    float even[3][MAGE_T6_TOKENS][M82_PAIRS_PER_SHARD],
    float odd[3][MAGE_T6_TOKENS][M82_PAIRS_PER_SHARD], unsigned input_groups) {
#pragma HLS INLINE off
accumulate_item:
    for (unsigned index = 0; index < input_groups * 3 * 4 * MAGE_T6_TOKENS; ++index) {
#pragma HLS PIPELINE II=2 style=flp
        const m83_result_t result = result_rx.read();
        const ap_uint<16> dot0_bits = t6_half_to_bits((half)result.dot0);
        const ap_uint<16> dot1_bits = t6_half_to_bits((half)result.dot1);
        const ap_uint<16> scaled0 = mage_t6_half_mul_bits_rne(dot0_bits, result.activation_scale);
        const ap_uint<16> scaled1 = mage_t6_half_mul_bits_rne(dot1_bits, result.activation_scale);
        const ap_uint<16> term0 = mage_t6_half_mul_bits_rne(scaled0, result.tagged0 & 0x7FFFU);
        const ap_uint<16> term1 = mage_t6_half_mul_bits_rne(scaled1, result.tagged1 & 0x7FFFU);
        even[result.local_shard][result.token][result.pair] += (float)t6_bits_to_half(term0);
        odd[result.local_shard][result.token][result.pair] += (float)t6_bits_to_half(term1);
    }
}

static void m83_lane(
    hls::stream<ap_uint<128> > &words0, hls::stream<ap_uint<128> > &words1,
    hls::stream<ap_uint<128> > &words2,
    const ap_uint<128> activations[M82_MAX_INPUT_GROUPS][MAGE_T6_TOKENS][4],
    const ap_uint<16> activation_scales[M82_MAX_INPUT_GROUPS][MAGE_T6_TOKENS],
    float even[3][MAGE_T6_TOKENS][M82_PAIRS_PER_SHARD],
    float odd[3][MAGE_T6_TOKENS][M82_PAIRS_PER_SHARD], unsigned input_groups, unsigned bits) {
#pragma HLS INLINE off
    m83_clear_triple(even, odd);
#pragma HLS DATAFLOW
    hls::stream<m83_slot_t> slot_fifo;
    hls::stream<m83_result_t> result_fifo;
#pragma HLS STREAM variable=slot_fifo depth=24
#pragma HLS STREAM variable=result_fifo depth=48
    m83_issue_triple(words0, words1, words2, input_groups, bits, slot_fifo);
    m83_dot_lane(slot_fifo, activations, activation_scales, input_groups, bits, result_fifo);
    m83_scale_accumulate(result_fifo, even, odd, input_groups);
}

static void m83_readers_and_lanes(
    const ap_uint<128> *shard0, const ap_uint<128> *shard1, const ap_uint<128> *shard2,
    const ap_uint<128> *shard3, const ap_uint<128> *shard4, const ap_uint<128> *shard5,
    const ap_uint<128> activations[M82_MAX_INPUT_GROUPS][MAGE_T6_TOKENS][4],
    const ap_uint<16> activation_scales[M82_MAX_INPUT_GROUPS][MAGE_T6_TOKENS],
    float output_even[M82_SHARDS][MAGE_T6_TOKENS][M82_PAIRS_PER_SHARD],
    float output_odd[M82_SHARDS][MAGE_T6_TOKENS][M82_PAIRS_PER_SHARD],
    unsigned word_count, unsigned input_groups, unsigned bits) {
#pragma HLS INLINE off
#pragma HLS DATAFLOW
    hls::stream<ap_uint<128> > words0, words1, words2, words3, words4, words5;
#pragma HLS STREAM variable=words0 depth=192
#pragma HLS STREAM variable=words1 depth=192
#pragma HLS STREAM variable=words2 depth=192
#pragma HLS STREAM variable=words3 depth=192
#pragma HLS STREAM variable=words4 depth=192
#pragma HLS STREAM variable=words5 depth=192
    m82_burst_reader(shard0, words0, word_count); m82_burst_reader(shard1, words1, word_count);
    m82_burst_reader(shard2, words2, word_count); m82_burst_reader(shard3, words3, word_count);
    m82_burst_reader(shard4, words4, word_count); m82_burst_reader(shard5, words5, word_count);
    m83_lane(words0, words1, words2, activations, activation_scales, output_even, output_odd, input_groups, bits);
    m83_lane(words3, words4, words5, activations, activation_scales, output_even + 3, output_odd + 3, input_groups, bits);
}

void mage_m83_registered_lane(
    hls::stream<mage_t6_axis128_t> &activation_tx,
    const ap_uint<128> *shard0, const ap_uint<128> *shard1, const ap_uint<128> *shard2,
    const ap_uint<128> *shard3, const ap_uint<128> *shard4, const ap_uint<128> *shard5,
    hls::stream<mage_t6_axis64_t> &rx, unsigned input_groups, unsigned bits,
    ap_uint<32> &status, ap_uint<32> &build_id, ap_uint<32> &completed_words_per_port) {
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
#pragma HLS INTERFACE s_axilite port=bits bundle=control
#pragma HLS INTERFACE s_axilite port=status bundle=control
#pragma HLS INTERFACE s_axilite port=build_id bundle=control
#pragma HLS INTERFACE s_axilite port=completed_words_per_port bundle=control
#pragma HLS INTERFACE s_axilite port=return bundle=control
    status = 0; build_id = M83_EXPECT_BUILD_ID; completed_words_per_port = 0;
    if (input_groups < 1 || input_groups > M82_MAX_INPUT_GROUPS || (bits != 2 && bits != 3 && bits != 4)) { status = 1; return; }
    ap_uint<128> activations[M82_MAX_INPUT_GROUPS][MAGE_T6_TOKENS][4];
    ap_uint<16> activation_scales[M82_MAX_INPUT_GROUPS][MAGE_T6_TOKENS];
#pragma HLS BIND_STORAGE variable=activations type=ram_2p impl=uram latency=2
#pragma HLS BIND_STORAGE variable=activation_scales type=ram_2p impl=bram latency=2
    m82_load_activations(activation_tx, activations, activation_scales, input_groups, status);
    if (status != 0) return;
    float output_even[M82_SHARDS][MAGE_T6_TOKENS][M82_PAIRS_PER_SHARD];
    float output_odd[M82_SHARDS][MAGE_T6_TOKENS][M82_PAIRS_PER_SHARD];
#pragma HLS ARRAY_PARTITION variable=output_even complete dim=2
#pragma HLS ARRAY_PARTITION variable=output_odd complete dim=2
    const unsigned word_count = input_groups * (1 + 4 * bits);
    m83_readers_and_lanes(shard0, shard1, shard2, shard3, shard4, shard5,
                          activations, activation_scales, output_even, output_odd,
                          word_count, input_groups, bits);
emit_token:
    for (unsigned token = 0; token < MAGE_T6_TOKENS; ++token) {
    emit_shard:
        for (unsigned shard = 0; shard < M82_SHARDS; ++shard) {
        emit_pair:
            for (unsigned pair = 0; pair < M82_PAIRS_PER_SHARD; ++pair) {
#pragma HLS PIPELINE II=1
                mage_t6_axis64_t item;
                item.data.range(31, 0) = m82_float_to_bits(output_even[shard][token][pair]);
                item.data.range(63, 32) = m82_float_to_bits(output_odd[shard][token][pair]);
                item.keep = -1; item.strb = -1;
                item.last = token == MAGE_T6_TOKENS - 1 && shard == M82_SHARDS - 1 && pair == M82_PAIRS_PER_SHARD - 1;
                rx.write(item);
            }
        }
    }
    completed_words_per_port = word_count;
}
