#include "mage_decode_sixport_v2.hpp"

#include <hls_half.h>
#include <hls_math.h>

#include <iostream>
#include <vector>

static ap_uint<16> v2_half_bits(half value) {
    fp_struct<half> encoded(value);
    return encoded.data();
}

static float v2_float_from_bits(ap_uint<32> bits) {
    fp_struct<float> value(bits);
    return value.to_float();
}

static int v2_signed_weight(unsigned shard, unsigned row, unsigned group, unsigned index, int qmin, int qmax) {
    const unsigned span = qmax - qmin + 1;
    return qmin + ((shard * 17 + row * 11 + group * 7 + index * 3) % span);
}

static int v2_run_case(unsigned bits) {
    const unsigned groups = 2;
    const unsigned rows = 16;
    const unsigned total_words = groups * (rows / 8) * (1 + 4 * bits);
    std::vector<ap_uint<128> > memory[6];
    float expected[6][rows] = {};
    hls::stream<mage_v2_axis128_t> activation_tx;
    hls::stream<mage_v2_axis64_t> rx;
    int activations[groups][MAGE_V2_GROUP_SIZE];

    for (unsigned group = 0; group < groups; ++group) {
        for (unsigned word = 0; word < 4; ++word) {
            mage_v2_axis128_t item;
            item.data = 0;
            for (unsigned byte = 0; byte < 16; ++byte) {
                const unsigned index = word * 16 + byte;
                const int value = ((group * 13 + index * 5) % 31) - 15;
                activations[group][index] = value;
                item.data.range(8 * byte + 7, 8 * byte) = (ap_uint<8>)(ap_int<8>)value;
            }
            item.keep = -1;
            item.strb = -1;
            item.last = false;
            activation_tx.write(item);
        }
        mage_v2_axis128_t metadata;
        metadata.data = v2_half_bits((half)1.0f);
        metadata.keep = -1;
        metadata.strb = -1;
        metadata.last = group == groups - 1;
        activation_tx.write(metadata);
    }

    for (unsigned shard = 0; shard < 6; ++shard) {
        memory[shard].resize(total_words);
        unsigned cursor = 0;
        for (unsigned group = 0; group < groups; ++group) {
            for (unsigned block = 0; block < rows / 8; ++block) {
                ap_uint<128> scale_word = 0;
                for (unsigned row_in_block = 0; row_in_block < 8; ++row_in_block) {
                    const unsigned row = block * 8 + row_in_block;
                    const bool orientation = ((shard + row + group) & 1U) != 0;
                    ap_uint<16> tagged = v2_half_bits((half)1.0f);
                    tagged[15] = orientation;
                    scale_word.range(16 * row_in_block + 15, 16 * row_in_block) = tagged;
                }
                memory[shard][cursor++] = scale_word;
                for (unsigned slot = 0; slot < 4; ++slot) {
                    ap_uint<512> packed = 0;
                    for (unsigned in_pair = 0; in_pair < 2; ++in_pair) {
                        const unsigned row = block * 8 + 2 * slot + in_pair;
                        const bool orientation = ((shard + row + group) & 1U) != 0;
                        const int half_range = 1 << (bits - 1);
                        const int qmin = orientation ? -half_range + 1 : -half_range;
                        const int qmax = orientation ? half_range : half_range - 1;
                        for (unsigned index = 0; index < MAGE_V2_GROUP_SIZE; ++index) {
                            const int weight = v2_signed_weight(shard, row, group, index, qmin, qmax);
                            const unsigned code = weight - qmin;
                            const unsigned offset = in_pair * MAGE_V2_GROUP_SIZE * bits + index * bits;
                            if (bits == 2) packed.range(offset + 1, offset) = code;
                            else if (bits == 3) packed.range(offset + 2, offset) = code;
                            else packed.range(offset + 3, offset) = code;
                            expected[shard][row] += (float)(weight * activations[group][index]);
                        }
                    }
                    for (unsigned word = 0; word < bits; ++word) {
                        memory[shard][cursor++] = packed.range(128 * word + 127, 128 * word);
                    }
                }
            }
        }
        if (cursor != total_words) return 1;
    }

    ap_uint<32> status = 0;
    ap_uint<32> build_id = 0;
    ap_uint<32> call_count = 0;
    ap_uint<32> macros = 0;
    mage_decode_sixport_v2(
        activation_tx,
        memory[0].data(), memory[1].data(), memory[2].data(),
        memory[3].data(), memory[4].data(), memory[5].data(),
        rx, groups, rows, bits, status, build_id, call_count, macros);
    const unsigned expected_calls = bits - 1;
    const unsigned expected_macros = expected_calls * groups * rows * 6;
    if (status != 0 || build_id != MAGE_V2_BUILD_ID ||
        call_count != expected_calls || macros != expected_macros) {
        std::cerr << "control failure bits=" << bits << " status=" << status
                  << " calls=" << call_count << " macros=" << macros << std::endl;
        return 1;
    }
    for (unsigned shard = 0; shard < 6; ++shard) {
        for (unsigned pair = 0; pair < rows / 2; ++pair) {
            const mage_v2_axis64_t item = rx.read();
            const float got0 = v2_float_from_bits(item.data.range(31, 0));
            const float got1 = v2_float_from_bits(item.data.range(63, 32));
            if (got0 != expected[shard][2 * pair] || got1 != expected[shard][2 * pair + 1]) {
                std::cerr << "value failure bits=" << bits << " shard=" << shard
                          << " pair=" << pair << " got=" << got0 << "," << got1
                          << " expected=" << expected[shard][2 * pair] << ","
                          << expected[shard][2 * pair + 1] << std::endl;
                return 1;
            }
            const bool expected_last = shard == 5 && pair == rows / 2 - 1;
            if ((bool)item.last != expected_last) return 1;
        }
    }
    return 0;
}

int main() {
    for (unsigned bits = 2; bits <= 4; ++bits) {
        if (v2_run_case(bits)) return 1;
    }
    std::cout << "MAGE_DECODE_SIXPORT_V2_CSIM_PASS bits=2,3,4" << std::endl;
    return 0;
}
