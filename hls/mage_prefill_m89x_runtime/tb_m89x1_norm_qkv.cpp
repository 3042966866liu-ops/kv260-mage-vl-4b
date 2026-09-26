#include "mage_prefill_m89x_runtime.hpp"
#include <hls_half.h>
#include <utils/x_hls_utils.h>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <string>

static unsigned u32(std::ifstream &in) {
  unsigned char b[4]; in.read((char*)b, 4);
  return unsigned(b[0]) | (unsigned(b[1]) << 8) |
         (unsigned(b[2]) << 16) | (unsigned(b[3]) << 24);
}
static ap_uint<128> word(std::ifstream &in) {
  unsigned char b[16]; in.read((char*)b, 16); ap_uint<128> value = 0;
  for (unsigned i = 0; i < 16; ++i) value.range(8*i+7, 8*i) = b[i];
  return value;
}
static ap_uint<16> hb(half value) { fp_struct<half> x(value); return x.data(); }
static half bh(ap_uint<16> bits) { fp_struct<half> x(bits); return x.to_half(); }
static ap_uint<32> fb(float value) { fp_struct<float> x(value); return x.data(); }
static int code(const ap_uint<128> *record, unsigned row, unsigned lane) {
  unsigned pair = row >> 1, which = row & 1;
  return int(record[1 + pair*2 + which].range(2*lane+1, 2*lane));
}
static int activation(const ap_uint<128> values[5], unsigned lane) {
  ap_uint<8> raw = values[lane >> 4].range(8*(lane & 15)+7, 8*(lane & 15));
  return raw[7] ? int(raw) - 256 : int(raw);
}
static half golden(const ap_uint<128> *base, unsigned groups,
                   const ap_uint<128> act[40][32][5], unsigned token, unsigned row) {
  float acc = 0.0f;
  for (unsigned group = 0; group < groups; ++group) {
    const ap_uint<128> *record = base + group * 9;
    ap_uint<16> tag = record[0].range(16*row+15, 16*row);
    int q = tag[15] ? -1 : -2, dot = 0;
    for (unsigned lane = 0; lane < 64; ++lane)
      dot += activation(act[group][token], lane) * (q + code(record, row, lane));
    float as = m89x_scale_float(act[group][token][4].range(15, 0));
    float ws = m89x_scale_float(tag & 0x7fff);
    acc += (float)dot * as * ws;
  }
  return (half)acc;
}
static void write_first_lane_trace(const char *path, const ap_uint<128> *base,
                                   const ap_uint<128> act[40][32][5]) {
  if (!path || !*path) return;
  std::ofstream trace(path, std::ios::trunc);
  trace << "token,group,dot,activation_bits,weight_bits,mul1_float_bits,"
           "term_float_bits,acc_float_bits,acc_half_bits\n";
  for (unsigned token = 0; token < 2; ++token) {
    float acc = 0.0f;
    for (unsigned group = 0; group < 40; ++group) {
      const ap_uint<128> *record = base + group * 9;
      ap_uint<16> tag = record[0].range(15, 0);
      int q = tag[15] ? -1 : -2, dot = 0;
      for (unsigned lane = 0; lane < 64; ++lane)
        dot += activation(act[group][token], lane) * (q + code(record, 0, lane));
      float activation_scale = m89x_scale_float(act[group][token][4].range(15, 0));
      float weight_scale = m89x_scale_float(tag & 0x7fff);
      float mul1 = (float)dot * activation_scale;
      float term = mul1 * weight_scale;
      acc += term;
      trace << token << ',' << group << ',' << dot << ','
            << unsigned(hb((half)activation_scale)) << ','
            << unsigned(hb((half)weight_scale)) << ',' << unsigned(fb(mul1))
            << ',' << unsigned(fb(term)) << ',' << unsigned(fb(acc)) << ','
            << unsigned(hb((half)acc)) << '\n';
    }
  }
}
static void write_axis64(std::ofstream &out, ap_uint<16> low, ap_uint<16> high) {
  // Preserve the AXIS64 byte placement: FP16 low at bits [15:0], FP16 high at
  // [47:32], with the two unused byte pairs explicitly serialized as zero.
  unsigned char b[8] = {
      static_cast<unsigned char>(low.range(7, 0)),
      static_cast<unsigned char>(low.range(15, 8)), 0, 0,
      static_cast<unsigned char>(high.range(7, 0)),
      static_cast<unsigned char>(high.range(15, 8)), 0, 0};
  out.write((char*)b, 8);
}

int main() {
  const char *fixture_path = std::getenv("M89X1_CSIM_FIXTURE");
  const char *output_path = std::getenv("M89X1_CSIM_OUTPUT");
  if (!fixture_path || !output_path) return 1;
  std::ifstream in(fixture_path, std::ios::binary);
  char magic[7]; in.read(magic, 7);
  if (!in || std::string(magic, 7) != "M89X1NQ") return 2;
  if (u32(in) != 1 || u32(in) != 10 || u32(in) != 32 || u32(in) != 32) return 3;
  if (u32(in) != 0 || u32(in) != 0 || u32(in) != 0 || u32(in) != 4 ||
      u32(in) != 40 || u32(in) != 2) return 4;
  static ap_uint<128> weights[4][4096]; ap_uint<128> descriptor[4];
  unsigned offset[4], rows[4], cursor = 0;
  for (unsigned index = 0; index < 4; ++index) {
    unsigned char h[8]; in.read((char*)h, 8);
    if (h[0] != 2 || h[1] != 9 || h[2] != 40) return 5;
    rows[index] = 8;
    offset[index] = cursor; descriptor[index] = 0;
    descriptor[index].range(31, 0) = cursor;
    descriptor[index].range(41, 32) = rows[index]; descriptor[index].range(44, 42) = 2;
    for (unsigned shard = 0; shard < 4; ++shard)
      for (unsigned group = 0; group < 40; ++group)
        for (unsigned z = 0; z < 17; ++z) {
          ap_uint<128> value = word(in);
          if (z < 9) weights[shard][cursor + group*9 + z] = value;
        }
    cursor += 40 * 9;
  }
  ap_uint<128> activation_words[40][32][5];
  for (unsigned group = 0; group < 40; ++group)
    for (unsigned token = 0; token < 32; ++token)
      for (unsigned z = 0; z < 5; ++z) activation_words[group][token][z] = word(in);
  if (!in) return 6;
  write_first_lane_trace(std::getenv("M89X1_CSIM_TRACE"),
                         &weights[0][offset[0]], activation_words);
  if (std::getenv("M89X1_CSIM_LEGACY_HOST_SCALE")) {
    std::ofstream output(output_path, std::ios::binary | std::ios::trunc);
    if (!output) return 12;
    for (unsigned index = 0; index < 4; ++index) {
      hls::stream<m89_axis128_t> legacy_tx;
      hls::stream<m89_axis64_t> legacy_rx;
      for (unsigned group = 0; group < 40; ++group)
        for (unsigned token = 0; token < 32; ++token)
          for (unsigned z = 0; z < 5; ++z) {
            m89_axis128_t item;
            item.data = activation_words[group][token][z];
            item.keep = -1;
            item.strb = -1;
            item.last = group == 39 && token == 31 && z == 4;
            legacy_tx.write(item);
          }
      ap_uint<32> status = 0, build = 0, calls = 0, macros = 0;
      m89s_scaleaware_reference(legacy_tx, weights[0] + offset[index],
          weights[1] + offset[index], weights[2] + offset[index],
          weights[3] + offset[index], legacy_rx, 40, rows[index], 2,
          status, build, calls, macros);
      if (status != 0 || calls != 1 || macros != 40 * rows[index] * 4 * 32)
        return 13;
      for (unsigned block = 0; block < rows[index] / 8; ++block)
        for (unsigned token = 0; token < 32; ++token)
          for (unsigned shard = 0; shard < 4; ++shard)
            for (unsigned pair = 0; pair < 4; ++pair) {
              m89_axis64_t item = legacy_rx.read();
              bool expected_last = block + 1 == rows[index] / 8 &&
                                   token == 31 && shard == 3 && pair == 3;
              if (bool(item.last) != expected_last) return 14;
              write_axis64(output, item.data.range(15, 0),
                           item.data.range(47, 32));
            }
      if (!legacy_rx.empty()) return 15;
    }
    output.close();
    std::cout << "M89X1_HOST_POWER2_SCALE_LEGACY_CSIM_PASS\n";
    return 0;
  }
  hls::stream<m89_axis128_t> tx; hls::stream<m89_axis64_t> rx;
  for (unsigned index = 0; index < 4; ++index) { m89_axis128_t item; item.data = descriptor[index]; item.keep = -1; item.strb = -1; item.last = 0; tx.write(item); }
  for (unsigned group = 0; group < 40; ++group)
    for (unsigned token = 0; token < 32; ++token)
      for (unsigned z = 0; z < 5; ++z) { m89_axis128_t item; item.data = activation_words[group][token][z]; item.keep = -1; item.strb = -1; item.last = group == 39 && token == 31 && z == 4; tx.write(item); }
  if (m89x_runtime_kernel(tx, weights[0], weights[1], weights[2], weights[3], rx, 0x00040228U) != 0x4D395832U) return 7;
  std::ofstream output(output_path, std::ios::binary | std::ios::trunc);
  if (!output) return 8;
  for (unsigned index = 0; index < 4; ++index)
    for (unsigned block = 0; block < rows[index] / 8; ++block)
      for (unsigned token = 0; token < 32; ++token)
        for (unsigned shard = 0; shard < 4; ++shard)
          for (unsigned pair = 0; pair < 4; ++pair) {
            m89_axis64_t item = rx.read();
            ap_uint<16> low = item.data.range(15, 0), high = item.data.range(47, 32);
            const ap_uint<128> *base = &weights[shard][offset[index]];
            if (low != hb(golden(base, 40, activation_words, token, block*8 + pair*2)) ||
                high != hb(golden(base, 40, activation_words, token, block*8 + pair*2 + 1))) return 9;
            bool expected_last = index == 3 && block + 1 == rows[index] / 8 && token == 31 && shard == 3 && pair == 3;
            if (bool(item.last) != expected_last) return 10;
            write_axis64(output, low, high);
          }
  if (!rx.empty()) return 11;
  output.close();
  std::cout << "M89X1_NORM_QKV_HLS_SEMANTICS_CSIM_PASS\n";
  return 0;
}
