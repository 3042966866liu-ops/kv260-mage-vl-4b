#include "mage_prefill_m89x_runtime.hpp"

#include <iostream>

namespace {

constexpr unsigned kGroups = 40;
constexpr unsigned kBits = 4;
constexpr unsigned kDescriptorCount = 10;
constexpr unsigned kRowsPerShard = 512;
constexpr unsigned kBlocks = kRowsPerShard / 8;
constexpr unsigned kWordsPerGroupBlock = 1 + 4 * kBits;
constexpr unsigned kWordsPerDescriptor =
    kGroups * kBlocks * kWordsPerGroupBlock;
constexpr unsigned kWordsPerShard = kDescriptorCount * kWordsPerDescriptor;
constexpr unsigned kPairsPerShardPerDescriptor =
    kBlocks * 32 * 4;
constexpr unsigned kOutputWordsPerDescriptor =
    kPairsPerShardPerDescriptor * 4;
constexpr unsigned kExpectedOutputWords =
    kDescriptorCount * kOutputWordsPerDescriptor;

static_assert(kWordsPerShard == 435200,
              "M120 legal max-chain weight geometry drifted");
static_assert(kWordsPerShard <= 524288,
              "M120 legal max-chain exceeds the synthesized m_axi depth");
static_assert(kPairsPerShardPerDescriptor == 8192,
              "result FIFO occupancy contract drifted");
static_assert(kExpectedOutputWords == 327680,
              "M120 max-chain output word contract drifted");

}  // namespace

int main() {
  // The arrays intentionally match the synthesized interface depth.  Only the
  // legal M120 window [0, kWordsPerShard) is populated and read.
  static ap_uint<128> weights[4][524288];
  for (unsigned shard = 0; shard < 4; ++shard) {
    for (unsigned descriptor = 0; descriptor < kDescriptorCount;
         ++descriptor) {
      const unsigned descriptor_base = descriptor * kWordsPerDescriptor;
      for (unsigned group = 0; group < kGroups; ++group) {
        for (unsigned block = 0; block < kBlocks; ++block) {
          const unsigned base = descriptor_base +
                                (group * kBlocks + block) *
                                    kWordsPerGroupBlock;
          // A zero scale makes the expected output exactly zero while all
          // legal weight addresses, decode loops and result FIFOs are still
          // exercised at maximum occupancy.
          weights[shard][base] = 0;
          for (unsigned word = 1; word < kWordsPerGroupBlock; ++word)
            weights[shard][base + word] =
                ap_uint<128>(0x0101010101010101ULL) |
                (ap_uint<128>(0x0101010101010101ULL) << 64);
        }
      }
    }
  }

  hls::stream<m89_axis128_t> tx;
  hls::stream<m89_axis64_t> rx;

  for (unsigned descriptor = 0; descriptor < kDescriptorCount;
       ++descriptor) {
    m89_axis128_t item;
    item.data = 0;
    item.data.range(31, 0) = descriptor * kWordsPerDescriptor;
    item.data.range(41, 32) = kRowsPerShard;
    item.data.range(44, 42) = kBits;
    item.keep = -1;
    item.strb = -1;
    item.last = 0;
    tx.write(item);
  }

  // M89-X2 consumes four packed int8 activation words plus one FP16 scale
  // word for every token/group pair.  TLAST is legal only on the final word.
  for (unsigned group = 0; group < kGroups; ++group) {
    for (unsigned token = 0; token < 32; ++token) {
      for (unsigned word = 0; word < 5; ++word) {
        m89_axis128_t item;
        item.data = word == 4 ? ap_uint<128>(0x3c00) : ap_uint<128>(0);
        item.keep = -1;
        item.strb = -1;
        item.last = group + 1 == kGroups && token == 31 && word == 4;
        tx.write(item);
      }
    }
  }

  const ap_uint<32> config =
      kGroups | (kBits << 8) | (kDescriptorCount << 16);
  const ap_uint<32> returned = m89x_runtime_kernel(
      tx, weights[0], weights[1], weights[2], weights[3], rx, config);

  if (returned != 0x4D395832U) {
    std::cerr << "M131_RETURN_FAIL observed=0x" << std::hex
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
      std::cerr << "M131_OUTPUT_PAYLOAD_FAIL index=" << index << "\n";
      return 2;
    }
    if (bool(item.last) != expected_last) {
      std::cerr << "M131_TLAST_FAIL index=" << index
                << " observed=" << bool(item.last)
                << " expected=" << expected_last << "\n";
      return 3;
    }
    if (item.last) ++tlast_count;
  }
  if (!rx.empty()) {
    std::cerr << "M131_EXTRA_OUTPUT_FAIL\n";
    return 4;
  }
  if (!tx.empty()) {
    std::cerr << "M131_UNCONSUMED_INPUT_FAIL\n";
    return 5;
  }
  if (tlast_count != 1) {
    std::cerr << "M131_TLAST_COUNT_FAIL observed=" << tlast_count << "\n";
    return 6;
  }

  std::cout << "M131_GEOMETRY groups=" << kGroups << " bits=" << kBits
            << " descriptors=" << kDescriptorCount
            << " rows_per_shard=" << kRowsPerShard
            << " words_per_shard=" << kWordsPerShard
            << " fifo_pairs_per_shard_descriptor="
            << kPairsPerShardPerDescriptor
            << " output_words64=" << kExpectedOutputWords << "\n";
  std::cout << "M131_RETURN_ID=0x" << std::hex << returned.to_uint()
            << std::dec << "\n";
  std::cout << "M131_M120_MAX_TRAFFIC_RTL_CONTRACT_PASS\n";
  return 0;
}
