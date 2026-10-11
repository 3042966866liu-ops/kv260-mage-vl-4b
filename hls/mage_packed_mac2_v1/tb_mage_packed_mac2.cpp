#include "mage_packed_mac2.hpp"

#include <cstdlib>
#include <iostream>

int main() {
    unsigned long long cases = 0;
    for (int activation = -128; activation <= 127; ++activation) {
        for (int weight0 = -8; weight0 <= 7; ++weight0) {
            for (int weight1 = -8; weight1 <= 7; ++weight1) {
                ap_int<16> product0 = 0;
                ap_int<16> product1 = 0;
                ap_uint<32> build_id = 0;
                mage_packed_mac2(
                    (ap_int<8>)activation,
                    (ap_int<5>)weight0,
                    (ap_int<5>)weight1,
                    product0,
                    product1,
                    build_id);
                const int expected0 = activation * weight0;
                const int expected1 = activation * weight1;
                if ((int)product0 != expected0 || (int)product1 != expected1 ||
                    build_id != MAGE_PACKED_MAC2_BUILD_ID) {
                    std::cerr << "FAIL a=" << activation
                              << " w0=" << weight0 << " w1=" << weight1
                              << " got=" << (int)product0 << "," << (int)product1
                              << " expected=" << expected0 << "," << expected1
                              << std::endl;
                    return 1;
                }
                ++cases;
            }
        }
    }
    std::cout << "MAGE_PACKED_MAC2_CSIM_PASS cases=" << cases << std::endl;
    return 0;
}
