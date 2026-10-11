// Vitis 2026.1 pure CSim does not link a separate design translation unit
// until a device-bound solution exists.  Include the exact candidate source
// here so this remains a license-independent numerical CSim gate.
#ifndef T64_TB_EXTERNAL_DUT
#include "mage_prefill_m230_t64_reuse.cpp"
#endif
#ifndef T64_TB_KERNEL
#define T64_TB_KERNEL m240_t64_kernel
#endif
#ifndef T64_TB_BUILD_ID
#define T64_TB_BUILD_ID 0x4D323430U
#endif
#ifndef T64_TB_LABEL
#define T64_TB_LABEL "M240"
#endif
#include <hls_half.h>
#include <hls_math.h>
#include <iostream>

static ap_uint<16> half_bits(half value) {
  fp_struct<half> payload(value);
  return payload.data();
}

static void put_weight_code(ap_uint<128> *record, unsigned bits,
                            unsigned row, unsigned lane, unsigned code) {
  unsigned pair = row >> 1;
  unsigned which = row & 1;
  unsigned base = 1 + pair * bits + which * (bits / 2);
  if (bits == 2)
    record[base].range(2 * lane + 1, 2 * lane) = code;
  else if (lane < 32)
    record[base].range(4 * lane + 3, 4 * lane) = code;
  else
    record[base + 1].range(4 * (lane - 32) + 3, 4 * (lane - 32)) = code;
}

static int run_case(unsigned bits) {
  const unsigned groups = 2;
  const unsigned rows = 8;
  const unsigned words = 1 + 4 * bits;
  static ap_uint<128> memory[4][256];
  static int weights[4][groups][rows][64];
  static int activations[2][groups][32][64];

  for (unsigned shard = 0; shard < 4; ++shard)
    for (unsigned index = 0; index < 256; ++index)
      memory[shard][index] = 0;

  const int qmin = -(1 << (bits - 1));
  const unsigned levels = 1U << bits;
  for (unsigned shard = 0; shard < 4; ++shard)
    for (unsigned group = 0; group < groups; ++group) {
      ap_uint<128> *record = &memory[shard][group * words];
      for (unsigned row = 0; row < rows; ++row)
        record[0].range(16 * row + 15, 16 * row) = half_bits((half)1.0f);
      for (unsigned row = 0; row < rows; ++row)
        for (unsigned lane = 0; lane < 64; ++lane) {
          unsigned code = (lane + 3 * row + 5 * group + 7 * shard) % levels;
          weights[shard][group][row][lane] = qmin + (int)code;
          put_weight_code(record, bits, row, lane, code);
        }
    }

  for (unsigned token_block = 0; token_block < 2; ++token_block)
    for (unsigned group = 0; group < groups; ++group)
      for (unsigned token = 0; token < 32; ++token)
        for (unsigned lane = 0; lane < 64; ++lane) {
          int magnitude = int((lane + 2 * token + 3 * group) % 15) - 7;
          activations[token_block][group][token][lane] =
              token_block == 0 ? magnitude : -magnitude;
        }

  hls::stream<m89_axis128_t> tx;
  hls::stream<m89_axis64_t> rx;
  m89_axis128_t descriptor;
  descriptor.data = 0;
  descriptor.data.range(41, 32) = rows;
  descriptor.data.range(44, 42) = bits;
  descriptor.keep = -1;
  descriptor.strb = -1;
  descriptor.last = 0;
  tx.write(descriptor);

  for (unsigned token_block = 0; token_block < 2; ++token_block)
    for (unsigned group = 0; group < groups; ++group)
      for (unsigned token = 0; token < 32; ++token)
        for (unsigned word_index = 0; word_index < 5; ++word_index) {
          m89_axis128_t item;
          item.data = 0;
          if (word_index < 4)
            for (unsigned lane = 0; lane < 16; ++lane) {
              int value = activations[token_block][group][token]
                                     [16 * word_index + lane];
              item.data.range(8 * lane + 7, 8 * lane) =
                  (ap_uint<8>)(ap_int<8>)value;
            }
          else
            item.data.range(15, 0) = half_bits((half)1.0f);
          item.keep = -1;
          item.strb = -1;
          item.last = token_block == 1 && group + 1 == groups &&
                      token == 31 && word_index == 4;
          tx.write(item);
        }

  ap_uint<32> config = groups | (bits << 8) | (1U << 16) | (2U << 20);
  ap_uint<32> status = T64_TB_KERNEL(
      tx, memory[0], memory[1], memory[2], memory[3], rx, config);
  if (status != T64_TB_BUILD_ID) {
    std::cerr << "M230 status mismatch bits=" << bits << " status=0x"
              << std::hex << status << std::dec << "\n";
    return 1;
  }

  unsigned words_seen = 0;
  for (unsigned token_block = 0; token_block < 2; ++token_block)
    for (unsigned token = 0; token < 32; ++token)
      for (unsigned shard = 0; shard < 4; ++shard)
        for (unsigned pair = 0; pair < 4; ++pair) {
          m89_axis64_t item = rx.read();
          for (unsigned which = 0; which < 2; ++which) {
            unsigned row = 2 * pair + which;
            int dot = 0;
            for (unsigned group = 0; group < groups; ++group)
              for (unsigned lane = 0; lane < 64; ++lane)
                dot += activations[token_block][group][token][lane] *
                       weights[shard][group][row][lane];
            ap_uint<16> expected = half_bits((half)(float)dot);
            ap_uint<16> observed = which == 0
                ? item.data.range(15, 0)
                : item.data.range(47, 32);
            if (observed != expected) {
              std::cerr << "M230 numerical mismatch bits=" << bits
                        << " block=" << token_block << " token=" << token
                        << " shard=" << shard << " row=" << row << "\n";
              return 2;
            }
          }
          bool expected_last = token_block == 1 && token == 31 &&
                               shard == 3 && pair == 3;
          if ((bool)item.last != expected_last)
            return 3;
          ++words_seen;
        }
  if (!rx.empty() || !tx.empty() || words_seen != 1024)
    return 4;
  std::cout << T64_TB_LABEL << "_T64_CASE_PASS bits=" << bits
            << " tokens=64 words=" << words_seen << "\n";
  return 0;
}

int main() {
  int rc = run_case(2);
  if (rc)
    return rc;
  rc = run_case(4);
  if (rc)
    return 10 + rc;
  std::cout << T64_TB_LABEL << "_T64_W2_W4_NUMERICAL_CSIM_PASS\n";
  return 0;
}
