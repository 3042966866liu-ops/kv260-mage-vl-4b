#include "qwen25_prefill_w4a8.hpp"

#include <cmath>
#include <cstdint>
#include <iostream>
#include <vector>

#include <hls_half.h>
#include <hls_math.h>

static ap_uint<16> half_bits(half value) {
    fp_struct<half> encoded(value);
    return encoded.data();
}

static float bits_float(ap_uint<32> bits) {
    fp_struct<float> decoded(bits);
    return decoded.to_ieee();
}

int main() {
    const unsigned tokens = 1;
    const unsigned groups = 3;
#ifdef TEST_DECODE_DIRECTDDR_CHAIN
    const unsigned blocks = 6;
#else
    const unsigned blocks = 5;
#endif
    hls::stream<prefill_axis128_t> tx;
    hls::stream<prefill_axis128_t> tx_decode;
    hls::stream<prefill_axis128_t> tx_third;
    hls::stream<prefill_axis64_t> rx;
    std::vector<ap_uint<128> > direct_weights0;
    std::vector<ap_uint<128> > direct_weights1;
    std::vector<ap_uint<128> > direct_weights2;
    std::vector<ap_uint<128> > direct_all_weights;
    const unsigned primary_blocks = (blocks + 1) / 2;
    const unsigned secondary_blocks = blocks - primary_blocks;
    std::vector<float> golden(tokens * blocks * PREFILL_OUTPUTS_PER_BLOCK, 0.0f);

    for (unsigned group = 0; group < groups; ++group) {
        ap_int<8> activation[PREFILL_MAX_TOKENS][PREFILL_GROUP_SIZE] = {};
        half activation_scale[PREFILL_MAX_TOKENS] = {};
        ap_int<16> activation_sum[PREFILL_MAX_TOKENS] = {};
        for (unsigned token = 0; token < tokens; ++token) {
            activation_scale[token] = (half)(0.005f + 0.0005f * token + 0.00025f * group);
            int sum = 0;
            for (unsigned input = 0; input < PREFILL_GROUP_SIZE; ++input) {
                const int value = (int)((token * 37 + group * 19 + input * 11) % 255) - 127;
                activation[token][input] = value;
                sum += value;
            }
            activation_sum[token] = sum;
            for (unsigned word = 0; word < 4; ++word) {
                prefill_axis128_t item;
                item.data = 0;
                for (unsigned byte = 0; byte < 16; ++byte) {
                    item.data.range(8 * byte + 7, 8 * byte) =
                        (ap_uint<8>)activation[token][word * 16 + byte];
                }
                item.keep = -1;
                item.strb = -1;
                item.last = 0;
#ifdef TEST_DECODE_TRISTREAM
                tx.write(item);
                tx_decode.write(item);
                tx_third.write(item);
#else
                tx.write(item);
#endif
            }
            prefill_axis128_t metadata;
            metadata.data = 0;
            metadata.data.range(15, 0) = half_bits(activation_scale[token]);
            metadata.data.range(31, 16) = (ap_uint<16>)activation_sum[token];
            metadata.keep = -1;
            metadata.strb = -1;
#if defined(TEST_DECODE_DIRECTDDR) || defined(TEST_DECODE_DIRECTDDR_CHAIN)
            metadata.last = group == groups - 1;
#else
            metadata.last = 0;
#endif
#ifdef TEST_DECODE_TRISTREAM
            tx.write(metadata);
            tx_decode.write(metadata);
            tx_third.write(metadata);
#else
            tx.write(metadata);
#endif
        }

        for (unsigned block = 0; block < blocks; ++block) {
            ap_uint<4> codes[PREFILL_OUTPUTS_PER_BLOCK][PREFILL_GROUP_SIZE];
            half scales[PREFILL_OUTPUTS_PER_BLOCK];
            half zeros[PREFILL_OUTPUTS_PER_BLOCK];
            for (unsigned output = 0; output < PREFILL_OUTPUTS_PER_BLOCK; ++output) {
                scales[output] = (half)(0.01f + 0.001f * output + 0.0005f * group);
                zeros[output] = (half)(6.5f + 0.125f * ((block + output) % 8));
                for (unsigned input = 0; input < PREFILL_GROUP_SIZE; ++input) {
                    codes[output][input] =
                        (group * 7 + block * 5 + output * 3 + input) & 15;
                }
            }
            for (unsigned word = 0; word < PREFILL_WEIGHT_WORDS; ++word) {
                prefill_axis128_t item;
                item.data = 0;
                if (word < 16) {
                    const unsigned output = word >> 1;
                    const unsigned half_word = word & 1U;
                    for (unsigned byte = 0; byte < 16; ++byte) {
                        const unsigned pair = half_word * 16 + byte;
                        const ap_uint<8> packed =
                            (ap_uint<8>)codes[output][2 * pair] |
                            ((ap_uint<8>)codes[output][2 * pair + 1] << 4);
                        item.data.range(8 * byte + 7, 8 * byte) = packed;
                    }
                } else {
                    for (unsigned output = 0; output < PREFILL_OUTPUTS_PER_BLOCK; ++output) {
                        item.data.range(16 * output + 15, 16 * output) =
                            word == 16 ? half_bits(scales[output]) : half_bits(zeros[output]);
                    }
                }
                item.keep = -1;
                item.strb = -1;
#ifdef TEST_DECODE_TRISTREAM
                item.last = group == groups - 1 &&
                    word == PREFILL_WEIGHT_WORDS - 1 &&
                    (block == 1 || block == 3 || block == 4);
                if (block < 2) tx.write(item);
                else if (block < 4) tx_decode.write(item);
                else tx_third.write(item);
#elif defined(TEST_DECODE_DIRECTDDR_CHAIN)
                item.last = 0;
                direct_all_weights.push_back(item.data);
#elif defined(TEST_DECODE_DIRECTDDR)
                item.last = 0;
                if (block < 2) direct_weights0.push_back(item.data);
                else if (block < 4) direct_weights1.push_back(item.data);
                else direct_weights2.push_back(item.data);
#elif defined(TEST_DUALTX_SHARED)
                if (block < primary_blocks) {
                    item.last = group == groups - 1 &&
                        block == primary_blocks - 1 &&
                        word == PREFILL_WEIGHT_WORDS - 1;
                    tx.write(item);
                } else {
                    item.last = group == groups - 1 &&
                        block == blocks - 1 &&
                        word == PREFILL_WEIGHT_WORDS - 1;
                    tx_decode.write(item);
                }
#else
                item.last = group == groups - 1 && block == blocks - 1 &&
                    word == PREFILL_WEIGHT_WORDS - 1;
                tx.write(item);
#endif
            }

            for (unsigned token = 0; token < tokens; ++token) {
                for (unsigned output = 0; output < PREFILL_OUTPUTS_PER_BLOCK; ++output) {
                    float dot = 0.0f;
                    for (unsigned input = 0; input < PREFILL_GROUP_SIZE; ++input) {
                        dot += ((float)codes[output][input] - (float)zeros[output]) *
                            (float)activation[token][input];
                    }
                    const unsigned index =
                        (token * blocks + block) * PREFILL_OUTPUTS_PER_BLOCK + output;
                    const float contribution = dot * (float)scales[output] *
                        (float)activation_scale[token];
                    golden[index] = (float)(half)(golden[index] + contribution);
                }
            }
        }
    }

    ap_uint<32> status = 0;
    ap_uint<32> build_id = 0;
    ap_uint<32> call_count = 0;
    ap_uint<32> processed_macros = 0;
#ifdef TEST_DECODE_DIRECTDDR_CHAIN
    for (unsigned tile = 0; tile < 2; ++tile) {
        for (unsigned shard = 0; shard < 3; ++shard) {
            std::vector<ap_uint<128> > *target = shard == 0 ? &direct_weights0 :
                                                  shard == 1 ? &direct_weights1 :
                                                               &direct_weights2;
            const unsigned block = tile * 3 + shard;
            for (unsigned group = 0; group < groups; ++group) {
                for (unsigned word = 0; word < PREFILL_WEIGHT_WORDS; ++word) {
                    const unsigned index =
                        (group * blocks + block) * PREFILL_WEIGHT_WORDS + word;
                    target->push_back(direct_all_weights[index]);
                }
            }
        }
    }
    const ap_uint<64> descriptor =
        (ap_uint<64>)1 | ((ap_uint<64>)1 << 16) | ((ap_uint<64>)1 << 32);
    ap_uint<128> descriptors[DIRECTDDR_MAX_CHAIN_TILES] = {};
    descriptors[0] = descriptor;
    descriptors[1] = descriptor;
    qwen25_decode_w4a8_directddr_chain(
        tx,
        direct_weights0.data(), direct_weights1.data(), direct_weights2.data(),
        descriptors, rx, groups, 2,
        status, build_id, call_count, processed_macros);
#elif defined(TEST_DECODE_TRISTREAM)
    qwen25_decode_w4a8_tristream(
        tx, tx_decode, tx_third, rx, groups, 2, 2, 1,
        status, build_id, call_count, processed_macros);
#elif defined(TEST_DECODE_DIRECTDDR)
    qwen25_decode_w4a8_directddr(
        tx,
        direct_weights0.data(), direct_weights1.data(), direct_weights2.data(),
        rx, groups, 2, 2, 1,
        status, build_id, call_count, processed_macros);
#elif defined(TEST_DUALTX_SHARED)
    qwen25_prefill_w4a8_dualtx(
        tx, tx_decode, rx, tokens, groups,
        primary_blocks, secondary_blocks,
        status, build_id, call_count, processed_macros);
#elif defined(TEST_DECODE_DUALHP)
    qwen25_decode_w4a8(
        tx, rx, groups, blocks,
        status, build_id, call_count, processed_macros);
#else
    qwen25_prefill_w4a8(
        tx, rx, tokens, groups, blocks,
        status, build_id, call_count, processed_macros);
#endif

    float worst = 0.0f;
    unsigned mismatch_count = 0;
    for (unsigned token = 0; token < tokens; ++token) {
        for (unsigned block = 0; block < blocks; ++block) {
            for (unsigned word = 0; word < PREFILL_RESULT_WORDS; ++word) {
                const prefill_axis64_t item = rx.read();
                const float values[2] = {
                    bits_float(item.data.range(31, 0)),
                    bits_float(item.data.range(63, 32)),
                };
                for (unsigned lane = 0; lane < 2; ++lane) {
                    const unsigned output = 2 * word + lane;
                    const unsigned index =
                        (token * blocks + block) * PREFILL_OUTPUTS_PER_BLOCK + output;
                    worst = std::fmax(worst, std::fabs(values[lane] - golden[index]));
                    if (std::fabs(values[lane] - golden[index]) > 2.0e-3f &&
                        mismatch_count < 12) {
                        std::cerr << "MISMATCH token=" << token
                                  << " block=" << block
                                  << " output=" << output
                                  << " actual=" << values[lane]
                                  << " golden=" << golden[index] << std::endl;
                        ++mismatch_count;
                    }
                }
                const bool expected_last = token == tokens - 1 &&
                    block == blocks - 1 && word == PREFILL_RESULT_WORDS - 1;
                if ((bool)item.last != expected_last) {
                    std::cerr << "TLAST mismatch" << std::endl;
                    return 1;
                }
            }
        }
    }
    std::cout << "PREFILL_CSIM max_abs=" << worst
              << " status=" << status
              << " build_id=0x" << std::hex << build_id << std::dec
              << " calls=" << call_count
              << " macros=" << processed_macros << std::endl;
    const ap_uint<32> expected_build_id =
#ifdef TEST_DECODE_TRISTREAM
        DECODE_TRISTREAM_BUILD_ID;
#elif defined(TEST_DECODE_DIRECTDDR_CHAIN)
        DECODE_DIRECTDDR_CHAIN_BUILD_ID;
#elif defined(TEST_DECODE_DIRECTDDR)
        DECODE_DIRECTDDR_BUILD_ID;
#elif defined(TEST_DUALTX_SHARED)
        DUALTX_SHARED_BUILD_ID;
#elif defined(TEST_DECODE_DUALHP)
        DECODE_DUALHP_BUILD_ID;
#else
        PREFILL_BUILD_ID;
#endif
    if (status != 0 || build_id != expected_build_id || call_count != 1 ||
        processed_macros != tokens * groups * blocks || worst > 2.0e-3f ||
        !tx.empty() || !tx_decode.empty() || !tx_third.empty() || !rx.empty()) {
        return 1;
    }
    std::cout << "QWEN_PREFILL_W4A8_CSIM_PASS" << std::endl;
    return 0;
}
