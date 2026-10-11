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
    const unsigned blocks = 5;
    hls::stream<prefill_axis128_t> tx;
    hls::stream<prefill_axis64_t> rx;
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
                tx.write(item);
            }
            prefill_axis128_t metadata;
            metadata.data = 0;
            metadata.data.range(15, 0) = half_bits(activation_scale[token]);
            metadata.data.range(31, 16) = (ap_uint<16>)activation_sum[token];
            metadata.keep = -1;
            metadata.strb = -1;
            metadata.last = 0;
            tx.write(metadata);
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
                item.last = group == groups - 1 && block == blocks - 1 &&
                    word == PREFILL_WEIGHT_WORDS - 1;
                tx.write(item);
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
    qwen25_prefill_w4a8(
        tx, rx, tokens, groups, blocks,
        status, build_id, call_count, processed_macros);

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
    if (status != 0 || build_id != PREFILL_BUILD_ID || call_count != 1 ||
        processed_macros != tokens * groups * blocks || worst > 2.0e-3f ||
        !tx.empty() || !rx.empty()) {
        return 1;
    }
    std::cout << "QWEN_PREFILL_W4A8_CSIM_PASS" << std::endl;
    return 0;
}
