#include "qwen25_mixed_gs_macro.hpp"

#include <hls_math.h>

#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <string>

static bool read_exact(const std::string &path, char *data, std::streamsize bytes) {
    std::ifstream stream(path.c_str(), std::ios::binary);
    if (!stream) return false;
    stream.read(data, bytes);
    return stream.gcount() == bytes;
}

static float bits_to_float(ap_uint<32> bits) {
    fp_struct<float> value(bits);
    return value.to_float();
}

int main() {
    static const unsigned TEST_GROUPS = 3;
    // Five blocks force a 3+2 tail and verify zero-padded internal lane 2.
    static const unsigned TEST_BLOCKS = 5;
    static const unsigned TEST_MACROS = TEST_GROUPS * TEST_BLOCKS;
    const char *root_env = std::getenv("QWEN_GS_DATA_DIR");
    if (!root_env) {
        std::cerr << "QWEN_GS_DATA_DIR is required" << std::endl;
        return 2;
    }
    const std::string root(root_env);
    unsigned char weight[QWEN_GS_WEIGHT_BYTES];
    unsigned char activation[QWEN_GS_ACTIVATION_BYTES];
    unsigned char legacy_packet[QWEN_GS_WEIGHT_BYTES + QWEN_GS_ACTIVATION_BYTES];
    float golden[QWEN_GS_OUTPUTS];
    if (!read_exact(root + "/macro_packet.bin", reinterpret_cast<char *>(legacy_packet),
                    sizeof(legacy_packet)) ||
        !read_exact(root + "/golden_output.bin", reinterpret_cast<char *>(golden),
                    sizeof(golden))) {
        std::cerr << "failed to load Qwen Mixed-GS golden data" << std::endl;
        return 2;
    }
    for (unsigned byte = 0; byte < QWEN_GS_WEIGHT_BYTES; ++byte)
        weight[byte] = legacy_packet[byte];
    for (unsigned byte = 0; byte < QWEN_GS_ACTIVATION_BYTES; ++byte)
        activation[byte] = legacy_packet[QWEN_GS_WEIGHT_BYTES + byte];

    hls::stream<qwen_axis128_t> tx("tx");
    hls::stream<qwen_axis64_t> rx("rx");
    for (unsigned group = 0; group < TEST_GROUPS; ++group) {
        for (unsigned word = 0; word < QWEN_GS_ACTIVATION_WORDS; ++word) {
            qwen_axis128_t item;
            item.data = 0;
            item.keep = -1;
            item.strb = -1;
            item.last = false;
            for (unsigned lane = 0; lane < 16; ++lane)
                item.data.range(8 * lane + 7, 8 * lane) =
                    activation[16 * word + lane];
            tx.write(item);
        }
        for (unsigned block = 0; block < TEST_BLOCKS; ++block) {
            for (unsigned word = 0; word < QWEN_GS_WEIGHT_WORDS; ++word) {
                qwen_axis128_t item;
                item.data = 0;
                item.keep = -1;
                item.strb = -1;
                item.last = group == TEST_GROUPS - 1 &&
                            block == TEST_BLOCKS - 1 &&
                            word == QWEN_GS_WEIGHT_WORDS - 1;
                for (unsigned lane = 0; lane < 16; ++lane)
                    item.data.range(8 * lane + 7, 8 * lane) =
                        weight[16 * word + lane];
                tx.write(item);
            }
        }
    }

    ap_uint<32> status = 0, build_id = 0, call_count = 0, processed_macros = 0;
    qwen25_mixed_gs_macro(tx, rx, TEST_GROUPS, TEST_BLOCKS,
                         status, build_id, call_count, processed_macros);
    float max_abs = 0.0f;
    float max_rel = 0.0f;
    bool last_ok = true;
    for (unsigned block = 0; block < TEST_BLOCKS; ++block) {
        unsigned output = 0;
        for (unsigned word = 0; word < QWEN_GS_RESULT_WORDS; ++word) {
            const qwen_axis64_t item = rx.read();
            last_ok &= (bool)item.last ==
                (block == TEST_BLOCKS - 1 && word == QWEN_GS_RESULT_WORDS - 1);
            for (unsigned lane = 0; lane < 2; ++lane, ++output) {
                const float actual = bits_to_float(
                    item.data.range(32 * lane + 31, 32 * lane));
                const float expected = TEST_GROUPS * golden[output];
                const float absolute = std::fabs(actual - expected);
                const float relative = absolute /
                    std::max(1.0e-6f, std::fabs(expected));
                max_abs = std::max(max_abs, absolute);
                max_rel = std::max(max_rel, relative);
            }
        }
    }

    const bool pass = status == 0 && build_id == QWEN_GS_BUILD_ID &&
        call_count == 1 && processed_macros == TEST_MACROS &&
        last_ok && max_abs <= 0.02f && max_rel <= 0.01f;
    std::cout << "QWEN_GS_BUILD_ID=0x" << std::hex << build_id.to_uint()
              << std::dec << " STATUS=" << status << " CALL_COUNT=" << call_count
              << " PROCESSED_MACROS=" << processed_macros << std::endl;
    std::cout << "QWEN_GS_MAX_ABS=" << max_abs << " MAX_REL=" << max_rel << std::endl;
    std::cout << "QWEN_GS_CSIM_RESULT=" << (pass ? "PASS" : "FAIL") << std::endl;
    return pass ? 0 : 1;
}
