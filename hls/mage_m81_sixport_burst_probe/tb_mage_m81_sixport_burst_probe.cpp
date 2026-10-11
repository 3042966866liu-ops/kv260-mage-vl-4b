#include "mage_m81_sixport_burst_probe.hpp"

#include <iostream>

static ap_uint<64> expected_checksum(const ap_uint<128> *data, unsigned words) {
    ap_uint<64> value = 0;
    for (unsigned i = 0; i < words; ++i) value ^= data[i].range(63, 0) ^ data[i].range(127, 64);
    return value;
}

int main() {
    const unsigned words = 257;
    static ap_uint<128> memory[6][M81_MAX_WORDS];
    for (unsigned port = 0; port < 6; ++port) {
        for (unsigned word = 0; word < words; ++word) {
            memory[port][word].range(63, 0) = ((ap_uint<64>)port << 32) | word;
            memory[port][word].range(127, 64) = ((ap_uint<64>)(0x5a00 + port) << 32) | (3 * word + 1);
        }
    }
    ap_uint<64> got[6];
    ap_uint<32> status = 0, build = 0, completed = 0;
    mage_m81_sixport_burst_probe(memory[0], memory[1], memory[2], memory[3], memory[4], memory[5], words,
        got[0], got[1], got[2], got[3], got[4], got[5], status, build, completed);
    if (status != 0 || build != M81_BUILD_ID || completed != words) return 1;
    for (unsigned port = 0; port < 6; ++port) if (got[port] != expected_checksum(memory[port], words)) return 1;
    std::cout << "M81_SIXPORT_BURST_CSIM_PASS words=" << words << std::endl;
    return 0;
}
