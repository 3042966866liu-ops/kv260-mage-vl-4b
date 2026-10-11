#include "../mage_prefill_m89d_t32_microtile/mage_prefill_m89d_t32_microtile.hpp"
#include <cstdlib>
#include <fstream>
#include <iostream>

void m89p_fourshard(hls::stream<m89_axis128_t>&, const ap_uint<128>*, const ap_uint<128>*,
                    const ap_uint<128>*, const ap_uint<128>*, hls::stream<m89_axis64_t>&,
                    unsigned, unsigned, unsigned, ap_uint<32>&, ap_uint<32>&,
                    ap_uint<32>&, ap_uint<32>&);

static unsigned read_u32(std::ifstream &in) {
  unsigned char b[4]; in.read(reinterpret_cast<char*>(b), 4);
  return unsigned(b[0]) | (unsigned(b[1]) << 8) | (unsigned(b[2]) << 16) | (unsigned(b[3]) << 24);
}

static ap_uint<128> read_word(std::ifstream &in) {
  unsigned char b[16]; in.read(reinterpret_cast<char*>(b), 16);
  ap_uint<128> word = 0;
  for (unsigned i = 0; i < 16; ++i) word.range(8*i+7, 8*i) = b[i];
  return word;
}

static int activation(unsigned descriptor, unsigned token, unsigned lane) {
  return int((descriptor * 17 + token * 7 + lane * 5 + 11) % 63) - 31;
}

static int code_at(const ap_uint<128> record[17], unsigned bits, unsigned row, unsigned lane) {
  unsigned pair = row >> 1;
  unsigned within = row & 1;
  if (bits == 2) {
    const ap_uint<128> &word = record[1 + pair * 2 + within];
    return int(word.range(2*lane+1, 2*lane));
  }
  const ap_uint<128> &word = record[1 + pair * 4 + within * 2 + (lane >= 32)];
  unsigned local = lane & 31;
  return int(word.range(4*local+3, 4*local));
}

static int golden(const ap_uint<128> record[17], unsigned bits, unsigned descriptor,
                  unsigned token, unsigned row) {
  ap_uint<16> tagged = record[0].range(16*row+15, 16*row);
  int half = 1 << (bits - 1);
  int qmin = tagged[15] ? -half + 1 : -half;
  int sum = 0;
  for (unsigned lane = 0; lane < 64; ++lane)
    sum += activation(descriptor, token, lane) * (qmin + code_at(record, bits, row, lane));
  return sum;
}

int main() {
  const char *path = std::getenv("M89Q_FIXTURE_PATH");
  if (!path) { std::cerr << "M89Q_FIXTURE_PATH missing\n"; return 1; }
  std::ifstream in(path, std::ios::binary);
  char magic[8]; in.read(magic, 8);
  if (!in || std::string(magic, 8) != "M89QREAL") return 2;
  unsigned count = read_u32(in), max_words = read_u32(in);
  if (count != 252 || max_words != 17) return 3;

  for (unsigned descriptor = 0; descriptor < count; ++descriptor) {
    unsigned char header[4]; in.read(reinterpret_cast<char*>(header), 4);
    unsigned bits = header[0], words = header[1];
    if ((bits != 2 && bits != 4) || words != 1 + 4*bits) return 4;
    ap_uint<128> record[4][17];
    for (unsigned shard = 0; shard < 4; ++shard)
      for (unsigned word = 0; word < 17; ++word) record[shard][word] = read_word(in);
    if (!in) return 5;

    hls::stream<m89_axis128_t> tx;
    hls::stream<m89_axis64_t> rx;
    for (unsigned token = 0; token < 32; ++token) {
      for (unsigned word = 0; word < 4; ++word) {
        m89_axis128_t item; item.data = 0; item.keep = -1; item.strb = -1;
        for (unsigned byte = 0; byte < 16; ++byte)
          item.data.range(8*byte+7, 8*byte) = ap_uint<8>(activation(descriptor, token, 16*word+byte));
        item.last = token == 31 && word == 3; tx.write(item);
      }
    }
    ap_uint<32> status, build, calls, macros;
    m89p_fourshard(tx, record[0], record[1], record[2], record[3], rx,
                   1, 8, bits, status, build, calls, macros);
    if (status != 0 || build != 0x4D383950U || calls != 1 || macros != 1024) return 6;
    for (unsigned token = 0; token < 32; ++token) {
      for (unsigned shard = 0; shard < 4; ++shard) {
        for (unsigned pair = 0; pair < 4; ++pair) {
          m89_axis64_t item = rx.read();
          int lo = int(ap_int<32>(item.data.range(31, 0)));
          int hi = int(ap_int<32>(item.data.range(63, 32)));
          if (lo != golden(record[shard], bits, descriptor, token, 2*pair) ||
              hi != golden(record[shard], bits, descriptor, token, 2*pair+1)) {
            std::cerr << "M89Q mismatch descriptor=" << descriptor << " token=" << token
                      << " shard=" << shard << " pair=" << pair << "\n";
            return 7;
          }
        }
      }
    }
    if (!rx.empty()) return 8;
  }
  std::cout << "M89Q_REAL_M56_ALL_252_W2W4_CSIM_PASS descriptors=" << count << "\n";
  return 0;
}
