#include "mage_prefill_m89x_runtime.hpp"

#include <iostream>

namespace {

constexpr unsigned kGroups = 1;
constexpr unsigned kBits = 4;
constexpr unsigned kDescriptorCount = 1;
constexpr unsigned kRowsPerShard = 512;
constexpr unsigned kBlocks = kRowsPerShard / 8;
constexpr unsigned kWordsPerGroupBlock = 1 + 4 * kBits;
constexpr unsigned kWordsPerShard =
    kGroups * kBlocks * kWordsPerGroupBlock;
constexpr unsigned kPairsPerShard = kBlocks * 32 * 4;
constexpr unsigned kExpectedOutputWords = kPairsPerShard * 4;

static_assert(kWordsPerShard == 1088,
              "M132 W4 weight-window geometry drifted");
static_assert(kPairsPerShard == 8192,
              "M132 maximum result-FIFO occupancy drifted");
static_assert(kExpectedOutputWords == 32768,
              "M132 output-word contract drifted");

}  // namespace

int main() {
  static ap_uint<128> weights[4][524288];
  for (unsigned shard = 0; shard < 4; ++shard) {
    for (unsigned block = 0; block < kBlocks; ++block) {
      const unsigned base = block * kWordsPerGroupBlock;
      // Zero scale gives a bit-exact zero oracle while all rows, weight
      // addresses, decode loops, and the full 8192-pair result FIFO execute.
      weights[shard][base] = 0;
      for (unsigned word = 1; word < kWordsPerGroupBlock; ++word)
        weights[shard][base + word] =
            ap_uint<128>(0x0101010101010101ULL) |
            (ap_uint<128>(0x0101010101010101ULL) << 64);
    }
  }

  hls::stream<m89_axis128_t> tx;
  hls::stream<m89_axis64_t> rx;

  m89_axis128_t descriptor;
  descriptor.data = 0;
  descriptor.data.range(41, 32) = kRowsPerShard;
  descriptor.data.range(44, 42) = kBits;
  descriptor.keep = -1;
  descriptor.strb = -1;
  descriptor.last = 0;
  tx.write(descriptor);

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
    std::cerr << "M132_RETURN_FAIL observed=0x" << std::hex
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
      std::cerr << "M132_OUTPUT_PAYLOAD_FAIL index=" << index << "\n";
      return 2;
    }
    if (bool(item.last) != expected_last) {
      std::cerr << "M132_TLAST_FAIL index=" << index
                << " observed=" << bool(item.last)
                << " expected=" << expected_last << "\n";
      return 3;
    }
    if (item.last) ++tlast_count;
  }
  if (!rx.empty()) {
    std::cerr << "M132_EXTRA_OUTPUT_FAIL\n";
    return 4;
  }
  if (!tx.empty()) {
    std::cerr << "M132_UNCONSUMED_INPUT_FAIL\n";
    return 5;
  }
  if (tlast_count != 1) {
    std::cerr << "M132_TLAST_COUNT_FAIL observed=" << tlast_count << "\n";
    return 6;
  }

  std::cout << "M132_GEOMETRY groups=" << kGroups << " bits=" << kBits
            << " descriptors=" << kDescriptorCount
            << " rows_per_shard=" << kRowsPerShard
            << " words_per_shard=" << kWordsPerShard
            << " fifo_pairs_per_shard=" << kPairsPerShard
            << " output_words64=" << kExpectedOutputWords << "\n";
  std::cout << "M132_RETURN_ID=0x" << std::hex << returned.to_uint()
            << std::dec << "\n";
  std::cout << "M132_M120_MAX_FIFO_RANDOM_STALL_RTL_PASS\n";
  return 0;
}

