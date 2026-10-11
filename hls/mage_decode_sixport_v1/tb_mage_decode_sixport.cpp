#include "mage_decode_sixport.hpp"

#include <hls_half.h>
#include <hls_math.h>

#include <cmath>
#include <iostream>
#include <vector>

static ap_uint<16> half_bits(half value) {
    fp_struct<half> encoded(value);
    return encoded.data();
}

static float float_from_bits(ap_uint<32> bits) {
    fp_struct<float> value(bits);
    return value.to_float();
}

static int signed_weight(unsigned shard, unsigned row, unsigned group, unsigned index, int qmin, int qmax) {
    const unsigned span = qmax - qmin + 1;
    return qmin + ((shard * 17 + row * 11 + group * 7 + index * 3) % span);
}

static int run_case(unsigned bits) {
    const unsigned groups = 2;
    const unsigned rows = 8;
    const unsigned code_words = groups * (rows / 2) * bits;
    const unsigned scale_base = code_words;
    const unsigned total_words = scale_base + groups * (rows / 8);
    std::vector<ap_uint<128> > memory[6];
    float expected[6][rows] = {};
    hls::stream<mage_axis128_t> activation_tx;
    hls::stream<mage_axis64_t> rx;

    int activations[groups][MAGE_GROUP_SIZE];
    for (unsigned group = 0; group < groups; ++group) {
        for (unsigned word = 0; word < 4; ++word) {
            mage_axis128_t item;
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
        mage_axis128_t metadata;
        metadata.data = half_bits((half)1.0f);
        metadata.keep = -1;
        metadata.strb = -1;
        metadata.last = group == groups - 1;
        activation_tx.write(metadata);
    }

    for (unsigned shard = 0; shard < 6; ++shard) {
        memory[shard].resize(total_words);
        for (unsigned group = 0; group < groups; ++group) {
            ap_uint<128> scale_word = 0;
            for (unsigned row = 0; row < rows; ++row) {
                const bool orientation = ((shard + row + group) & 1U) != 0;
                ap_uint<16> tagged = half_bits((half)1.0f);
                tagged[15] = orientation;
                scale_word.range(16 * row + 15, 16 * row) = tagged;
            }
            memory[shard][scale_base + group] = scale_word;
            for (unsigned pair = 0; pair < rows / 2; ++pair) {
                ap_uint<512> packed = 0;
                for (unsigned in_pair = 0; in_pair < 2; ++in_pair) {
                    const unsigned row = 2 * pair + in_pair;
                    const bool orientation = ((shard + row + group) & 1U) != 0;
                    const int half_range = 1 << (bits - 1);
                    const int qmin = orientation ? -half_range + 1 : -half_range;
                    const int qmax = orientation ? half_range : half_range - 1;
                    for (unsigned index = 0; index < MAGE_GROUP_SIZE; ++index) {
                        const int weight = signed_weight(shard, row, group, index, qmin, qmax);
                        const unsigned code = weight - qmin;
                        const unsigned bit_offset = in_pair * MAGE_GROUP_SIZE * bits + index * bits;
                        if (bits == 2) packed.range(bit_offset + 1, bit_offset) = code;
                        else if (bits == 3) packed.range(bit_offset + 2, bit_offset) = code;
                        else packed.range(bit_offset + 3, bit_offset) = code;
                        expected[shard][row] += (float)(weight * activations[group][index]);
                    }
                }
                const unsigned base = (group * (rows / 2) + pair) * bits;
                for (unsigned word = 0; word < bits; ++word) {
                    memory[shard][base + word] = packed.range(128 * word + 127, 128 * word);
                }
            }
        }
    }

    ap_uint<32> status = 0;
    ap_uint<32> build_id = 0;
    ap_uint<32> call_count = 0;
    ap_uint<32> macros = 0;
    mage_decode_sixport(
        activation_tx,
        memory[0].data(), memory[1].data(), memory[2].data(),
        memory[3].data(), memory[4].data(), memory[5].data(),
        rx, groups, rows, bits, scale_base,
        status, build_id, call_count, macros);
    const unsigned expected_calls = bits - 1;
    const unsigned expected_macros = expected_calls * groups * rows * 6;
    if (status != 0 || build_id != MAGE_SIXPORT_BUILD_ID ||
        call_count != expected_calls || macros != expected_macros) {
        std::cerr << "control failure bits=" << bits << " status=" << status
                  << " build=" << std::hex << build_id << std::dec
                  << " calls=" << call_count << " macros=" << macros << std::endl;
        return 1;
    }
    for (unsigned shard = 0; shard < 6; ++shard) {
        for (unsigned pair = 0; pair < rows / 2; ++pair) {
            const mage_axis64_t item = rx.read();
            const float got0 = float_from_bits(item.data.range(31, 0));
            const float got1 = float_from_bits(item.data.range(63, 32));
            if (got0 != expected[shard][2 * pair] || got1 != expected[shard][2 * pair + 1]) {
                std::cerr << "value failure bits=" << bits << " shard=" << shard
                          << " pair=" << pair << " got=" << got0 << "," << got1
                          << " expected=" << expected[shard][2 * pair] << ","
                          << expected[shard][2 * pair + 1] << std::endl;
                return 1;
            }
            const bool expected_last = shard == 5 && pair == rows / 2 - 1;
            if ((bool)item.last != expected_last) {
                std::cerr << "TLAST failure bits=" << bits << std::endl;
                return 1;
            }
        }
    }
    return 0;
}

int main() {
    for (unsigned bits = 2; bits <= 4; ++bits) {
        if (run_case(bits)) return 1;
    }
    std::cout << "MAGE_DECODE_SIXPORT_CSIM_PASS bits=2,3,4" << std::endl;
    return 0;
}
