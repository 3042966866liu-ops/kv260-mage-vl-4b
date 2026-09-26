#include "../mage_prefill_m89d_t32_microtile/mage_prefill_m89d_t32_microtile.hpp"
#include <hls_half.h>
#include <hls_math.h>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <string>

#ifndef M89V_EXPECTED_CHAINS
#define M89V_EXPECTED_CHAINS 8
#endif
#ifndef M89V_FIXTURE_MAGIC
#define M89V_FIXTURE_MAGIC "M89VALL1"
#endif
#ifndef M89V_PASS_MARKER
#define M89V_PASS_MARKER "M89V_REAL_HIDDEN_ALLGROUPS_W2W4_4FAMILY_CSIM_PASS"
#endif
#ifndef M89V_TOP
#define M89V_TOP m89v_fullgroup_chain
#endif
#ifndef M89V_COALESCED_TLAST
#define M89V_COALESCED_TLAST 0
#endif
#ifndef M89V_EXPECTED_STATUS
#define M89V_EXPECTED_STATUS 0x4D383954U
#endif

ap_uint<32> M89V_TOP(hls::stream<m89_axis128_t>&,
                      const ap_uint<128>*, const ap_uint<128>*,
                      const ap_uint<128>*, const ap_uint<128>*,
                      hls::stream<m89_axis64_t>&, ap_uint<32>);

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
static int code(const ap_uint<128> *record, unsigned bits,
                unsigned row, unsigned lane) {
  unsigned pair = row >> 1, which = row & 1;
  if (bits == 2)
    return int(record[1 + pair*2 + which].range(2*lane+1, 2*lane));
  unsigned z = lane & 31;
  return int(record[1 + pair*4 + which*2 + (lane >= 32)].range(4*z+3, 4*z));
}
static int activation(const ap_uint<128> values[5], unsigned lane) {
  ap_uint<8> raw = values[lane >> 4].range(8*(lane & 15)+7, 8*(lane & 15));
  return raw[7] ? int(raw) - 256 : int(raw);
}
static half golden(const ap_uint<128> *base, unsigned bits, unsigned groups,
                   const ap_uint<128> act[152][32][5],
                   unsigned token, unsigned row) {
  unsigned words = 1 + 4*bits;
  half acc = (half)0.0f;
  for (unsigned g = 0; g < groups; ++g) {
    const ap_uint<128> *record = base + g*words;
    ap_uint<16> tag = record[0].range(16*row+15, 16*row);
    int h = 1 << (bits-1), q = tag[15] ? -h+1 : -h, dot = 0;
    for (unsigned lane = 0; lane < 64; ++lane)
      dot += activation(act[g][token], lane) *
             (q + code(record, bits, row, lane));
    half as = bh(act[g][token][4].range(15, 0));
    half ws = bh(tag & 0x7fff);
    half term = (half)((half)dot * as) * ws;
    acc = (half)(acc + term);
  }
  return acc;
}

int main() {
  const char *path = std::getenv("M89V_FIXTURE_PATH");
  if (!path) return 1;
  std::ifstream in(path, std::ios::binary);
  char magic[8]; in.read(magic, 8);
  if (!in || std::string(magic, 8) != M89V_FIXTURE_MAGIC) return 2;
  unsigned chains = u32(in), max_chain = u32(in), tokens = u32(in);
  unsigned valid_tokens = u32(in);
  if (chains != M89V_EXPECTED_CHAINS || max_chain != 10 || tokens != 32 ||
      valid_tokens != 30)
    return 3;

  for (unsigned ordinal = 0; ordinal < chains; ++ordinal) {
    unsigned chain_id = u32(in), layer = u32(in), family = u32(in);
    unsigned count = u32(in), groups = u32(in), chain_bits = u32(in);
    if (chain_id != ordinal || layer >= 36 || family >= 4 || count < 1 ||
        count > 10 || groups < 1 || groups > 152 ||
        (chain_bits != 2 && chain_bits != 4)) return 4;

    static ap_uint<128> weights[4][4096];
    static ap_uint<128> act[152][32][5];
    ap_uint<128> desc[10]; unsigned bits[10], offsets[10];
    unsigned cursor = 0;
    for (unsigned i = 0; i < count; ++i) {
      unsigned char header[8]; in.read((char*)header, 8);
      bits[i] = header[0]; unsigned words = header[1];
      unsigned header_groups = header[2];
      if (bits[i] != chain_bits || words != 1 + 4*bits[i] ||
          header_groups != groups) return 5;
      offsets[i] = cursor; desc[i] = 0;
      desc[i].range(31, 0) = cursor;
      desc[i].range(41, 32) = 8;
      desc[i].range(44, 42) = bits[i];
      for (unsigned shard = 0; shard < 4; ++shard)
        for (unsigned g = 0; g < groups; ++g)
          for (unsigned z = 0; z < 17; ++z) {
            ap_uint<128> value = word(in);
            if (z < words) weights[shard][cursor + g*words + z] = value;
          }
      cursor += groups*words;
      if (cursor > 4096) return 6;
    }
    for (unsigned g = 0; g < groups; ++g)
      for (unsigned token = 0; token < 32; ++token)
        for (unsigned z = 0; z < 5; ++z) act[g][token][z] = word(in);
    if (!in) return 7;

    hls::stream<m89_axis128_t> tx; hls::stream<m89_axis64_t> rx;
    for (unsigned i = 0; i < count; ++i) {
      m89_axis128_t item; item.data = desc[i]; item.keep = -1; item.strb = -1;
      item.last = 0; tx.write(item);
    }
    for (unsigned g = 0; g < groups; ++g)
      for (unsigned token = 0; token < 32; ++token)
        for (unsigned z = 0; z < 5; ++z) {
          m89_axis128_t item; item.data = act[g][token][z];
          item.keep = -1; item.strb = -1;
          item.last = g+1 == groups && token == 31 && z == 4;
          tx.write(item);
        }

    ap_uint<32> config = groups | (chain_bits << 8) | (count << 16);
    ap_uint<32> result = M89V_TOP(tx, weights[0], weights[1],
                                         weights[2], weights[3], rx, config);
    if (result != M89V_EXPECTED_STATUS) {
      std::cerr << "M89V status reject chain=" << chain_id << " result=0x"
                << std::hex << result << std::dec << "\n";
      return 8;
    }

    for (unsigned i = 0; i < count; ++i)
      for (unsigned token = 0; token < 32; ++token)
        for (unsigned shard = 0; shard < 4; ++shard)
          for (unsigned pair = 0; pair < 4; ++pair) {
            m89_axis64_t item = rx.read();
            const ap_uint<128> *base = &weights[shard][offsets[i]];
            ap_uint<16> expected0 = hb(golden(base, bits[i], groups, act,
                                               token, 2*pair));
            ap_uint<16> expected1 = hb(golden(base, bits[i], groups, act,
                                               token, 2*pair+1));
            if (item.data.range(15, 0) != expected0 ||
                item.data.range(47, 32) != expected1) {
              std::cerr << "M89V mismatch chain=" << chain_id
                        << " layer=" << layer << " family=" << family
                        << " descriptor=" << i << " token=" << token
                        << " shard=" << shard << " pair=" << pair << "\n";
              return 9;
            }
            bool last = token == 31 && shard == 3 && pair == 3 &&
                        (!M89V_COALESCED_TLAST || i + 1 == count);
            if (bool(item.last) != last) return 10;
          }
    if (!rx.empty()) return 11;
    std::cout << "M89V_CHAIN_PASS id=" << chain_id << " layer=" << layer
              << " family=" << family << " bits=" << chain_bits
              << " groups=" << groups << " descriptors=" << count << "\n";
  }
  std::cout << M89V_PASS_MARKER << "\n";
  return 0;
}
