#include "../mage_prefill_m89d_t32_microtile/mage_prefill_m89d_t32_microtile.hpp"
#include <hls_half.h>
#include <hls_math.h>
#include <cstdlib>
#include <fstream>
#include <iostream>

ap_uint<32> m89t_scale_chain(hls::stream<m89_axis128_t>&,
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
static int act(unsigned chain, unsigned group, unsigned token, unsigned lane) {
  return int((chain*19 + group*23 + token*7 + lane*5 + 11) % 63) - 31;
}
static int code(const ap_uint<128> *record, unsigned bits,
                unsigned row, unsigned lane) {
  unsigned pair = row >> 1, which = row & 1;
  if (bits == 2)
    return int(record[1 + pair*2 + which].range(2*lane+1, 2*lane));
  unsigned z = lane & 31;
  return int(record[1 + pair*4 + which*2 + (lane >= 32)].range(4*z+3, 4*z));
}
static half golden(const ap_uint<128> *base, unsigned bits, unsigned groups,
                   unsigned chain, unsigned token, unsigned row) {
  unsigned words = 1 + 4*bits;
  half acc = (half)0.0f;
  for (unsigned g = 0; g < groups; ++g) {
    const ap_uint<128> *record = base + g*words;
    ap_uint<16> tag = record[0].range(16*row+15, 16*row);
    int h = 1 << (bits-1), q = tag[15] ? -h+1 : -h, dot = 0;
    for (unsigned lane = 0; lane < 64; ++lane)
      dot += act(chain, g, token, lane) * (q + code(record, bits, row, lane));
    half as = (half)(0.001953125f * (1 + ((chain + 3*g + token) % 11)));
    half ws = bh(tag & 0x7fff);
    half term = (half)((half)dot * as) * ws;
    acc = (half)(acc + term);
  }
  return acc;
}

int main() {
  const char *path = std::getenv("M89T_FIXTURE_PATH");
  if (!path) return 1;
  std::ifstream in(path, std::ios::binary);
  char magic[8]; in.read(magic, 8);
  if (!in || std::string(magic, 8) != "M89TCHN1") return 2;
  unsigned chains = u32(in), max_chain = u32(in), groups = u32(in);
  if (chains != 144 || max_chain != 10 || groups != 3) return 3;

  for (unsigned chain = 0; chain < chains; ++chain) {
    unsigned chain_id = u32(in), count = u32(in);
    if (chain_id != chain || count < 1 || count > 10) return 4;
    static ap_uint<128> weights[4][510];
    ap_uint<128> desc[10]; unsigned bits[10], offsets[10];
    unsigned cursor = 0;
    for (unsigned i = 0; i < count; ++i) {
      unsigned char header[4]; in.read((char*)header, 4);
      bits[i] = header[0]; unsigned words = header[1];
      if ((bits[i] != 2 && bits[i] != 4) || words != 1 + 4*bits[i] ||
          header[2] != groups) return 5;
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
    }
    if (!in) return 6;
    for (unsigned i = 1; i < count; ++i) if (bits[i] != bits[0]) return 11;

    hls::stream<m89_axis128_t> tx; hls::stream<m89_axis64_t> rx;
    for (unsigned i = 0; i < count; ++i) {
      m89_axis128_t item; item.data = desc[i]; item.keep = -1; item.strb = -1;
      item.last = 0; tx.write(item);
    }
    for (unsigned g = 0; g < groups; ++g)
      for (unsigned token = 0; token < 32; ++token)
        for (unsigned z = 0; z < 5; ++z) {
          m89_axis128_t item; item.data = 0; item.keep = -1; item.strb = -1;
          if (z < 4)
            for (unsigned b = 0; b < 16; ++b)
              item.data.range(8*b+7, 8*b) =
                  ap_uint<8>(act(chain, g, token, 16*z+b));
          else
            item.data.range(15, 0) = hb((half)(0.001953125f *
                (1 + ((chain + 3*g + token) % 11))));
          item.last = g+1 == groups && token == 31 && z == 4;
          tx.write(item);
        }

    ap_uint<32> config = groups | (bits[0] << 8) | (count << 16);
    ap_uint<32> result = m89t_scale_chain(tx, weights[0], weights[1],
                                         weights[2], weights[3], rx, config);
    if (result != 0x4D383954U) return 7;

    for (unsigned i = 0; i < count; ++i)
      for (unsigned token = 0; token < 32; ++token)
        for (unsigned shard = 0; shard < 4; ++shard)
          for (unsigned pair = 0; pair < 4; ++pair) {
            m89_axis64_t item = rx.read();
            const ap_uint<128> *base = &weights[shard][offsets[i]];
            if (item.data.range(15, 0) != hb(golden(base, bits[i], groups,
                                                    chain, token, 2*pair)) ||
                item.data.range(47, 32) != hb(golden(base, bits[i], groups,
                                                     chain, token, 2*pair+1))) {
              std::cerr << "M89T mismatch chain=" << chain << " descriptor=" << i
                        << " token=" << token << " shard=" << shard
                        << " pair=" << pair << "\n";
              return 8;
            }
            bool last = token == 31 && shard == 3 && pair == 3;
            if (bool(item.last) != last) return 9;
          }
    if (!rx.empty()) return 10;
  }
  std::cout << "M89T_REAL_M56_144_CHAINS_252_MODULES_3GROUP_SCALE_CSIM_PASS\n";
  return 0;
}
