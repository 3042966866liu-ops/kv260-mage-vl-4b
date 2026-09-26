#include "mage_prefill_m89x_runtime.hpp"
#include <hls_half.h>
#include <hls_math.h>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <string>

static const unsigned MAX_WORDS = 17;

static unsigned u32(std::ifstream &in) {
  unsigned char b[4];
  in.read((char *)b, 4);
  return unsigned(b[0]) | (unsigned(b[1]) << 8) |
         (unsigned(b[2]) << 16) | (unsigned(b[3]) << 24);
}

static ap_uint<128> word(std::ifstream &in) {
  unsigned char b[16];
  in.read((char *)b, 16);
  ap_uint<128> value = 0;
  for (unsigned i = 0; i < 16; ++i)
    value.range(8 * i + 7, 8 * i) = b[i];
  return value;
}

static ap_uint<16> half_bits(half value) {
  fp_struct<half> payload(value);
  return payload.data();
}

static half bits_half(ap_uint<16> bits) {
  fp_struct<half> payload(bits);
  return payload.to_half();
}

static float scale_float(ap_uint<16> bits) {
  ap_uint<5> exponent = bits.range(14, 10);
  ap_uint<10> mantissa = bits.range(9, 0);
  if (exponent == 0) {
    float value = (float)(unsigned)mantissa * 5.9604644775390625e-8f;
    return bits[15] ? -value : value;
  }
  return (float)bits_half(bits);
}

static int weight_code(const ap_uint<128> *record, unsigned bits,
                       unsigned row, unsigned lane) {
  unsigned pair = row >> 1;
  unsigned which = row & 1;
  if (bits == 2)
    return int(record[1 + pair * 2 + which].range(2 * lane + 1, 2 * lane));
  unsigned index = lane & 31;
  return int(record[1 + pair * 4 + which * 2 + (lane >= 32)]
                 .range(4 * index + 3, 4 * index));
}

static int activation_code(const ap_uint<128> values[5], unsigned lane) {
  ap_uint<8> raw = values[lane >> 4].range(8 * (lane & 15) + 7,
                                                8 * (lane & 15));
  return raw[7] ? int(raw) - 256 : int(raw);
}

static half independent_golden(const ap_uint<128> *base, unsigned bits,
                               unsigned groups,
                               const ap_uint<128> activation[152][32][5],
                               unsigned token, unsigned row) {
  const unsigned words = 1 + 4 * bits;
  float accumulator = 0.0f;
  for (unsigned group = 0; group < groups; ++group) {
    const ap_uint<128> *record = base + group * words;
    ap_uint<16> tag = record[0].range(16 * row + 15, 16 * row);
    int half_range = 1 << (bits - 1);
    int zero = tag[15] ? -half_range + 1 : -half_range;
    int dot = 0;
    for (unsigned lane = 0; lane < 64; ++lane)
      dot += activation_code(activation[group][token], lane) *
             (zero + weight_code(record, bits, row, lane));
    ap_uint<16> activation_scale_bits =
        activation[group][token][4].range(15, 0);
    float activation_scale = scale_float(activation_scale_bits);
    float weight_scale = scale_float(tag & 0x7fff);
    accumulator += (float)dot * activation_scale * weight_scale;
  }
  return (half)accumulator;
}

int main() {
  const char *path = std::getenv("M128_FIXTURE_PATH");
  if (!path)
    return 1;
  std::ifstream in(path, std::ios::binary);
  char magic[8];
  in.read(magic, 8);
  if (!in || std::string(magic, 8) != "M128CSM1")
    return 2;
  unsigned chains = u32(in), max_chain = u32(in), tokens = u32(in);
  unsigned valid_tokens = u32(in);
  if (chains != 7 || max_chain != 10 || tokens != 32 || valid_tokens != 30)
    return 3;

  unsigned total_output_words = 0;
  for (unsigned ordinal = 0; ordinal < chains; ++ordinal) {
    unsigned chain_id = u32(in), layer = u32(in), family = u32(in);
    unsigned count = u32(in), groups = u32(in), chain_bits = u32(in);
    if (chain_id != ordinal || (layer >= 36 && layer != 0xffffffffU) ||
        family > 6 || count < 1 || count > 10 || groups < 1 ||
        groups > 152 || (chain_bits != 2 && chain_bits != 4))
      return 4;

    static ap_uint<128> weights[4][8192];
    static ap_uint<128> activation[152][32][5];
    ap_uint<128> descriptors[10];
    unsigned bits[10], offsets[10];
    unsigned cursor = 0;
    for (unsigned descriptor_index = 0; descriptor_index < count;
         ++descriptor_index) {
      unsigned char header[8];
      in.read((char *)header, 8);
      bits[descriptor_index] = header[0];
      unsigned words = header[1];
      unsigned header_groups = header[2];
      if (bits[descriptor_index] != chain_bits ||
          words != 1 + 4 * bits[descriptor_index] ||
          header_groups != groups)
        return 5;
      offsets[descriptor_index] = cursor;
      descriptors[descriptor_index] = 0;
      descriptors[descriptor_index].range(31, 0) = cursor;
      descriptors[descriptor_index].range(41, 32) = 8;
      descriptors[descriptor_index].range(44, 42) = bits[descriptor_index];
      for (unsigned shard = 0; shard < 4; ++shard)
        for (unsigned group = 0; group < groups; ++group)
          for (unsigned index = 0; index < MAX_WORDS; ++index) {
            ap_uint<128> value = word(in);
            if (index < words)
              weights[shard][cursor + group * words + index] = value;
          }
      cursor += groups * words;
      if (cursor > 8192)
        return 6;
    }
    for (unsigned group = 0; group < groups; ++group)
      for (unsigned token = 0; token < 32; ++token)
        for (unsigned index = 0; index < 5; ++index)
          activation[group][token][index] = word(in);
    if (!in)
      return 7;

    hls::stream<m89_axis128_t> tx;
    hls::stream<m89_axis64_t> rx;
    for (unsigned descriptor_index = 0; descriptor_index < count;
         ++descriptor_index) {
      m89_axis128_t item;
      item.data = descriptors[descriptor_index];
      item.keep = -1;
      item.strb = -1;
      item.last = 0;
      tx.write(item);
    }
    for (unsigned group = 0; group < groups; ++group)
      for (unsigned token = 0; token < 32; ++token)
        for (unsigned index = 0; index < 5; ++index) {
          m89_axis128_t item;
          item.data = activation[group][token][index];
          item.keep = -1;
          item.strb = -1;
          item.last = group + 1 == groups && token == 31 && index == 4;
          tx.write(item);
        }

    ap_uint<32> config = groups | (chain_bits << 8) | (count << 16);
    ap_uint<32> status = m89x_runtime_kernel(
        tx, weights[0], weights[1], weights[2], weights[3], rx, config);
    if (status != 0x4D395832U) {
      std::cerr << "M128 status mismatch chain=" << ordinal << " status=0x"
                << std::hex << status << std::dec << "\n";
      return 8;
    }

    for (unsigned descriptor_index = 0; descriptor_index < count;
         ++descriptor_index)
      for (unsigned token = 0; token < 32; ++token)
        for (unsigned shard = 0; shard < 4; ++shard)
          for (unsigned pair = 0; pair < 4; ++pair) {
            m89_axis64_t item = rx.read();
            const ap_uint<128> *base =
                &weights[shard][offsets[descriptor_index]];
            ap_uint<16> expected0 = half_bits(independent_golden(
                base, bits[descriptor_index], groups, activation, token,
                2 * pair));
            ap_uint<16> expected1 = half_bits(independent_golden(
                base, bits[descriptor_index], groups, activation, token,
                2 * pair + 1));
            if (item.data.range(15, 0) != expected0 ||
                item.data.range(47, 32) != expected1) {
              std::cerr << "M128 numerical mismatch chain=" << ordinal
                        << " descriptor=" << descriptor_index
                        << " token=" << token << " shard=" << shard
                        << " pair=" << pair << "\n";
              return 9;
            }
            bool expected_last = descriptor_index + 1 == count &&
                                 token == 31 && shard == 3 && pair == 3;
            if (bool(item.last) != expected_last)
              return 10;
            ++total_output_words;
          }
    if (!rx.empty() || !tx.empty())
      return 11;
    std::cout << "M128_CHAIN_PASS ordinal=" << ordinal << " layer=" << layer
              << " family=" << family << " bits=" << chain_bits
              << " groups=" << groups << " descriptors=" << count << "\n";
  }
  if (!in || in.peek() != std::char_traits<char>::eof())
    return 12;
  std::cout << "M128_OUTPUT_WORDS=" << total_output_words << "\n";
  std::cout << "M128_M120_REAL_RECORD_NUMERICAL_CSIM_PASS\n";
  return 0;
}
