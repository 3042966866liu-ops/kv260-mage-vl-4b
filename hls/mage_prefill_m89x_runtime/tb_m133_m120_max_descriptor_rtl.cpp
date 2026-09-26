#include "mage_prefill_m89x_runtime.hpp"

#include <iostream>

namespace {

constexpr unsigned kGroups = 1;
constexpr unsigned kBits = 4;
constexpr unsigned kDescriptorCount = 10;
constexpr unsigned kRowsPerShard = 8;
constexpr unsigned kBlocks = kRowsPerShard / 8;
constexpr unsigned kWordsPerGroupBlock = 1 + 4 * kBits;
constexpr unsigned kWordsPerDescriptor =
    kGroups * kBlocks * kWordsPerGroupBlock;
constexpr unsigned kWordsPerShard =
    kDescriptorCount * kWordsPerDescriptor;
constexpr unsigned kPairsPerShardPerDescriptor = kBlocks * 32 * 4;
constexpr unsigned kOutputWordsPerDescriptor =
    kPairsPerShardPerDescriptor * 4;
constexpr unsigned kExpectedOutputWords =
    kDescriptorCount * kOutputWordsPerDescriptor;

static_assert(kDescriptorCount == 10,
              "M120 maximum descriptor-count contract drifted");
static_assert(kWordsPerShard == 170,
              "M133 descriptor weight geometry drifted");
static_assert(kOutputWordsPerDescriptor == 512,
              "M133 per-descriptor word count drifted");
static_assert(kExpectedOutputWords == 5120,
              "M133 chain word count drifted");

}  // namespace

int main() {
  static ap_uint<128> weights[4][524288];
  for (unsigned shard = 0; shard < 4; ++shard) {
    for (unsigned descriptor = 0; descriptor < kDescriptorCount;
         ++descriptor) {
      const unsigned base = descriptor * kWordsPerDescriptor;
      weights[shard][base] = 0;
      for (unsigned word = 1; word < kWordsPerGroupBlock; ++word)
        weights[shard][base + word] =
            ap_uint<128>(0x0101010101010101ULL) |
            (ap_uint<128>(0x0101010101010101ULL) << 64);
    }
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

  for (unsigned token = 0; token < 32; ++token) {
    for (unsigned word = 0; word < 5; ++word) {
      m89_axis128_t item;
      item.data = word == 4 ? ap_uint<128>(0x3c00) : ap_uint<128>(0);
      item.keep = -1;
      item.strb = -1;
      item.last = token == 31 && word == 4;
      tx.write(item);
    }
  }

  const ap_uint<32> config =
      kGroups | (kBits << 8) | (kDescriptorCount << 16);
  const ap_uint<32> returned = m89x_runtime_kernel(
      tx, weights[0], weights[1], weights[2], weights[3], rx, config);
  if (returned != 0x4D395832U) {
    std::cerr << "M133_RETURN_FAIL observed=0x" << std::hex
              << returned.to_uint() << " expected=0x4d395832" << std::dec
              << "\n";
    return 1;
  }

  unsigned tlast_count = 0;
  for (unsigned index = 0; index < kExpectedOutputWords; ++index) {
    const m89_axis64_t item = rx.read();
    const bool expected_last = index + 1 == kExpectedOutputWords;
    if (item.data != 0 || item.keep != ap_uint<8>(0xff) ||
        item.strb != ap_uint<8>(0xff)) {
      std::cerr << "M133_OUTPUT_PAYLOAD_FAIL index=" << index << "\n";
      return 2;
    }
    if (bool(item.last) != expected_last) {
      std::cerr << "M133_TLAST_FAIL index=" << index
                << " observed=" << bool(item.last)
                << " expected=" << expected_last << "\n";
      return 3;
    }
    if (item.last) ++tlast_count;
  }
  if (!rx.empty()) {
    std::cerr << "M133_EXTRA_OUTPUT_FAIL\n";
    return 4;
  }
  if (!tx.empty()) {
    std::cerr << "M133_UNCONSUMED_INPUT_FAIL\n";
    return 5;
  }
  if (tlast_count != 1) {
    std::cerr << "M133_TLAST_COUNT_FAIL observed=" << tlast_count << "\n";
    return 6;
  }

  std::cout << "M133_GEOMETRY groups=" << kGroups << " bits=" << kBits
            << " descriptors=" << kDescriptorCount
            << " rows_per_shard=" << kRowsPerShard
            << " words_per_shard=" << kWordsPerShard
            << " output_words_per_descriptor="
            << kOutputWordsPerDescriptor
            << " output_words64=" << kExpectedOutputWords << "\n";
  std::cout << "M133_RETURN_ID=0x" << std::hex << returned.to_uint()
            << std::dec << "\n";
  std::cout << "M133_M120_MAX_DESCRIPTOR_RTL_PASS\n";
  return 0;
}

