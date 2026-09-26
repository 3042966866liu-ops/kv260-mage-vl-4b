// Board-shell candidate: the verified M89-S arithmetic with the M89-V
// 152-group geometry and chain-final TLAST generated directly in HLS.
#define M89_MAX_GROUPS_VALUE 152
#include "decode_one.hpp"
#define m89s_scaleaware m89s_scaleaware_reference
#include "../mage_prefill_m89s_scaleaware/mage_prefill_m89s_scaleaware.cpp"
#undef m89s_scaleaware
#undef M89_MAX_GROUPS_VALUE

static const unsigned M89X_MAX_CHAIN = 10;

static float m89x_scale_float(ap_uint<16> bits) {
#pragma HLS INLINE
  // The Xilinx half model deliberately flushes subnormals while decoding.
  // Quantized activation/weight scales are positive, so expand an exponent-0
  // payload directly as mantissa * 2^-24 before entering the FP32 datapath.
  ap_uint<5> exponent = bits.range(14, 10);
  ap_uint<10> mantissa = bits.range(9, 0);
  if (exponent == 0) {
    float value = (float)(unsigned)mantissa * 5.9604644775390625e-8f;
    return bits[15] ? -value : value;
  }
  return (float)m89s_bits_half(bits);
}

static void m89x_decode_pair(const ap_uint<128> *record, unsigned pair,
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
  ap_uint<128> high1 = bits == 4 ? record[base + bits / 2 + 1] : (ap_uint<128>)0;
  m89n_decode(low0, high0, tagged0, bits, weight0);
  m89n_decode(low1, high1, tagged1, bits, weight1);
}

static void m89x_shard(const ap_uint<128> *memory,
                       const ap_uint<128> x[M89_MAX_GROUPS][32][4],
                       const ap_uint<16> as[M89_MAX_GROUPS][32],
                       hls::stream<m89s_pair_t> &out, unsigned groups,
                       unsigned rows, unsigned bits, bool decode_one) {
#pragma HLS INLINE off
  // M89-X2: keep the scale product and the cross-group accumulator in FP32.
  // The Vitis half operator flushes FP16 subnormals to zero; RMSNorm-derived
  // activation scales make many valid dot*activation*weight terms subnormal.
  // Converting the two (normal) stored scales to float before multiplication
  // preserves those contributions and rounds only once at the AXIS FP16 edge.
  float acc0[32][4], acc1[32][4];
#pragma HLS ARRAY_PARTITION variable=acc0 cyclic factor=16 dim=1
#pragma HLS ARRAY_PARTITION variable=acc1 cyclic factor=16 dim=1
#pragma HLS BIND_STORAGE variable=acc0 type=ram_2p impl=lutram
#pragma HLS BIND_STORAGE variable=acc1 type=ram_2p impl=lutram
  const unsigned blocks = rows / 8;
  const unsigned words = 1 + 4 * bits;
  for (unsigned block = 0; block < blocks; ++block) {
    for (unsigned token = 0; token < 32; ++token)
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
        m89x_decode_pair(memory + base, pair, bits, tagged0, tagged1,
                         weight0, weight1);
        float scale0 = m89x_scale_float(tagged0 & 0x7fff);
        float scale1 = m89x_scale_float(tagged1 & 0x7fff);
        for (unsigned token_pair = 0; token_pair < (decode_one ? 1U : 16U); ++token_pair) {
#pragma HLS PIPELINE II=1
          unsigned token0 = 2 * token_pair, token1 = token0 + 1;
          ap_int<24> dot00, dot01, dot10, dot11;
          m89o_dot(weight0, weight1, x[group][token0], dot00, dot01);
          m89o_dot(weight0, weight1, x[group][token1], dot10, dot11);
          float activation0 = m89x_scale_float(as[group][token0]);
          float activation1 = m89x_scale_float(as[group][token1]);
          acc0[token0][pair] += (float)dot00 * activation0 * scale0;
          acc1[token0][pair] += (float)dot01 * activation0 * scale1;
          acc0[token1][pair] += (float)dot10 * activation1 * scale0;
          acc1[token1][pair] += (float)dot11 * activation1 * scale1;
        }
      }
    }
    for (unsigned token = 0; token < 32; ++token)
      for (unsigned pair = 0; pair < 4; ++pair) {
#pragma HLS PIPELINE II=1
        m89s_pair_t item;
        item.data.range(15, 0) = (decode_one && token != 0) ? ap_uint<16>(0) : m89s_half_bits((half)acc0[token][pair]);
        item.data.range(31, 16) = (decode_one && token != 0) ? ap_uint<16>(0) : m89s_half_bits((half)acc1[token][pair]);
        out.write(item);
      }
  }
}

static void m89x_merge(hls::stream<m89s_pair_t> r[4],
                       hls::stream<m89_axis64_t> &rx,
                       unsigned rows, bool final_descriptor) {
#pragma HLS INLINE off
#pragma HLS ARRAY_PARTITION variable=r complete
  for (unsigned block = 0; block < rows / 8; ++block)
    for (unsigned token = 0; token < 32; ++token)
      for (unsigned shard = 0; shard < 4; ++shard)
        for (unsigned pair = 0; pair < 4; ++pair) {
#pragma HLS PIPELINE II=1
          m89_axis64_t item;
          ap_uint<32> value = r[shard].read().data;
          item.data = 0;
          item.data.range(15, 0) = value.range(15, 0);
          item.data.range(47, 32) = value.range(31, 16);
          item.keep = -1;
          item.strb = -1;
          item.last = final_descriptor && block + 1 == rows / 8 &&
                      token == 31 && shard == 3 && pair == 3;
          rx.write(item);
        }
}

static void m89x_four(const ap_uint<128> *s0, const ap_uint<128> *s1,
                      const ap_uint<128> *s2, const ap_uint<128> *s3,
                      const ap_uint<128> x[M89_MAX_GROUPS][32][4],
                      const ap_uint<16> as[M89_MAX_GROUPS][32],
                      hls::stream<m89_axis64_t> &rx, unsigned groups,
                      unsigned rows, unsigned bits, bool final_descriptor, bool decode_one) {
#pragma HLS INLINE off
#pragma HLS DATAFLOW
  hls::stream<m89s_pair_t> result[4];
#pragma HLS ARRAY_PARTITION variable=result complete
  // Vitis 2026.1 schedules the four shard producers through a generated
  // activation-read process.  With only 64 entries that process can fill
  // result[0] before result[1] becomes available, while the interleaved merge
  // is already waiting on result[1]: a deterministic RTL deadlock that CSim
  // cannot expose.  One shard emits at most 512/8 * 32 * 4 = 8192 pairs per
  // descriptor, so this exact bound lets a producer complete before the merge
  // advances without relying on scheduler-specific overlap.
#pragma HLS STREAM variable=result depth=8192
  m89x_shard(s0, x, as, result[0], groups, rows, bits, decode_one);
  m89x_shard(s1, x, as, result[1], groups, rows, bits, decode_one);
  m89x_shard(s2, x, as, result[2], groups, rows, bits, decode_one);
  m89x_shard(s3, x, as, result[3], groups, rows, bits, decode_one);
  m89x_merge(result, rx, rows, final_descriptor);
}

ap_uint<32> op01_decode_one_kernel(hls::stream<m89_axis128_t> &tx,
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
// Keep the AXI-Lite address channel explicitly eight bits wide.  The retained
// KV260 control SmartConnect exposes an 8-bit M02 port; allowing HLS to place
// the last register at 0x48 narrows the generated slave to seven bits and
// Vivado 2026.1 then produces an incompatible 8-bit black box / 7-bit DCP.
#pragma HLS INTERFACE s_axilite port=config bundle=control offset=0x80
#pragma HLS INTERFACE s_axilite port=return bundle=control
  unsigned groups = config.range(7, 0);
  unsigned bits = config.range(10, 8);
  unsigned descriptor_count = config.range(19, 16);
  if (groups < 1 || groups > M89_MAX_GROUPS ||
      (bits != 2 && bits != 4) || descriptor_count < 1 ||
      descriptor_count > M89X_MAX_CHAIN)
    return 0xE0000001U;

  ap_uint<32> status = 0;
  ap_uint<64> table[M89X_MAX_CHAIN];
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
    return 0xE0000002U;

  ap_uint<128> activation[M89_MAX_GROUPS][M89_TOKEN_LANES][4];
  ap_uint<16> activation_scale[M89_MAX_GROUPS][M89_TOKEN_LANES];
#pragma HLS BIND_STORAGE variable=activation type=ram_2p impl=uram latency=2
#pragma HLS BIND_STORAGE variable=activation_scale type=ram_2p impl=bram latency=2
  m89s_load(tx, activation, activation_scale, groups, status);
  if (status)
    return 0xE0000003U;

  for (unsigned i = 0; i < descriptor_count; ++i) {
#pragma HLS LOOP_TRIPCOUNT min=1 max=10
    unsigned offset = table[i].range(31, 0);
    unsigned rows = table[i].range(41, 32);
    m89x_four(s0 + offset, s1 + offset, s2 + offset, s3 + offset,
              activation, activation_scale, rx, groups, rows, bits,
              i + 1 == descriptor_count, config[24]);
  }
  // M89-X2: FP32 scale/accumulation correction after the X1 non-unit-scale
  // Layer-0 rejection.  Keep the identity distinct from both X and X1.
  return 0x4F503131U;
}
