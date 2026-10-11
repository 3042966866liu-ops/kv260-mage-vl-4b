#include "mage_prefill_m77_w2_wide.hpp"

#include <cstdint>
#include <iostream>
#include <random>

static void set_code(ap_uint<128> &word, unsigned lane, unsigned value) {
    word.range(2 * lane + 1, 2 * lane) = value;
}

static int qmin(bool orientation) { return orientation ? -1 : -2; }

int main() {
    const unsigned groups = 3;
    const unsigned rows = 16;
    const unsigned blocks = rows / 8;
    const unsigned words = groups * blocks * 9;
    static ap_uint<128> memory[M77_SHARDS][M77_MAX_GROUPS * (M77_MAX_ROWS_PER_SHARD / 8) * 9];
    static ap_int<8> activation[groups][M77_TOKEN_LANES][M77_GROUP_SIZE];
    static int expected[M77_TOKEN_LANES][M77_SHARDS][rows];
    hls::stream<m77_axis128_t> tx;
    hls::stream<m77_axis64_t> rx;
    std::mt19937 rng(0x4d373741U);
    std::uniform_int_distribution<int> act_dist(-31, 31);
    std::uniform_int_distribution<int> code_dist(0, 3);
    std::uniform_int_distribution<int> bit_dist(0, 1);
    for (unsigned g = 0; g < groups; ++g) {
        for (unsigned t = 0; t < M77_TOKEN_LANES; ++t) {
            for (unsigned lane = 0; lane < M77_GROUP_SIZE; ++lane) activation[g][t][lane] = act_dist(rng);
            for (unsigned word = 0; word < 4; ++word) {
                m77_axis128_t item;
                item.data = 0;
                for (unsigned byte = 0; byte < 16; ++byte) {
                    const unsigned lane = 16 * word + byte;
                    item.data.range(8 * byte + 7, 8 * byte) = (ap_uint<8>)activation[g][t][lane];
                }
                item.keep = -1;
                item.strb = -1;
                item.last = g + 1 == groups && t + 1 == M77_TOKEN_LANES && word == 3;
                tx.write(item);
            }
        }
    }
    for (unsigned t = 0; t < M77_TOKEN_LANES; ++t)
        for (unsigned shard = 0; shard < M77_SHARDS; ++shard)
            for (unsigned row = 0; row < rows; ++row) expected[t][shard][row] = 0;
    for (unsigned shard = 0; shard < M77_SHARDS; ++shard) {
        for (unsigned g = 0; g < groups; ++g) {
            for (unsigned block = 0; block < blocks; ++block) {
                const unsigned base = g * blocks * 9 + block * 9;
                ap_uint<128> scale = 0;
                bool orientation[8];
                for (unsigned row = 0; row < 8; ++row) {
                    orientation[row] = bit_dist(rng);
                    scale.range(16 * row + 15, 16 * row) = (ap_uint<16>)orientation[row] << 15;
                }
                memory[shard][base] = scale;
                for (unsigned pair = 0; pair < 4; ++pair) {
                    ap_uint<128> codes0 = 0;
                    ap_uint<128> codes1 = 0;
                    for (unsigned lane = 0; lane < M77_GROUP_SIZE; ++lane) {
                        const int c0 = code_dist(rng);
                        const int c1 = code_dist(rng);
                        set_code(codes0, lane, c0);
                        set_code(codes1, lane, c1);
                        for (unsigned t = 0; t < M77_TOKEN_LANES; ++t) {
                            expected[t][shard][8 * block + 2 * pair] += (int)activation[g][t][lane] * (qmin(orientation[2 * pair]) + c0);
                            expected[t][shard][8 * block + 2 * pair + 1] += (int)activation[g][t][lane] * (qmin(orientation[2 * pair + 1]) + c1);
                        }
                    }
                    memory[shard][base + 1 + 2 * pair] = codes0;
                    memory[shard][base + 2 + 2 * pair] = codes1;
                }
            }
        }
    }
    ap_uint<32> status = 0, build = 0, calls = 0, macros = 0;
    m77_w2_wide(tx, memory[0], memory[1], memory[2], memory[3], memory[4], memory[5], rx,
                groups, rows, status, build, calls, macros);
    if (status != 0 || build != M77_BUILD_ID || calls != 1 ||
        macros != groups * rows * M77_SHARDS * M77_TOKEN_LANES) {
        std::cerr << "counter failure" << std::endl;
        return 1;
    }
    for (unsigned t = 0; t < M77_TOKEN_LANES; ++t) {
        for (unsigned shard = 0; shard < M77_SHARDS; ++shard) {
            for (unsigned row = 0; row < rows; row += 2) {
                const m77_axis64_t item = rx.read();
                const int got0 = (int)(ap_int<32>)item.data.range(31, 0);
                const int got1 = (int)(ap_int<32>)item.data.range(63, 32);
                if (got0 != expected[t][shard][row] || got1 != expected[t][shard][row + 1]) {
                    std::cerr << "value mismatch" << std::endl;
                    return 1;
                }
                const bool expected_last = t + 1 == M77_TOKEN_LANES && shard + 1 == M77_SHARDS && row + 2 == rows;
                if ((bool)item.last != expected_last) return 1;
            }
        }
    }
    if (!rx.empty()) return 1;
    std::cout << "M77_W2_WIDE_CSIM_PASS tokens=" << M77_TOKEN_LANES << " groups=" << groups << " rows=" << rows << std::endl;
    return 0;
}
