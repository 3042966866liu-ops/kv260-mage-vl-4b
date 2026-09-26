#define m89s_scaleaware m89s_scaleaware_reference
#include "../mage_prefill_m89s_scaleaware/mage_prefill_m89s_scaleaware.cpp"
#undef m89s_scaleaware

static const unsigned M89T_MAX_CHAIN = 10;

// Emit one packet per descriptor. A tiny RTL coalescer in the Vivado shell
// suppresses intermediate TLAST values without perturbing the arithmetic QoR.
ap_uint<32> m89t_scale_chain(hls::stream<m89_axis128_t> &tx,
                      const ap_uint<128> *s0, const ap_uint<128> *s1,
                      const ap_uint<128> *s2, const ap_uint<128> *s3,
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
#pragma HLS INTERFACE s_axilite port=config bundle=control
#pragma HLS INTERFACE s_axilite port=return bundle=control
  unsigned groups = config.range(7, 0);
  unsigned bits = config.range(10, 8);
  unsigned descriptor_count = config.range(19, 16);
  if (groups < 1 || groups > M89_MAX_GROUPS || (bits != 2 && bits != 4) ||
      descriptor_count < 1 ||
      descriptor_count > M89T_MAX_CHAIN) {
    return 0xE0000001U;
  }

  ap_uint<32> status = 0;
  ap_uint<64> table[M89T_MAX_CHAIN];
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

  ap_uint<128> x[M89_MAX_GROUPS][M89_TOKEN_LANES][4];
  ap_uint<16> as[M89_MAX_GROUPS][M89_TOKEN_LANES];
#pragma HLS BIND_STORAGE variable=x type=ram_2p impl=uram latency=2
#pragma HLS BIND_STORAGE variable=as type=ram_2p impl=bram latency=2
  m89s_load(tx, x, as, groups, status);
  if (status)
    return 0xE0000003U;

  for (unsigned i = 0; i < descriptor_count; ++i) {
#pragma HLS LOOP_TRIPCOUNT min=1 max=10
    unsigned offset = table[i].range(31, 0);
    unsigned rows = table[i].range(41, 32);
    m89s_four(s0 + offset, s1 + offset, s2 + offset, s3 + offset,
              x, as, rx, groups, rows, bits);
  }
  return 0x4D383954U;
}
