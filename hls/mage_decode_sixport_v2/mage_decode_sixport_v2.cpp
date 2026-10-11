#include "mage_decode_sixport_v2.hpp"

#include <hls_half.h>
#include <hls_math.h>

static half v2_bits_to_half(ap_uint<16> bits) {
#pragma HLS INLINE
    fp_struct<half> value(bits);
    return value.to_half();
}

static ap_uint<32> v2_float_to_bits(float value) {
#pragma HLS INLINE
    fp_struct<float> encoded(value);
    return encoded.data();
}

static ap_int<27> v2_pack_weights(ap_int<5> weight0, ap_int<5> weight1) {
#pragma HLS INLINE
    const ap_int<14> upper = (ap_int<14>)weight1 - (weight0 < 0 ? 1 : 0);
    ap_int<27> packed = (ap_int<27>)upper << 13;
    packed.range(12, 0) = (ap_uint<13>)weight0;
    return packed;
}

static void v2_packed_mac2(
    ap_int<8> activation,
    ap_int<5> weight0,
    ap_int<5> weight1,
    ap_int<16> &product0,
    ap_int<16> &product1) {
#pragma HLS INLINE
    const ap_int<27> packed_weights = v2_pack_weights(weight0, weight1);
    const ap_int<45> packed_product = packed_weights * activation;
#pragma HLS BIND_OP variable=packed_product op=mul impl=dsp
    const ap_int<13> low_product = (ap_int<13>)packed_product.range(12, 0);
    ap_int<32> high_product = (ap_int<32>)(packed_product >> 13);
    if (low_product < 0) high_product += 1;
    product0 = low_product;
    product1 = high_product;
}

static void v2_load_activations(
    hls::stream<mage_v2_axis128_t> &activation_tx,
    ap_uint<128> activation0[MAGE_V2_MAX_INPUT_GROUPS][4],
    ap_uint<128> activation1[MAGE_V2_MAX_INPUT_GROUPS][4],
    ap_uint<128> activation2[MAGE_V2_MAX_INPUT_GROUPS][4],
    ap_uint<128> activation3[MAGE_V2_MAX_INPUT_GROUPS][4],
    ap_uint<128> activation4[MAGE_V2_MAX_INPUT_GROUPS][4],
    ap_uint<128> activation5[MAGE_V2_MAX_INPUT_GROUPS][4],
    ap_uint<16> scale0[MAGE_V2_MAX_INPUT_GROUPS],
    ap_uint<16> scale1[MAGE_V2_MAX_INPUT_GROUPS],
    ap_uint<16> scale2[MAGE_V2_MAX_INPUT_GROUPS],
    ap_uint<16> scale3[MAGE_V2_MAX_INPUT_GROUPS],
    ap_uint<16> scale4[MAGE_V2_MAX_INPUT_GROUPS],
    ap_uint<16> scale5[MAGE_V2_MAX_INPUT_GROUPS],
    unsigned input_groups,
    ap_uint<32> &status) {
#pragma HLS INLINE off
v2_load_group:
    for (unsigned group = 0; group < input_groups; ++group) {
    v2_load_word:
        for (unsigned word = 0; word < 5; ++word) {
#pragma HLS PIPELINE II=1
            const mage_v2_axis128_t item = activation_tx.read();
            const bool expected_last = group == input_groups - 1 && word == 4;
            if ((bool)item.last != expected_last) status = 2;
            if (word < 4) {
                activation0[group][word] = item.data;
                activation1[group][word] = item.data;
                activation2[group][word] = item.data;
                activation3[group][word] = item.data;
                activation4[group][word] = item.data;
                activation5[group][word] = item.data;
            } else {
                const ap_uint<16> value = item.data.range(15, 0);
                scale0[group] = value;
                scale1[group] = value;
                scale2[group] = value;
                scale3[group] = value;
                scale4[group] = value;
                scale5[group] = value;
            }
        }
    }
}

struct v2_pair_packet_t {
    ap_uint<512> codes;
    ap_uint<16> tagged_scale0;
    ap_uint<16> tagged_scale1;
    ap_uint<16> group;
    ap_uint<16> pair;
};

struct v2_chunk_packet_t {
    ap_int<20> sum0;
    ap_int<20> sum1;
    ap_uint<16> tagged_scale0;
    ap_uint<16> tagged_scale1;
    ap_uint<16> group;
    ap_uint<16> pair;
    ap_uint<1> last_chunk;
};

struct v2_result_pair_t {
    ap_uint<64> data;
};

template <int SHARD_ID>
static void v2_read_words(
    const ap_uint<128> *memory,
    hls::stream<ap_uint<128> > &words,
    unsigned total_words) {
#pragma HLS INLINE off
v2_read_word:
    for (unsigned index = 0; index < total_words; ++index) {
#pragma HLS PIPELINE II=1
        words.write(memory[index]);
    }
}

template <int SHARD_ID>
static void v2_assemble_pairs(
    hls::stream<ap_uint<128> > &words,
    hls::stream<v2_pair_packet_t> &pairs,
    unsigned input_groups,
    unsigned rows_per_shard,
    unsigned bits,
    unsigned total_words) {
#pragma HLS INLINE off
    const unsigned blocks_per_group = rows_per_shard / 8;
    ap_uint<128> scale_word = 0;
    ap_uint<512> codes = 0;
    unsigned group = 0;
    unsigned block = 0;
    unsigned slot = 0;
    unsigned code_word = 0;
    bool expect_scale = true;
v2_assemble_word:
    for (unsigned index = 0; index < total_words; ++index) {
#pragma HLS PIPELINE II=1
        const ap_uint<128> word = words.read();
        if (expect_scale) {
            scale_word = word;
            expect_scale = false;
            codes = 0;
        } else {
            if (code_word == 0) codes.range(127, 0) = word;
            else if (code_word == 1) codes.range(255, 128) = word;
            else if (code_word == 2) codes.range(383, 256) = word;
            else codes.range(511, 384) = word;
            if (code_word + 1 == bits) {
                v2_pair_packet_t packet;
                packet.codes = codes;
                packet.group = group;
                packet.pair = block * 4 + slot;
                if (slot == 0) {
                    packet.tagged_scale0 = scale_word.range(15, 0);
                    packet.tagged_scale1 = scale_word.range(31, 16);
                } else if (slot == 1) {
                    packet.tagged_scale0 = scale_word.range(47, 32);
                    packet.tagged_scale1 = scale_word.range(63, 48);
                } else if (slot == 2) {
                    packet.tagged_scale0 = scale_word.range(79, 64);
                    packet.tagged_scale1 = scale_word.range(95, 80);
                } else {
                    packet.tagged_scale0 = scale_word.range(111, 96);
                    packet.tagged_scale1 = scale_word.range(127, 112);
                }
                pairs.write(packet);
                codes = 0;
                code_word = 0;
                ++slot;
                if (slot == 4) {
                    slot = 0;
                    ++block;
                    if (block == blocks_per_group) {
                        block = 0;
                        ++group;
                    }
                    expect_scale = true;
                }
            } else {
                ++code_word;
            }
        }
    }
}

template <int SHARD_ID>
static void v2_compute_chunks(
    hls::stream<v2_pair_packet_t> &pairs,
    hls::stream<v2_chunk_packet_t> &chunks,
    const ap_uint<128> activations[MAGE_V2_MAX_INPUT_GROUPS][4],
    unsigned input_groups,
    unsigned rows_per_shard,
    unsigned bits) {
#pragma HLS INLINE off
    const unsigned total_pairs = input_groups * (rows_per_shard / 2);
    v2_pair_packet_t current;
v2_compute_step:
    for (unsigned step = 0; step < total_pairs * 2; ++step) {
#pragma HLS PIPELINE II=1
        const unsigned chunk = step & 1U;
        if (chunk == 0) current = pairs.read();
        const ap_uint<128> activation_word0 = activations[current.group][2 * chunk];
        const ap_uint<128> activation_word1 = activations[current.group][2 * chunk + 1];
        ap_uint<256> activation_bits = 0;
        activation_bits.range(127, 0) = activation_word0;
        activation_bits.range(255, 128) = activation_word1;

        ap_uint<128> code_chunk0 = 0;
        ap_uint<128> code_chunk1 = 0;
        if (bits == 2) {
            if (chunk == 0) {
                code_chunk0.range(63, 0) = current.codes.range(63, 0);
                code_chunk1.range(63, 0) = current.codes.range(191, 128);
            } else {
                code_chunk0.range(63, 0) = current.codes.range(127, 64);
                code_chunk1.range(63, 0) = current.codes.range(255, 192);
            }
        } else if (bits == 3) {
            if (chunk == 0) {
                code_chunk0.range(95, 0) = current.codes.range(95, 0);
                code_chunk1.range(95, 0) = current.codes.range(287, 192);
            } else {
                code_chunk0.range(95, 0) = current.codes.range(191, 96);
                code_chunk1.range(95, 0) = current.codes.range(383, 288);
            }
        } else {
            if (chunk == 0) {
                code_chunk0 = current.codes.range(127, 0);
                code_chunk1 = current.codes.range(383, 256);
            } else {
                code_chunk0 = current.codes.range(255, 128);
                code_chunk1 = current.codes.range(511, 384);
            }
        }

        const bool orientation0 = current.tagged_scale0[15];
        const bool orientation1 = current.tagged_scale1[15];
        const ap_int<5> half_range = (ap_int<5>)(1 << (bits - 1));
        const ap_int<5> negative_half = (ap_int<5>)(-half_range);
        const ap_int<5> shifted_half = (ap_int<5>)(negative_half + (ap_int<5>)1);
        const ap_int<5> qmin0 = orientation0 ? shifted_half : negative_half;
        const ap_int<5> qmin1 = orientation1 ? shifted_half : negative_half;
        ap_int<20> sum0 = 0;
        ap_int<20> sum1 = 0;
    v2_mac_lane:
        for (unsigned lane = 0; lane < MAGE_V2_MAC_LANES; ++lane) {
#pragma HLS UNROLL
            const ap_int<8> activation = (ap_int<8>)activation_bits.range(
                8 * lane + 7, 8 * lane);
            ap_int<5> weight0;
            ap_int<5> weight1;
            if (bits == 2) {
                weight0 = (ap_uint<2>)code_chunk0.range(2 * lane + 1, 2 * lane) + qmin0;
                weight1 = (ap_uint<2>)code_chunk1.range(2 * lane + 1, 2 * lane) + qmin1;
            } else if (bits == 3) {
                weight0 = (ap_uint<3>)code_chunk0.range(3 * lane + 2, 3 * lane) + qmin0;
                weight1 = (ap_uint<3>)code_chunk1.range(3 * lane + 2, 3 * lane) + qmin1;
            } else {
                weight0 = (ap_uint<4>)code_chunk0.range(4 * lane + 3, 4 * lane) + qmin0;
                weight1 = (ap_uint<4>)code_chunk1.range(4 * lane + 3, 4 * lane) + qmin1;
            }
            ap_int<16> product0;
            ap_int<16> product1;
            v2_packed_mac2(activation, weight0, weight1, product0, product1);
            sum0 += product0;
            sum1 += product1;
        }
        v2_chunk_packet_t packet;
        packet.sum0 = sum0;
        packet.sum1 = sum1;
        packet.tagged_scale0 = current.tagged_scale0;
        packet.tagged_scale1 = current.tagged_scale1;
        packet.group = current.group;
        packet.pair = current.pair;
        packet.last_chunk = chunk;
        chunks.write(packet);
    }
}

template <int SHARD_ID>
static void v2_accumulate_emit(
    hls::stream<v2_chunk_packet_t> &chunks,
    hls::stream<v2_result_pair_t> &results,
    const ap_uint<16> activation_scales[MAGE_V2_MAX_INPUT_GROUPS],
    unsigned input_groups,
    unsigned rows_per_shard) {
#pragma HLS INLINE off
    float output_even[MAGE_V2_MAX_ROWS_PER_SHARD / 2];
    float output_odd[MAGE_V2_MAX_ROWS_PER_SHARD / 2];
#pragma HLS BIND_STORAGE variable=output_even type=ram_2p impl=bram latency=2
#pragma HLS BIND_STORAGE variable=output_odd type=ram_2p impl=bram latency=2
v2_clear_output:
    for (unsigned pair = 0; pair < rows_per_shard / 2; ++pair) {
#pragma HLS PIPELINE II=1
        output_even[pair] = 0.0f;
        output_odd[pair] = 0.0f;
    }
    ap_int<20> partial0 = 0;
    ap_int<20> partial1 = 0;
    const unsigned total_steps = input_groups * (rows_per_shard / 2) * 2;
v2_accumulate_step:
    for (unsigned step = 0; step < total_steps; ++step) {
#pragma HLS PIPELINE II=1
#pragma HLS DEPENDENCE variable=output_even inter false
#pragma HLS DEPENDENCE variable=output_odd inter false
        const v2_chunk_packet_t packet = chunks.read();
        if (!packet.last_chunk) {
            partial0 = packet.sum0;
            partial1 = packet.sum1;
        } else {
            const ap_int<24> dot0 = (ap_int<24>)partial0 + packet.sum0;
            const ap_int<24> dot1 = (ap_int<24>)partial1 + packet.sum1;
            const float activation_scale = (float)v2_bits_to_half(activation_scales[packet.group]);
            const float weight_scale0 = (float)v2_bits_to_half(packet.tagged_scale0 & 0x7FFFU);
            const float weight_scale1 = (float)v2_bits_to_half(packet.tagged_scale1 & 0x7FFFU);
            const unsigned pair = packet.pair;
            output_even[pair] += (float)dot0 * activation_scale * weight_scale0;
            output_odd[pair] += (float)dot1 * activation_scale * weight_scale1;
        }
    }
v2_emit_pair:
    for (unsigned pair = 0; pair < rows_per_shard / 2; ++pair) {
#pragma HLS PIPELINE II=1
        v2_result_pair_t item;
        item.data.range(31, 0) = v2_float_to_bits(output_even[pair]);
        item.data.range(63, 32) = v2_float_to_bits(output_odd[pair]);
        results.write(item);
    }
}

template <int SHARD_ID>
static void v2_run_shard(
    const ap_uint<128> *memory,
    const ap_uint<128> activations[MAGE_V2_MAX_INPUT_GROUPS][4],
    const ap_uint<16> activation_scales[MAGE_V2_MAX_INPUT_GROUPS],
    hls::stream<v2_result_pair_t> &results,
    unsigned input_groups,
    unsigned rows_per_shard,
    unsigned bits) {
#pragma HLS INLINE off
#pragma HLS DATAFLOW
    hls::stream<ap_uint<128> > words;
    hls::stream<v2_pair_packet_t> pairs;
    hls::stream<v2_chunk_packet_t> chunks;
#pragma HLS STREAM variable=words depth=64
#pragma HLS STREAM variable=pairs depth=32
#pragma HLS STREAM variable=chunks depth=32
#pragma HLS BIND_STORAGE variable=words type=fifo impl=lutram
#pragma HLS BIND_STORAGE variable=pairs type=fifo impl=lutram
#pragma HLS BIND_STORAGE variable=chunks type=fifo impl=lutram
    const unsigned total_words = input_groups * (rows_per_shard / 8) * (1 + 4 * bits);
    v2_read_words<SHARD_ID>(memory, words, total_words);
    v2_assemble_pairs<SHARD_ID>(words, pairs, input_groups, rows_per_shard, bits, total_words);
    v2_compute_chunks<SHARD_ID>(pairs, chunks, activations, input_groups, rows_per_shard, bits);
    v2_accumulate_emit<SHARD_ID>(chunks, results, activation_scales, input_groups, rows_per_shard);
}

static void v2_merge_results(
    hls::stream<v2_result_pair_t> results[6],
    hls::stream<mage_v2_axis64_t> &rx,
    unsigned rows_per_shard) {
#pragma HLS INLINE off
v2_merge_shard:
    for (unsigned shard = 0; shard < 6; ++shard) {
    v2_merge_pair:
        for (unsigned pair = 0; pair < rows_per_shard / 2; ++pair) {
#pragma HLS PIPELINE II=1
            mage_v2_axis64_t item;
            item.data = results[shard].read().data;
            item.keep = -1;
            item.strb = -1;
            item.last = shard == 5 && pair == rows_per_shard / 2 - 1;
            rx.write(item);
        }
    }
}

static void v2_run_sixport(
    const ap_uint<128> *shard0,
    const ap_uint<128> *shard1,
    const ap_uint<128> *shard2,
    const ap_uint<128> *shard3,
    const ap_uint<128> *shard4,
    const ap_uint<128> *shard5,
    const ap_uint<128> activation0[MAGE_V2_MAX_INPUT_GROUPS][4],
    const ap_uint<128> activation1[MAGE_V2_MAX_INPUT_GROUPS][4],
    const ap_uint<128> activation2[MAGE_V2_MAX_INPUT_GROUPS][4],
    const ap_uint<128> activation3[MAGE_V2_MAX_INPUT_GROUPS][4],
    const ap_uint<128> activation4[MAGE_V2_MAX_INPUT_GROUPS][4],
    const ap_uint<128> activation5[MAGE_V2_MAX_INPUT_GROUPS][4],
    const ap_uint<16> scale0[MAGE_V2_MAX_INPUT_GROUPS],
    const ap_uint<16> scale1[MAGE_V2_MAX_INPUT_GROUPS],
    const ap_uint<16> scale2[MAGE_V2_MAX_INPUT_GROUPS],
    const ap_uint<16> scale3[MAGE_V2_MAX_INPUT_GROUPS],
    const ap_uint<16> scale4[MAGE_V2_MAX_INPUT_GROUPS],
    const ap_uint<16> scale5[MAGE_V2_MAX_INPUT_GROUPS],
    hls::stream<mage_v2_axis64_t> &rx,
    unsigned input_groups,
    unsigned rows_per_shard,
    unsigned bits) {
#pragma HLS INLINE off
#pragma HLS DATAFLOW
    hls::stream<v2_result_pair_t> results[6];
#pragma HLS STREAM variable=results depth=32
#pragma HLS BIND_STORAGE variable=results type=fifo impl=lutram
    v2_run_shard<0>(shard0, activation0, scale0, results[0], input_groups, rows_per_shard, bits);
    v2_run_shard<1>(shard1, activation1, scale1, results[1], input_groups, rows_per_shard, bits);
    v2_run_shard<2>(shard2, activation2, scale2, results[2], input_groups, rows_per_shard, bits);
    v2_run_shard<3>(shard3, activation3, scale3, results[3], input_groups, rows_per_shard, bits);
    v2_run_shard<4>(shard4, activation4, scale4, results[4], input_groups, rows_per_shard, bits);
    v2_run_shard<5>(shard5, activation5, scale5, results[5], input_groups, rows_per_shard, bits);
    v2_merge_results(results, rx, rows_per_shard);
}

void mage_decode_sixport_v2(
    hls::stream<mage_v2_axis128_t> &activation_tx,
    const ap_uint<128> *shard0,
    const ap_uint<128> *shard1,
    const ap_uint<128> *shard2,
    const ap_uint<128> *shard3,
    const ap_uint<128> *shard4,
    const ap_uint<128> *shard5,
    hls::stream<mage_v2_axis64_t> &rx,
    unsigned input_groups,
    unsigned rows_per_shard,
    unsigned bits,
    ap_uint<32> &status,
    ap_uint<32> &build_id,
    ap_uint<32> &call_count,
    ap_uint<32> &processed_macros) {
#pragma HLS INTERFACE axis port=activation_tx
#pragma HLS INTERFACE m_axi port=shard0 offset=slave bundle=weights0 depth=524288 max_read_burst_length=64 num_read_outstanding=16
#pragma HLS INTERFACE m_axi port=shard1 offset=slave bundle=weights1 depth=524288 max_read_burst_length=64 num_read_outstanding=16
#pragma HLS INTERFACE m_axi port=shard2 offset=slave bundle=weights2 depth=524288 max_read_burst_length=64 num_read_outstanding=16
#pragma HLS INTERFACE m_axi port=shard3 offset=slave bundle=weights3 depth=524288 max_read_burst_length=64 num_read_outstanding=16
#pragma HLS INTERFACE m_axi port=shard4 offset=slave bundle=weights4 depth=524288 max_read_burst_length=64 num_read_outstanding=16
#pragma HLS INTERFACE m_axi port=shard5 offset=slave bundle=weights5 depth=524288 max_read_burst_length=64 num_read_outstanding=16
#pragma HLS INTERFACE axis port=rx
#pragma HLS INTERFACE s_axilite port=shard0 bundle=control
#pragma HLS INTERFACE s_axilite port=shard1 bundle=control
#pragma HLS INTERFACE s_axilite port=shard2 bundle=control
#pragma HLS INTERFACE s_axilite port=shard3 bundle=control
#pragma HLS INTERFACE s_axilite port=shard4 bundle=control
#pragma HLS INTERFACE s_axilite port=shard5 bundle=control
#pragma HLS INTERFACE s_axilite port=input_groups bundle=control
#pragma HLS INTERFACE s_axilite port=rows_per_shard bundle=control
#pragma HLS INTERFACE s_axilite port=bits bundle=control
#pragma HLS INTERFACE s_axilite port=status bundle=control
#pragma HLS INTERFACE s_axilite port=build_id bundle=control
#pragma HLS INTERFACE s_axilite port=call_count bundle=control
#pragma HLS INTERFACE s_axilite port=processed_macros bundle=control
#pragma HLS INTERFACE s_axilite port=return bundle=control
    static ap_uint<32> calls = 0;
    static ap_uint<32> macros = 0;
    status = 0;
    build_id = MAGE_V2_BUILD_ID;
    call_count = calls;
    processed_macros = macros;
    if (input_groups < 1 || input_groups > MAGE_V2_MAX_INPUT_GROUPS ||
        rows_per_shard < 16 || rows_per_shard > MAGE_V2_MAX_ROWS_PER_SHARD ||
        (rows_per_shard & 7U) != 0 || (bits != 2 && bits != 3 && bits != 4)) {
        status = 1;
        return;
    }

    ap_uint<128> activation0[MAGE_V2_MAX_INPUT_GROUPS][4];
    ap_uint<128> activation1[MAGE_V2_MAX_INPUT_GROUPS][4];
    ap_uint<128> activation2[MAGE_V2_MAX_INPUT_GROUPS][4];
    ap_uint<128> activation3[MAGE_V2_MAX_INPUT_GROUPS][4];
    ap_uint<128> activation4[MAGE_V2_MAX_INPUT_GROUPS][4];
    ap_uint<128> activation5[MAGE_V2_MAX_INPUT_GROUPS][4];
    ap_uint<16> scale0[MAGE_V2_MAX_INPUT_GROUPS];
    ap_uint<16> scale1[MAGE_V2_MAX_INPUT_GROUPS];
    ap_uint<16> scale2[MAGE_V2_MAX_INPUT_GROUPS];
    ap_uint<16> scale3[MAGE_V2_MAX_INPUT_GROUPS];
    ap_uint<16> scale4[MAGE_V2_MAX_INPUT_GROUPS];
    ap_uint<16> scale5[MAGE_V2_MAX_INPUT_GROUPS];
#pragma HLS BIND_STORAGE variable=activation0 type=ram_2p impl=uram latency=2
#pragma HLS BIND_STORAGE variable=activation1 type=ram_2p impl=uram latency=2
#pragma HLS BIND_STORAGE variable=activation2 type=ram_2p impl=uram latency=2
#pragma HLS BIND_STORAGE variable=activation3 type=ram_2p impl=uram latency=2
#pragma HLS BIND_STORAGE variable=activation4 type=ram_2p impl=uram latency=2
#pragma HLS BIND_STORAGE variable=activation5 type=ram_2p impl=uram latency=2
#pragma HLS BIND_STORAGE variable=scale0 type=ram_2p impl=bram latency=2
#pragma HLS BIND_STORAGE variable=scale1 type=ram_2p impl=bram latency=2
#pragma HLS BIND_STORAGE variable=scale2 type=ram_2p impl=bram latency=2
#pragma HLS BIND_STORAGE variable=scale3 type=ram_2p impl=bram latency=2
#pragma HLS BIND_STORAGE variable=scale4 type=ram_2p impl=bram latency=2
#pragma HLS BIND_STORAGE variable=scale5 type=ram_2p impl=bram latency=2

    v2_load_activations(
        activation_tx,
        activation0, activation1, activation2, activation3, activation4, activation5,
        scale0, scale1, scale2, scale3, scale4, scale5,
        input_groups, status);
    v2_run_sixport(
        shard0, shard1, shard2, shard3, shard4, shard5,
        activation0, activation1, activation2, activation3, activation4, activation5,
        scale0, scale1, scale2, scale3, scale4, scale5,
        rx, input_groups, rows_per_shard, bits);
    calls += 1;
    macros += input_groups * rows_per_shard * 6;
    call_count = calls;
    processed_macros = macros;
}
