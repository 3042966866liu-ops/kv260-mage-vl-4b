// M89-H folds packed products in exact 8-lane groups.  A W2*int8 8-lane
// dot is bounded by [-2048, 2048], so its signed low 13-bit field cannot
// overflow.  This permits one packed-product unpack/carry correction per
// group instead of one per lane, while retaining all 64 packed DSP multiplies.
#define m89e_t32_packedaccum m89e_t32_packedaccum_reference
#include "../mage_prefill_m89e_t32_packedaccum/mage_prefill_m89e_t32_packedaccum.cpp"
#undef m89e_t32_packedaccum

static void m89h_dot_chunked(const ap_int<5> weights0[M89_GROUP_SIZE],
                             const ap_int<5> weights1[M89_GROUP_SIZE],
                             const ap_uint<128> activation_words[4],
                             ap_int<24> &dot0, ap_int<24> &dot1) {
#pragma HLS INLINE
    ap_int<24> sum0 = 0, sum1 = 0;
    for (unsigned chunk = 0; chunk < 8; ++chunk) {
#pragma HLS UNROLL
        ap_int<48> packed_sum = 0;
        for (unsigned off = 0; off < 8; ++off) {
#pragma HLS UNROLL
            const unsigned lane = 8 * chunk + off;
            const ap_uint<128> packed = activation_words[lane >> 4];
            const ap_int<8> input = (ap_int<8>)packed.range(8 * (lane & 15U) + 7, 8 * (lane & 15U));
            const ap_int<27> packed_weights = t6_pack_weights(weights0[lane], weights1[lane]);
            const ap_int<45> packed_product = packed_weights * input;
#pragma HLS BIND_OP variable=packed_product op=mul impl=dsp
            packed_sum += packed_product;
        }
        const ap_int<13> group0 = (ap_int<13>)packed_sum.range(12, 0);
        ap_int<32> group1 = (ap_int<32>)(packed_sum >> 13);
        if (group0 < 0) group1 += 1;
        sum0 += group0;
        sum1 += group1;
    }
    dot0 = sum0;
    dot1 = sum1;
}

static void m89h_compute_shard(
    const ap_uint<128> *memory,
    const ap_uint<128> activation[M89_MAX_GROUPS][M89_TOKEN_LANES][4],
    hls::stream<m89d_pair_t> &result, unsigned input_groups, unsigned rows_per_shard) {
#pragma HLS INLINE off
    ap_uint<64> accum[M89_TOKEN_LANES][4];
#pragma HLS ARRAY_PARTITION variable=accum cyclic factor=16 dim=1
#pragma HLS BIND_STORAGE variable=accum type=ram_2p impl=lutram
    const unsigned blocks = rows_per_shard / 8;
    for (unsigned block = 0; block < blocks; ++block) {
        for (unsigned token = 0; token < M89_TOKEN_LANES; ++token)
            for (unsigned pair = 0; pair < 4; ++pair) {
#pragma HLS PIPELINE II=1
                accum[token][pair] = 0;
            }
        for (unsigned group = 0; group < input_groups; ++group) {
            const unsigned base = group * blocks * 9 + block * 9;
            const ap_uint<128> scale = memory[base];
            for (unsigned pair = 0; pair < 4; ++pair) {
                const ap_uint<128> codes0 = memory[base + 1 + 2 * pair];
                const ap_uint<128> codes1 = memory[base + 2 + 2 * pair];
                const ap_uint<16> tagged0 = scale.range(32 * pair + 15, 32 * pair);
                const ap_uint<16> tagged1 = scale.range(32 * pair + 31, 32 * pair + 16);
                ap_int<5> weights0[M89_GROUP_SIZE], weights1[M89_GROUP_SIZE];
#pragma HLS ARRAY_PARTITION variable=weights0 complete dim=1
#pragma HLS ARRAY_PARTITION variable=weights1 complete dim=1
                m89e_decode_w2(codes0, tagged0, weights0);
                m89e_decode_w2(codes1, tagged1, weights1);
                for (unsigned token_pair = 0; token_pair < M89_TOKEN_PAIRS; ++token_pair) {
#pragma HLS PIPELINE II=1
                    const unsigned token0 = 2 * token_pair, token1 = token0 + 1;
                    ap_int<24> dot00, dot01, dot10, dot11;
                    m89h_dot_chunked(weights0, weights1, activation[group][token0], dot00, dot01);
                    m89h_dot_chunked(weights0, weights1, activation[group][token1], dot10, dot11);
                    const ap_uint<64> old0 = accum[token0][pair], old1 = accum[token1][pair];
                    ap_uint<64> next0, next1;
                    next0.range(31,0) = (ap_uint<32>)((ap_int<32>)old0.range(31,0) + dot00);
                    next0.range(63,32) = (ap_uint<32>)((ap_int<32>)old0.range(63,32) + dot01);
                    next1.range(31,0) = (ap_uint<32>)((ap_int<32>)old1.range(31,0) + dot10);
                    next1.range(63,32) = (ap_uint<32>)((ap_int<32>)old1.range(63,32) + dot11);
                    accum[token0][pair] = next0;
                    accum[token1][pair] = next1;
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

static void m89h_six_shards(const ap_uint<128> *shard0, const ap_uint<128> *shard1,
    const ap_uint<128> *shard2, const ap_uint<128> *shard3, const ap_uint<128> *shard4,
    const ap_uint<128> *shard5, const ap_uint<128> activation[M89_MAX_GROUPS][M89_TOKEN_LANES][4],
    hls::stream<m89_axis64_t> &rx, unsigned input_groups, unsigned rows_per_shard) {
#pragma HLS INLINE off
#pragma HLS DATAFLOW
    hls::stream<m89d_pair_t> results[M89_SHARDS];
#pragma HLS ARRAY_PARTITION variable=results complete dim=1
#pragma HLS STREAM variable=results depth=64
    m89h_compute_shard(shard0,activation,results[0],input_groups,rows_per_shard);
    m89h_compute_shard(shard1,activation,results[1],input_groups,rows_per_shard);
    m89h_compute_shard(shard2,activation,results[2],input_groups,rows_per_shard);
    m89h_compute_shard(shard3,activation,results[3],input_groups,rows_per_shard);
    m89h_compute_shard(shard4,activation,results[4],input_groups,rows_per_shard);
    m89h_compute_shard(shard5,activation,results[5],input_groups,rows_per_shard);
    m89d_merge(results,rx,rows_per_shard);
}

void m89h_t32_chunkedpacked(hls::stream<m89_axis128_t> &activation_tx,
    const ap_uint<128> *shard0,const ap_uint<128> *shard1,const ap_uint<128> *shard2,
    const ap_uint<128> *shard3,const ap_uint<128> *shard4,const ap_uint<128> *shard5,
    hls::stream<m89_axis64_t> &rx,unsigned input_groups,unsigned rows_per_shard,
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
#pragma HLS INTERFACE s_axilite port=status bundle=control
#pragma HLS INTERFACE s_axilite port=build_id bundle=control
#pragma HLS INTERFACE s_axilite port=call_count bundle=control
#pragma HLS INTERFACE s_axilite port=processed_macros bundle=control
#pragma HLS INTERFACE s_axilite port=return bundle=control
    static ap_uint<32> calls=0,macros=0;
    status=0; build_id=M89_BUILD_ID; call_count=calls; processed_macros=macros;
    if(input_groups<1||input_groups>M89_MAX_GROUPS||rows_per_shard<8||rows_per_shard>M89_MAX_ROWS_PER_SHARD||(rows_per_shard&7U)!=0){status=1;return;}
    ap_uint<128> activation[M89_MAX_GROUPS][M89_TOKEN_LANES][4];
#pragma HLS BIND_STORAGE variable=activation type=ram_2p impl=uram latency=2
    m89d_load_activation(activation_tx,activation,input_groups,status);
    m89h_six_shards(shard0,shard1,shard2,shard3,shard4,shard5,activation,rx,input_groups,rows_per_shard);
    calls+=1; macros+=input_groups*rows_per_shard*M89_SHARDS*M89_TOKEN_LANES;
    call_count=calls; processed_macros=macros;
}
