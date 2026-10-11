// M89-G shares the packed DSP operand as well as raw W2 decode across the two
// tokens that consume a record.  Arithmetic is the same bit-level packed MAC
// identity used by t6_packed_mac2.
#define m89e_t32_packedaccum m89e_t32_packedaccum_reference
#include "../mage_prefill_m89e_t32_packedaccum/mage_prefill_m89e_t32_packedaccum.cpp"
#undef m89e_t32_packedaccum

static void m89g_prepack_w2(ap_uint<128> codes0, ap_uint<128> codes1,
                            ap_uint<16> tagged0, ap_uint<16> tagged1,
                            ap_int<27> packed[M89_GROUP_SIZE]) {
#pragma HLS INLINE
#pragma HLS ARRAY_PARTITION variable=packed complete dim=1
    const ap_int<5> qmin0 = m89d_qmin(tagged0), qmin1 = m89d_qmin(tagged1);
    for (unsigned lane = 0; lane < M89_GROUP_SIZE; ++lane) {
#pragma HLS UNROLL
        const ap_int<5> weight0 = (ap_uint<2>)codes0.range(2 * lane + 1, 2 * lane) + qmin0;
        const ap_int<5> weight1 = (ap_uint<2>)codes1.range(2 * lane + 1, 2 * lane) + qmin1;
        packed[lane] = t6_pack_weights(weight0, weight1);
    }
}

static void m89g_dot_prepacked(const ap_int<27> packed[M89_GROUP_SIZE],
                               const ap_uint<128> words[4],
                               ap_int<24> &dot0, ap_int<24> &dot1) {
#pragma HLS INLINE
    ap_int<24> sum0 = 0, sum1 = 0;
    for (unsigned lane = 0; lane < M89_GROUP_SIZE; ++lane) {
#pragma HLS UNROLL
        const ap_uint<128> block = words[lane >> 4];
        const ap_int<8> input = (ap_int<8>)block.range(8 * (lane & 15U) + 7, 8 * (lane & 15U));
        const ap_int<45> product = packed[lane] * input;
#pragma HLS BIND_OP variable=product op=mul impl=dsp
        const ap_int<13> low = (ap_int<13>)product.range(12, 0);
        ap_int<32> high = (ap_int<32>)(product >> 13);
        if (low < 0) high += 1;
        sum0 += low; sum1 += high;
    }
    dot0 = sum0; dot1 = sum1;
}

static void m89g_compute_shard(const ap_uint<128> *memory,
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
                ap_int<27> packed[M89_GROUP_SIZE];
#pragma HLS ARRAY_PARTITION variable=packed complete dim=1
                m89g_prepack_w2(codes0, codes1, tagged0, tagged1, packed);
                for (unsigned token_pair = 0; token_pair < M89_TOKEN_PAIRS; ++token_pair) {
#pragma HLS PIPELINE II=1
                    const unsigned token0 = 2 * token_pair, token1 = token0 + 1;
                    ap_int<24> dot00, dot01, dot10, dot11;
                    m89g_dot_prepacked(packed, activation[group][token0], dot00, dot01);
                    m89g_dot_prepacked(packed, activation[group][token1], dot10, dot11);
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

static void m89g_six_shards(const ap_uint<128> *shard0, const ap_uint<128> *shard1,
    const ap_uint<128> *shard2, const ap_uint<128> *shard3, const ap_uint<128> *shard4,
    const ap_uint<128> *shard5, const ap_uint<128> activation[M89_MAX_GROUPS][M89_TOKEN_LANES][4],
    hls::stream<m89_axis64_t> &rx, unsigned input_groups, unsigned rows_per_shard) {
#pragma HLS INLINE off
#pragma HLS DATAFLOW
    hls::stream<m89d_pair_t> results[M89_SHARDS];
#pragma HLS ARRAY_PARTITION variable=results complete dim=1
#pragma HLS STREAM variable=results depth=64
    m89g_compute_shard(shard0,activation,results[0],input_groups,rows_per_shard);
    m89g_compute_shard(shard1,activation,results[1],input_groups,rows_per_shard);
    m89g_compute_shard(shard2,activation,results[2],input_groups,rows_per_shard);
    m89g_compute_shard(shard3,activation,results[3],input_groups,rows_per_shard);
    m89g_compute_shard(shard4,activation,results[4],input_groups,rows_per_shard);
    m89g_compute_shard(shard5,activation,results[5],input_groups,rows_per_shard);
    m89d_merge(results,rx,rows_per_shard);
}

void m89g_t32_prepacked(hls::stream<m89_axis128_t> &activation_tx,
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
    m89g_six_shards(shard0,shard1,shard2,shard3,shard4,shard5,activation,rx,input_groups,rows_per_shard);
    calls+=1; macros+=input_groups*rows_per_shard*M89_SHARDS*M89_TOKEN_LANES;
    call_count=calls; processed_macros=macros;
}
