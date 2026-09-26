// M89-N extends the M89-H weight-stationary T32 microarchitecture to the
// actual M56 language bit widths: W2 and W4.  A record is six-port layout
// data: 1 tagged-scale word plus 4*bits code words for eight output rows.
// This remains an offline HLS candidate, not a full model kernel.
#define m89h_t32_chunkedpacked m89h_t32_chunkedpacked_reference
#include "../mage_prefill_m89h_t32_chunkedpacked/mage_prefill_m89h_t32_chunkedpacked.cpp"
#undef m89h_t32_chunkedpacked

static ap_int<5> m89n_qmin(ap_uint<16> tagged, unsigned bits) {
#pragma HLS INLINE
    const ap_int<5> half = (ap_int<5>)(1 << (bits - 1));
    return tagged[15] ? (ap_int<5>)(-half + 1) : (ap_int<5>)-half;
}

static void m89n_decode(ap_uint<128> low, ap_uint<128> high, ap_uint<16> tagged,
                        unsigned bits, ap_int<5> decoded[M89_GROUP_SIZE]) {
#pragma HLS INLINE
#pragma HLS ARRAY_PARTITION variable=decoded complete dim=1
    const ap_int<5> minimum = m89n_qmin(tagged, bits);
    for (unsigned lane = 0; lane < M89_GROUP_SIZE; ++lane) {
#pragma HLS UNROLL
        ap_uint<4> code;
        if (bits == 2) code = low.range(2 * lane + 1, 2 * lane);
        else if (lane < 32) code = low.range(4 * lane + 3, 4 * lane);
        else code = high.range(4 * (lane - 32) + 3, 4 * (lane - 32));
        decoded[lane] = (ap_int<5>)code + minimum;
    }
}

static ap_int<32> m89n_pack(ap_int<5> weight0, ap_int<5> weight1, unsigned bits) {
#pragma HLS INLINE
    const unsigned shift = bits == 2 ? 13 : 15;
    const ap_int<7> upper = (ap_int<7>)weight1 - (weight0 < 0 ? 1 : 0);
    ap_int<32> packed = (ap_int<32>)upper << shift;
    if (bits == 2) packed.range(12, 0) = (ap_uint<13>)weight0;
    else packed.range(14, 0) = (ap_uint<15>)weight0;
    return packed;
}

static void m89n_dot_chunked(const ap_int<5> weights0[M89_GROUP_SIZE],
                             const ap_int<5> weights1[M89_GROUP_SIZE],
                             const ap_uint<128> activation_words[4], unsigned bits,
                             ap_int<24> &dot0, ap_int<24> &dot1) {
#pragma HLS INLINE
    ap_int<24> sum0 = 0, sum1 = 0;
    for (unsigned chunk = 0; chunk < 8; ++chunk) {
#pragma HLS UNROLL
        ap_int<56> packed_sum = 0;
        for (unsigned off = 0; off < 8; ++off) {
#pragma HLS UNROLL
            const unsigned lane = 8 * chunk + off;
            const ap_uint<128> packed = activation_words[lane >> 4];
            const ap_int<8> input = (ap_int<8>)packed.range(8 * (lane & 15U) + 7, 8 * (lane & 15U));
            const ap_int<32> packed_weights = m89n_pack(weights0[lane], weights1[lane], bits);
            const ap_int<40> packed_product = packed_weights * input;
#pragma HLS BIND_OP variable=packed_product op=mul impl=dsp
            packed_sum += packed_product;
        }
        if (bits == 2) {
            const ap_int<13> low = (ap_int<13>)packed_sum.range(12, 0);
            ap_int<32> high = (ap_int<32>)(packed_sum >> 13);
            if (low < 0) high += 1;
            sum0 += low; sum1 += high;
        } else {
            const ap_int<15> low = (ap_int<15>)packed_sum.range(14, 0);
            ap_int<32> high = (ap_int<32>)(packed_sum >> 15);
            if (low < 0) high += 1;
            sum0 += low; sum1 += high;
        }
    }
    dot0 = sum0; dot1 = sum1;
}

static void m89n_compute_shard(const ap_uint<128> *memory,
    const ap_uint<128> activation[M89_MAX_GROUPS][M89_TOKEN_LANES][4],
    hls::stream<m89d_pair_t> &result, unsigned input_groups, unsigned rows_per_shard,
    unsigned bits) {
#pragma HLS INLINE off
    ap_uint<64> accum[M89_TOKEN_LANES][4];
#pragma HLS ARRAY_PARTITION variable=accum cyclic factor=16 dim=1
#pragma HLS BIND_STORAGE variable=accum type=ram_2p impl=lutram
    const unsigned blocks = rows_per_shard / 8;
    const unsigned words_per_record = 1 + 4 * bits;
    for (unsigned block = 0; block < blocks; ++block) {
        for (unsigned token = 0; token < M89_TOKEN_LANES; ++token)
            for (unsigned pair = 0; pair < 4; ++pair) {
#pragma HLS PIPELINE II=1
                accum[token][pair] = 0;
            }
        for (unsigned group = 0; group < input_groups; ++group) {
            const unsigned base = group * blocks * words_per_record + block * words_per_record;
            const ap_uint<128> scale = memory[base];
            for (unsigned pair = 0; pair < 4; ++pair) {
                // A code row occupies bits/2 AXI words (one for W2, two for
                // W4), hence a two-row pair occupies exactly ``bits`` words.
                const unsigned pair_base = base + 1 + pair * bits;
                const ap_uint<128> code0_low = memory[pair_base];
                const ap_uint<128> code0_high = bits == 4 ? memory[pair_base + 1] : (ap_uint<128>)0;
                const ap_uint<128> code1_low = memory[pair_base + bits / 2];
                const ap_uint<128> code1_high = bits == 4 ? memory[pair_base + bits / 2 + 1] : (ap_uint<128>)0;
                const ap_uint<16> tagged0 = scale.range(32 * pair + 15, 32 * pair);
                const ap_uint<16> tagged1 = scale.range(32 * pair + 31, 32 * pair + 16);
                ap_int<5> weights0[M89_GROUP_SIZE], weights1[M89_GROUP_SIZE];
#pragma HLS ARRAY_PARTITION variable=weights0 complete dim=1
#pragma HLS ARRAY_PARTITION variable=weights1 complete dim=1
                m89n_decode(code0_low, code0_high, tagged0, bits, weights0);
                m89n_decode(code1_low, code1_high, tagged1, bits, weights1);
                for (unsigned token_pair = 0; token_pair < M89_TOKEN_PAIRS; ++token_pair) {
#pragma HLS PIPELINE II=1
                    const unsigned token0 = 2 * token_pair, token1 = token0 + 1;
                    ap_int<24> dot00, dot01, dot10, dot11;
                    m89n_dot_chunked(weights0, weights1, activation[group][token0], bits, dot00, dot01);
                    m89n_dot_chunked(weights0, weights1, activation[group][token1], bits, dot10, dot11);
                    const ap_uint<64> old0 = accum[token0][pair], old1 = accum[token1][pair];
                    ap_uint<64> next0, next1;
                    next0.range(31,0) = (ap_uint<32>)((ap_int<32>)old0.range(31,0) + dot00);
                    next0.range(63,32) = (ap_uint<32>)((ap_int<32>)old0.range(63,32) + dot01);
                    next1.range(31,0) = (ap_uint<32>)((ap_int<32>)old1.range(31,0) + dot10);
                    next1.range(63,32) = (ap_uint<32>)((ap_int<32>)old1.range(63,32) + dot11);
                    accum[token0][pair] = next0; accum[token1][pair] = next1;
                }
            }
        }
        for (unsigned token = 0; token < M89_TOKEN_LANES; ++token)
            for (unsigned pair = 0; pair < 4; ++pair) {
#pragma HLS PIPELINE II=1
                m89d_pair_t item; item.data = accum[token][pair]; result.write(item);
            }
    }
}

static void m89n_six_shards(const ap_uint<128> *shard0, const ap_uint<128> *shard1,
    const ap_uint<128> *shard2, const ap_uint<128> *shard3, const ap_uint<128> *shard4,
    const ap_uint<128> *shard5, const ap_uint<128> activation[M89_MAX_GROUPS][M89_TOKEN_LANES][4],
    hls::stream<m89_axis64_t> &rx, unsigned input_groups, unsigned rows_per_shard, unsigned bits) {
#pragma HLS INLINE off
#pragma HLS DATAFLOW
    hls::stream<m89d_pair_t> results[M89_SHARDS];
#pragma HLS ARRAY_PARTITION variable=results complete dim=1
#pragma HLS STREAM variable=results depth=64
    m89n_compute_shard(shard0,activation,results[0],input_groups,rows_per_shard,bits);
    m89n_compute_shard(shard1,activation,results[1],input_groups,rows_per_shard,bits);
    m89n_compute_shard(shard2,activation,results[2],input_groups,rows_per_shard,bits);
    m89n_compute_shard(shard3,activation,results[3],input_groups,rows_per_shard,bits);
    m89n_compute_shard(shard4,activation,results[4],input_groups,rows_per_shard,bits);
    m89n_compute_shard(shard5,activation,results[5],input_groups,rows_per_shard,bits);
    m89d_merge(results,rx,rows_per_shard);
}

void m89n_t32_w2w4(hls::stream<m89_axis128_t> &activation_tx,
    const ap_uint<128> *shard0,const ap_uint<128> *shard1,const ap_uint<128> *shard2,
    const ap_uint<128> *shard3,const ap_uint<128> *shard4,const ap_uint<128> *shard5,
    hls::stream<m89_axis64_t> &rx,unsigned input_groups,unsigned rows_per_shard,unsigned bits,
    ap_uint<32> &status,ap_uint<32> &build_id,ap_uint<32> &call_count,ap_uint<32> &processed_macros) {
#pragma HLS INTERFACE axis port=activation_tx
#pragma HLS INTERFACE m_axi port=shard0 offset=slave bundle=weights0 depth=524288 max_read_burst_length=64 num_read_outstanding=32
#pragma HLS INTERFACE m_axi port=shard1 offset=slave bundle=weights1 depth=524288 max_read_burst_length=64 num_read_outstanding=32
#pragma HLS INTERFACE m_axi port=shard2 offset=slave bundle=weights2 depth=524288 max_read_burst_length=64 num_read_outstanding=32
#pragma HLS INTERFACE m_axi port=shard3 offset=slave bundle=weights3 depth=524288 max_read_burst_length=64 num_read_outstanding=32
#pragma HLS INTERFACE m_axi port=shard4 offset=slave bundle=weights4 depth=524288 max_read_burst_length=64 num_read_outstanding=32
#pragma HLS INTERFACE m_axi port=shard5 offset=slave bundle=weights5 depth=524288 max_read_burst_length=64 num_read_outstanding=32
#pragma HLS INTERFACE axis port=rx
#pragma HLS INTERFACE s_axilite port=shard0 bundle=control
#pragma HLS INTERFACE s_axilite port=shard1 bundle=control
#pragma HLS INTERFACE s_axilite port=shard2 bundle=control
#pragma HLS INTERFACE s_axilite port=shard3 bundle=control
#pragma HLS INTERFACE s_axilite port=shard4 bundle=control
#pragma HLS INTERFACE s_axilite port=shard5 bundle=control
#pragma HLS INTERFACE s_axilite port=input_groups bundle=control
#pragma HLS INTERFACE s_axilite port=rows_per_shard bundle=control
#pragma HLS INTERFACE s_axilite port=bits bundle=control
#pragma HLS INTERFACE s_axilite port=status bundle=control
#pragma HLS INTERFACE s_axilite port=build_id bundle=control
#pragma HLS INTERFACE s_axilite port=call_count bundle=control
#pragma HLS INTERFACE s_axilite port=processed_macros bundle=control
#pragma HLS INTERFACE s_axilite port=return bundle=control
    static ap_uint<32> calls=0, macros=0;
    status=0; build_id=0x4D38394EU; call_count=calls; processed_macros=macros;
    if ((bits != 2 && bits != 4) || input_groups<1 || input_groups>M89_MAX_GROUPS || rows_per_shard<8 || rows_per_shard>M89_MAX_ROWS_PER_SHARD || (rows_per_shard&7U)!=0) { status=1; return; }
    ap_uint<128> activation[M89_MAX_GROUPS][M89_TOKEN_LANES][4];
#pragma HLS BIND_STORAGE variable=activation type=ram_2p impl=uram latency=2
    m89d_load_activation(activation_tx,activation,input_groups,status);
    m89n_six_shards(shard0,shard1,shard2,shard3,shard4,shard5,activation,rx,input_groups,rows_per_shard,bits);
    calls+=1; macros+=input_groups*rows_per_shard*M89_SHARDS*M89_TOKEN_LANES;
    call_count=calls; processed_macros=macros;
}
