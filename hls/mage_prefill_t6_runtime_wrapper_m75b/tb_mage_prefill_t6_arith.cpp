#include "mage_prefill_t6_arith.hpp"

#include <cmath>
#include <cstdint>
#include <iostream>
#include <random>

#include <hls_half.h>
#include <hls_math.h>

static ap_uint<16> half_bits(half value) {
    fp_struct<half> encoded(value);
    return encoded.data();
}

static void set_code(ap_uint<512> &packed, unsigned row, unsigned lane, unsigned bits, unsigned code) {
    const unsigned base = row * MAGE_T6_GROUP_SIZE * bits + lane * bits;
    packed.range(base + bits - 1, base) = code;
}

static int run_case(unsigned bits) {
    std::mt19937 rng(0x4D473248U + bits);
    std::uniform_int_distribution<int> activation_dist(-100, 100);
    std::uniform_int_distribution<int> code_dist(0, (1 << bits) - 1);
    std::uniform_int_distribution<int> orientation_dist(0, 1);
    hls::stream<mage_t6_axis128_t> tx;
    hls::stream<mage_t6_axis64_t> rx;
    ap_int<8> activations[MAGE_T6_TOKENS][MAGE_T6_GROUP_SIZE];
    half activation_scales[MAGE_T6_TOKENS];
    for (unsigned token = 0; token < MAGE_T6_TOKENS; ++token) {
        ap_uint<512> packed = 0;
        for (unsigned lane = 0; lane < MAGE_T6_GROUP_SIZE; ++lane) {
            activations[token][lane] = activation_dist(rng);
            packed.range(8 * lane + 7, 8 * lane) = (ap_uint<8>)activations[token][lane];
        }
        activation_scales[token] = (half)(0.003f * (token + 1));
        for (unsigned word = 0; word < 5; ++word) {
            mage_t6_axis128_t item;
            item.data = word < 4 ? packed.range(128 * word + 127, 128 * word) : (ap_uint<128>)half_bits(activation_scales[token]);
            item.keep = -1;
            item.strb = -1;
            item.last = token == MAGE_T6_TOKENS - 1 && word == 4;
            tx.write(item);
        }
    }

    ap_uint<128> memories[MAGE_T6_SHARDS][5];
    ap_int<5> signed_weights[MAGE_T6_SHARDS][2][MAGE_T6_GROUP_SIZE];
    half weight_scales[MAGE_T6_SHARDS][2];
    for (unsigned shard = 0; shard < MAGE_T6_SHARDS; ++shard) {
        const bool orientation0 = orientation_dist(rng);
        const bool orientation1 = orientation_dist(rng);
        weight_scales[shard][0] = (half)(0.01f + 0.001f * shard);
        weight_scales[shard][1] = (half)(0.02f + 0.001f * shard);
        ap_uint<128> tagged = 0;
        tagged.range(15, 0) = half_bits(weight_scales[shard][0]) | ((ap_uint<16>)orientation0 << 15);
        tagged.range(31, 16) = half_bits(weight_scales[shard][1]) | ((ap_uint<16>)orientation1 << 15);
        memories[shard][0] = tagged;
        ap_uint<512> codes = 0;
        const int qmin0 = -(1 << (bits - 1)) + (orientation0 ? 1 : 0);
        const int qmin1 = -(1 << (bits - 1)) + (orientation1 ? 1 : 0);
        for (unsigned lane = 0; lane < MAGE_T6_GROUP_SIZE; ++lane) {
            const unsigned code0 = code_dist(rng);
            const unsigned code1 = code_dist(rng);
            set_code(codes, 0, lane, bits, code0);
            set_code(codes, 1, lane, bits, code1);
            signed_weights[shard][0][lane] = (ap_int<5>)(qmin0 + (int)code0);
            signed_weights[shard][1][lane] = (ap_int<5>)(qmin1 + (int)code1);
        }
        for (unsigned word = 0; word < 4; ++word) {
            memories[shard][1 + word] = word < bits ? codes.range(128 * word + 127, 128 * word) : (ap_uint<128>)0;
        }
    }

    ap_uint<32> status = 0;
    ap_uint<32> build = 0;
    ap_uint<32> calls = 0;
    ap_uint<32> macros = 0;
    m75b_t6rt(
        tx, memories[0], memories[1], memories[2], memories[3], memories[4], memories[5],
        rx, 1, 2, bits, status, build, calls, macros);
    const unsigned invocation = bits - 1;
    if (status != 0 || build != MAGE_T6_BUILD_ID || calls != invocation ||
        macros != invocation * MAGE_T6_TOKENS * MAGE_T6_SHARDS * 2 * MAGE_T6_GROUP_SIZE) {
        std::cerr << "counter/status failure bits=" << bits << std::endl;
        return 1;
    }
    for (unsigned token = 0; token < MAGE_T6_TOKENS; ++token) {
        for (unsigned shard = 0; shard < MAGE_T6_SHARDS; ++shard) {
            const mage_t6_axis64_t item = rx.read();
            for (unsigned row = 0; row < 2; ++row) {
                int dot = 0;
                for (unsigned lane = 0; lane < MAGE_T6_GROUP_SIZE; ++lane) {
                    dot += (int)activations[token][lane] * (int)signed_weights[shard][row][lane];
                }
                const half scaled = (half)dot * activation_scales[token];
                const half expected = scaled * weight_scales[shard][row];
                const ap_uint<16> actual_bits = item.data.range(32 * row + 15, 32 * row);
                if (actual_bits != half_bits(expected)) {
                    std::cerr << "value failure bits=" << bits << " token=" << token
                              << " shard=" << shard << " row=" << row
                              << " actual=" << (unsigned)actual_bits
                              << " expected=" << (unsigned)half_bits(expected) << std::endl;
                    return 1;
                }
            }
            const bool expected_last = token == MAGE_T6_TOKENS - 1 && shard == MAGE_T6_SHARDS - 1;
            if ((bool)item.last != expected_last) {
                std::cerr << "TLAST failure" << std::endl;
                return 1;
            }
        }
    }
    if (!rx.empty()) return 1;
    return 0;
}

int main() {
    for (unsigned bits = 2; bits <= 4; ++bits) {
        if (run_case(bits)) return 1;
    }
    std::cout << "MAGE_PREFILL_T6_RUNTIME_WRAPPER_CSIM_PASS bits=2,3,4 input_groups=1 rows_per_shard=2 tokens=6 shards=6" << std::endl;
    return 0;
}
