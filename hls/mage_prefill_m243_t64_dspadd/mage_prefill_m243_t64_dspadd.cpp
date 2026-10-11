// M243 is the final isolated T64 timing experiment.  It preserves M240's
// numerical contract, serial token schedule, and 64-token weight reuse.  Only
// the packed-dot reduction is changed: its final 8-to-1 additions are an
// explicit balanced tree mapped to registered DSP operators, directly
// targeting M240's routed CARRY8 critical path.
#define M89_MAX_GROUPS_VALUE 152
#include "mage_prefill_m243_t64_dspadd.hpp"
#define m89o_dot m243_legacy_dot_reference
#define m89s_scaleaware m243_scaleaware_reference
#include "../mage_prefill_m89s_scaleaware/mage_prefill_m89s_scaleaware.cpp"
#undef m89s_scaleaware
#undef m89o_dot
#undef M89_MAX_GROUPS_VALUE

static const unsigned M243_TOKEN_BLOCKS = 2;
static const unsigned M243_MAX_CHAIN = 10;
static const ap_uint<32> M243_BUILD_ID = 0x4D323433U;

static ap_int<24> m243_reduce8(ap_int<24> value[8]) {
#pragma HLS INLINE
#pragma HLS ARRAY_PARTITION variable=value complete
  ap_int<24> s01 = value[0] + value[1];
  ap_int<24> s23 = value[2] + value[3];
  ap_int<24> s45 = value[4] + value[5];
  ap_int<24> s67 = value[6] + value[7];
#pragma HLS BIND_OP variable=s01 op=add impl=dsp latency=2
#pragma HLS BIND_OP variable=s23 op=add impl=dsp latency=2
#pragma HLS BIND_OP variable=s45 op=add impl=dsp latency=2
#pragma HLS BIND_OP variable=s67 op=add impl=dsp latency=2
  ap_int<24> s03 = s01 + s23;
  ap_int<24> s47 = s45 + s67;
#pragma HLS BIND_OP variable=s03 op=add impl=dsp latency=2
#pragma HLS BIND_OP variable=s47 op=add impl=dsp latency=2
  ap_int<24> result = s03 + s47;
#pragma HLS BIND_OP variable=result op=add impl=dsp latency=2
  return result;
}

static void m89o_dot(const ap_int<5> a[M89_GROUP_SIZE],
                     const ap_int<5> b[M89_GROUP_SIZE],
                     const ap_uint<128> x[4], ap_int<24> &y0,
                     ap_int<24> &y1) {
#pragma HLS INLINE
  ap_int<24> low_part[8];
  ap_int<24> high_part[8];
#pragma HLS ARRAY_PARTITION variable=low_part complete
#pragma HLS ARRAY_PARTITION variable=high_part complete
  for (unsigned column = 0; column < 8; ++column) {
#pragma HLS UNROLL
    ap_int<56> packed_sum = 0;
    for (unsigned offset = 0; offset < 8; ++offset) {
#pragma HLS UNROLL
      unsigned lane = 8 * column + offset;
      ap_int<8> activation =
          (ap_int<8>)x[lane >> 4].range(8 * (lane & 15) + 7,
                                       8 * (lane & 15));
      ap_int<32> packed_weight = m89n_pack(a[lane], b[lane], 4);
      ap_int<40> product = packed_weight * activation;
#pragma HLS BIND_OP variable=product op=mul impl=dsp
      packed_sum += product;
    }
    ap_int<15> low = (ap_int<15>)packed_sum.range(14, 0);
    ap_int<32> high = (ap_int<32>)(packed_sum >> 15);
    if (low < 0)
      high += 1;
    low_part[column] = (ap_int<24>)low;
    high_part[column] = (ap_int<24>)high;
  }
  y0 = m243_reduce8(low_part);
  y1 = m243_reduce8(high_part);
}

static float m243_scale_float(ap_uint<16> bits) {
#pragma HLS INLINE
  ap_uint<5> exponent = bits.range(14, 10);
  ap_uint<10> mantissa = bits.range(9, 0);
  if (exponent == 0) {
    float value = (float)(unsigned)mantissa * 5.9604644775390625e-8f;
    return bits[15] ? -value : value;
  }
  return (float)m89s_bits_half(bits);
}

static void m243_decode_pair(const ap_uint<128> *record, unsigned pair,
                             unsigned bits, ap_uint<16> tagged0,
                             ap_uint<16> tagged1, ap_int<5> weight0[64],
                             ap_int<5> weight1[64]) {
#pragma HLS INLINE
#pragma HLS ARRAY_PARTITION variable=weight0 complete
#pragma HLS ARRAY_PARTITION variable=weight1 complete
  const unsigned base = 1 + pair * bits;
  ap_uint<128> low0 = record[base];
  ap_uint<128> high0 = bits == 4 ? record[base + 1] : (ap_uint<128>)0;
  ap_uint<128> low1 = record[base + bits / 2];
  ap_uint<128> high1 =
      bits == 4 ? record[base + bits / 2 + 1] : (ap_uint<128>)0;
  m89n_decode(low0, high0, tagged0, bits, weight0);
  m89n_decode(low1, high1, tagged1, bits, weight1);
}

static void m243_load_t64(
    hls::stream<m89_axis128_t> &tx,
    ap_uint<128> activation[M89_MAX_GROUPS][64][4],
    ap_uint<16> activation_scale[M89_MAX_GROUPS][64], unsigned groups,
    ap_uint<32> &status) {
#pragma HLS INLINE off
  for (unsigned token_block = 0; token_block < M243_TOKEN_BLOCKS;
       ++token_block)
    for (unsigned group = 0; group < groups; ++group)
      for (unsigned token = 0; token < 32; ++token)
        for (unsigned word = 0; word < 5; ++word) {
#pragma HLS PIPELINE II=1
          m89_axis128_t item = tx.read();
          bool expected_last = token_block + 1 == M243_TOKEN_BLOCKS &&
                               group + 1 == groups && token == 31 && word == 4;
          if ((bool)item.last != expected_last)
            status = 2;
          const unsigned token_index = token_block * 32 + token;
          if (word < 4)
            activation[group][token_index][word] = item.data;
          else
            activation_scale[group][token_index] = item.data.range(15, 0);
        }
}

struct m243_pair_t { ap_uint<32> data; };

static void m243_shard(
    const ap_uint<128> *memory,
    const ap_uint<128> activation[M89_MAX_GROUPS][64][4],
    const ap_uint<16> activation_scale[M89_MAX_GROUPS][64],
    hls::stream<m243_pair_t> &out, unsigned groups, unsigned rows,
    unsigned bits) {
#pragma HLS INLINE off
  float acc0[64][4];
  float acc1[64][4];
#pragma HLS BIND_STORAGE variable=acc0 type=ram_2p impl=bram
#pragma HLS BIND_STORAGE variable=acc1 type=ram_2p impl=bram
  const unsigned blocks = rows / 8;
  const unsigned words = 1 + 4 * bits;
  for (unsigned block = 0; block < blocks; ++block) {
    for (unsigned token = 0; token < 64; ++token)
      for (unsigned pair = 0; pair < 4; ++pair) {
#pragma HLS PIPELINE II=1
        acc0[token][pair] = 0.0f;
        acc1[token][pair] = 0.0f;
      }
    for (unsigned group = 0; group < groups; ++group) {
      const unsigned base = group * blocks * words + block * words;
      ap_uint<128> tagged = memory[base];
      for (unsigned pair = 0; pair < 4; ++pair) {
        ap_uint<16> tagged0 = tagged.range(32 * pair + 15, 32 * pair);
        ap_uint<16> tagged1 = tagged.range(32 * pair + 31, 32 * pair + 16);
        ap_int<5> weight0[64], weight1[64];
#pragma HLS ARRAY_PARTITION variable=weight0 complete
#pragma HLS ARRAY_PARTITION variable=weight1 complete
        m243_decode_pair(memory + base, pair, bits, tagged0, tagged1, weight0,
                         weight1);
        float scale0 = m243_scale_float(tagged0 & 0x7fff);
        float scale1 = m243_scale_float(tagged1 & 0x7fff);
        for (unsigned token = 0; token < 64; ++token) {
#pragma HLS PIPELINE II=1
          ap_int<24> dot0, dot1;
          m89o_dot(weight0, weight1, activation[group][token], dot0, dot1);
          float activation_value =
              m243_scale_float(activation_scale[group][token]);
          acc0[token][pair] += (float)dot0 * activation_value * scale0;
          acc1[token][pair] += (float)dot1 * activation_value * scale1;
        }
      }
    }
    for (unsigned token = 0; token < 64; ++token)
      for (unsigned pair = 0; pair < 4; ++pair) {
#pragma HLS PIPELINE II=1
        m243_pair_t item;
        item.data.range(15, 0) = m89s_half_bits((half)acc0[token][pair]);
        item.data.range(31, 16) = m89s_half_bits((half)acc1[token][pair]);
        out.write(item);
      }
  }
}

static void m243_merge(hls::stream<m243_pair_t> result[4],
                       hls::stream<m89_axis64_t> &rx, unsigned rows,
                       bool final_descriptor) {
#pragma HLS INLINE off
#pragma HLS ARRAY_PARTITION variable=result complete
  for (unsigned block = 0; block < rows / 8; ++block)
    for (unsigned token = 0; token < 64; ++token)
      for (unsigned shard = 0; shard < 4; ++shard)
        for (unsigned pair = 0; pair < 4; ++pair) {
#pragma HLS PIPELINE II=1
          m89_axis64_t item;
          ap_uint<32> value = result[shard].read().data;
          item.data = 0;
          item.data.range(15, 0) = value.range(15, 0);
          item.data.range(47, 32) = value.range(31, 16);
          item.keep = -1;
          item.strb = -1;
          item.last = final_descriptor && block + 1 == rows / 8 &&
                      token == 63 && shard == 3 && pair == 3;
          rx.write(item);
        }
}

static void m243_four(
    const ap_uint<128> *s0, const ap_uint<128> *s1,
    const ap_uint<128> *s2, const ap_uint<128> *s3,
    const ap_uint<128> activation[M89_MAX_GROUPS][64][4],
    const ap_uint<16> activation_scale[M89_MAX_GROUPS][64],
    hls::stream<m89_axis64_t> &rx, unsigned groups, unsigned rows,
    unsigned bits, bool final_descriptor) {
#pragma HLS INLINE off
#pragma HLS DATAFLOW
  hls::stream<m243_pair_t> result[4];
#pragma HLS ARRAY_PARTITION variable=result complete
#pragma HLS STREAM variable=result depth=16384
#pragma HLS BIND_STORAGE variable=result type=fifo impl=uram
  m243_shard(s0, activation, activation_scale, result[0], groups, rows, bits);
  m243_shard(s1, activation, activation_scale, result[1], groups, rows, bits);
  m243_shard(s2, activation, activation_scale, result[2], groups, rows, bits);
  m243_shard(s3, activation, activation_scale, result[3], groups, rows, bits);
  m243_merge(result, rx, rows, final_descriptor);
}

ap_uint<32> m243_t64_kernel(hls::stream<m89_axis128_t> &tx,
                            const ap_uint<128> *s0,
                            const ap_uint<128> *s1,
                            const ap_uint<128> *s2,
                            const ap_uint<128> *s3,
                            hls::stream<m89_axis64_t> &rx,
                            ap_uint<32> config) {
#pragma HLS INTERFACE axis port=tx
#pragma HLS INTERFACE m_axi port=s0 offset=slave bundle=w0 depth=524288 max_read_burst_length=64 num_read_outstanding=32
#pragma HLS INTERFACE m_axi port=s1 offset=slave bundle=w1 depth=524288 max_read_burst_length=64 num_read_outstanding=32
#pragma HLS INTERFACE m_axi port=s2 offset=slave bundle=w2 depth=524288 max_read_burst_length=64 num_read_outstanding=32
#pragma HLS INTERFACE m_axi port=s3 offset=slave bundle=w3 depth=524288 max_read_burst_length=64 num_read_outstanding=32
#pragma HLS INTERFACE axis port=rx
#pragma HLS INTERFACE s_axilite port=s0 bundle=control
#pragma HLS INTERFACE s_axilite port=s1 bundle=control
#pragma HLS INTERFACE s_axilite port=s2 bundle=control
#pragma HLS INTERFACE s_axilite port=s3 bundle=control
#pragma HLS INTERFACE s_axilite port=config bundle=control offset=0x80
#pragma HLS INTERFACE s_axilite port=return bundle=control
  unsigned groups = config.range(7, 0);
  unsigned bits = config.range(10, 8);
  unsigned descriptor_count = config.range(19, 16);
  unsigned token_blocks = config.range(23, 20);
  if (groups < 1 || groups > M89_MAX_GROUPS ||
      (bits != 2 && bits != 4) || descriptor_count < 1 ||
      descriptor_count > M243_MAX_CHAIN || token_blocks != M243_TOKEN_BLOCKS)
    return 0xE0000243U;

  ap_uint<32> status = 0;
  ap_uint<64> table[M243_MAX_CHAIN];
#pragma HLS BIND_STORAGE variable=table type=ram_1p impl=lutram
  for (unsigned i = 0; i < descriptor_count; ++i) {
#pragma HLS PIPELINE II=1
    m89_axis128_t item = tx.read();
    ap_uint<128> raw = item.data;
    table[i] = raw.range(63, 0);
    unsigned rows = raw.range(41, 32);
    if (item.last || raw.range(44, 42) != bits || rows < 8 ||
        rows > M89_MAX_ROWS_PER_SHARD || (rows & 7))
      status = 2;
  }
  if (status)
    return 0xE1000243U;

  ap_uint<128> activation[M89_MAX_GROUPS][64][4];
  ap_uint<16> activation_scale[M89_MAX_GROUPS][64];
#pragma HLS BIND_STORAGE variable=activation type=ram_2p impl=uram latency=2
#pragma HLS BIND_STORAGE variable=activation_scale type=ram_2p impl=bram latency=2
  m243_load_t64(tx, activation, activation_scale, groups, status);
  if (status)
    return 0xE2000243U;

  for (unsigned i = 0; i < descriptor_count; ++i) {
#pragma HLS LOOP_TRIPCOUNT min=1 max=10
    unsigned offset = table[i].range(31, 0);
    unsigned rows = table[i].range(41, 32);
    m243_four(s0 + offset, s1 + offset, s2 + offset, s3 + offset, activation,
              activation_scale, rx, groups, rows, bits,
              i + 1 == descriptor_count);
  }
  return M243_BUILD_ID;
}
