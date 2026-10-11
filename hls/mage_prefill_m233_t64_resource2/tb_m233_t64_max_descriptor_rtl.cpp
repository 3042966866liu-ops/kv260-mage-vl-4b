#include "mage_prefill_m230_t64_reuse.hpp"

#include <iostream>

namespace {
constexpr unsigned kGroups = 1;
constexpr unsigned kBits = 4;
constexpr unsigned kDescriptorCount = 10;
constexpr unsigned kRowsPerShard = 8;
constexpr unsigned kWordsPerDescriptor = 1 + 4 * kBits;
constexpr unsigned kExpectedOutputWords = kDescriptorCount * 1024;
static_assert(kExpectedOutputWords == 10240, "M233 chain words drifted");
}

int main() {
  static ap_uint<128> weights[4][524288];
  for (unsigned shard = 0; shard < 4; ++shard)
    for (unsigned descriptor_index = 0;
         descriptor_index < kDescriptorCount; ++descriptor_index) {
      const unsigned base = descriptor_index * kWordsPerDescriptor;
      weights[shard][base] = 0;
      for (unsigned word = 1; word < kWordsPerDescriptor; ++word)
        weights[shard][base + word] =
            ap_uint<128>(0x0101010101010101ULL) |
            (ap_uint<128>(0x0101010101010101ULL) << 64);
    }

  hls::stream<m89_axis128_t> tx;
  hls::stream<m89_axis64_t> rx;
  for (unsigned descriptor_index = 0;
       descriptor_index < kDescriptorCount; ++descriptor_index) {
    m89_axis128_t descriptor;
    descriptor.data = 0;
    descriptor.data.range(31, 0) =
        descriptor_index * kWordsPerDescriptor;
    descriptor.data.range(41, 32) = kRowsPerShard;
    descriptor.data.range(44, 42) = kBits;
    descriptor.keep = -1;
    descriptor.strb = -1;
    descriptor.last = 0;
    tx.write(descriptor);
  }
  for (unsigned token_block = 0; token_block < 2; ++token_block)
    for (unsigned token = 0; token < 32; ++token)
      for (unsigned word = 0; word < 5; ++word) {
        m89_axis128_t item;
        item.data = word == 4 ? ap_uint<128>(0x3c00) : ap_uint<128>(0);
        item.keep = -1;
        item.strb = -1;
        item.last = token_block == 1 && token == 31 && word == 4;
        tx.write(item);
      }

  const ap_uint<32> config =
      kGroups | (kBits << 8) | (kDescriptorCount << 16) | (2U << 20);
  const ap_uint<32> returned = m233_t64_kernel(
      tx, weights[0], weights[1], weights[2], weights[3], rx, config);
  if (returned != 0x4D323333U) return 1;
  unsigned tlast_count = 0;
  for (unsigned index = 0; index < kExpectedOutputWords; ++index) {
    const m89_axis64_t item = rx.read();
    const bool expected_last = index + 1 == kExpectedOutputWords;
    if (item.data != 0 || item.keep != ap_uint<8>(0xff) ||
        item.strb != ap_uint<8>(0xff)) return 2;
    if (bool(item.last) != expected_last) return 3;
    if (item.last) ++tlast_count;
  }
  if (!rx.empty() || !tx.empty()) return 4;
  if (tlast_count != 1) return 5;
  std::cout << "M233_GEOMETRY descriptors=" << kDescriptorCount
            << " output_words64=" << kExpectedOutputWords << "\n";
  std::cout << "M233_RETURN_ID=0x" << std::hex << returned.to_uint()
            << std::dec << "\n";
  std::cout << "M233_T64_MAX_DESCRIPTOR_RTL_PASS\n";
  return 0;
}
