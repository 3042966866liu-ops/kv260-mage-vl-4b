#define m89p_fourshard m89p_fourshard_reference
#include "../mage_prefill_m89p_fourshard/mage_prefill_m89p_fourshard.cpp"
#undef m89p_fourshard

static const unsigned M89R_MAX_CHAIN = 10;

static void m89r_merge(hls::stream<m89d_pair_t> r[4], hls::stream<m89_axis64_t> &rx,
                       unsigned rows, bool final_descriptor) {
#pragma HLS INLINE off
#pragma HLS ARRAY_PARTITION variable=r complete
  for (unsigned block=0; block<rows/8; ++block)
    for (unsigned token=0; token<M89_TOKEN_LANES; ++token)
      for (unsigned shard=0; shard<4; ++shard)
        for (unsigned pair=0; pair<4; ++pair) {
#pragma HLS PIPELINE II=1
          m89_axis64_t item; item.data=r[shard].read().data; item.keep=-1; item.strb=-1;
          item.last=final_descriptor && block+1==rows/8 && token+1==M89_TOKEN_LANES && shard==3 && pair==3;
          rx.write(item);
        }
}

static void m89r_four(const ap_uint<128>*s0,const ap_uint<128>*s1,const ap_uint<128>*s2,
                      const ap_uint<128>*s3,const ap_uint<128>x[M89_MAX_GROUPS][M89_TOKEN_LANES][4],
                      hls::stream<m89_axis64_t>&rx,unsigned groups,unsigned rows,unsigned bits,bool final_descriptor) {
#pragma HLS INLINE off
#pragma HLS DATAFLOW
  hls::stream<m89d_pair_t> r[4];
#pragma HLS ARRAY_PARTITION variable=r complete
#pragma HLS STREAM variable=r depth=64
  m89o_shard(s0,x,r[0],groups,rows,bits); m89o_shard(s1,x,r[1],groups,rows,bits);
  m89o_shard(s2,x,r[2],groups,rows,bits); m89o_shard(s3,x,r[3],groups,rows,bits);
  m89r_merge(r,rx,rows,final_descriptor);
}

void m89r_chain(hls::stream<m89_axis128_t>&tx,const ap_uint<128>*desc,const ap_uint<128>*s0,
                const ap_uint<128>*s1,const ap_uint<128>*s2,const ap_uint<128>*s3,
                hls::stream<m89_axis64_t>&rx,unsigned groups,unsigned descriptor_count,
                ap_uint<32>&status,ap_uint<32>&build,ap_uint<32>&calls,
                ap_uint<32>&descriptors_done,ap_uint<32>&macros) {
#pragma HLS INTERFACE axis port=tx
#pragma HLS INTERFACE m_axi port=desc offset=slave bundle=w0 depth=16
#pragma HLS INTERFACE m_axi port=s0 offset=slave bundle=w0 depth=524288 max_read_burst_length=64 num_read_outstanding=32
#pragma HLS INTERFACE m_axi port=s1 offset=slave bundle=w1 depth=524288 max_read_burst_length=64 num_read_outstanding=32
#pragma HLS INTERFACE m_axi port=s2 offset=slave bundle=w2 depth=524288 max_read_burst_length=64 num_read_outstanding=32
#pragma HLS INTERFACE m_axi port=s3 offset=slave bundle=w3 depth=524288 max_read_burst_length=64 num_read_outstanding=32
#pragma HLS INTERFACE axis port=rx
#pragma HLS INTERFACE s_axilite port=desc bundle=control
#pragma HLS INTERFACE s_axilite port=s0 bundle=control
#pragma HLS INTERFACE s_axilite port=s1 bundle=control
#pragma HLS INTERFACE s_axilite port=s2 bundle=control
#pragma HLS INTERFACE s_axilite port=s3 bundle=control
#pragma HLS INTERFACE s_axilite port=groups bundle=control
#pragma HLS INTERFACE s_axilite port=descriptor_count bundle=control
#pragma HLS INTERFACE s_axilite port=status bundle=control
#pragma HLS INTERFACE s_axilite port=build bundle=control
#pragma HLS INTERFACE s_axilite port=calls bundle=control
#pragma HLS INTERFACE s_axilite port=descriptors_done bundle=control
#pragma HLS INTERFACE s_axilite port=macros bundle=control
#pragma HLS INTERFACE s_axilite port=return bundle=control
  status=0; build=0x4D383952U; calls=0; descriptors_done=0; macros=0;
  if (groups<1 || groups>M89_MAX_GROUPS || descriptor_count<1 || descriptor_count>M89R_MAX_CHAIN) {status=1; return;}
  ap_uint<128> table[M89R_MAX_CHAIN];
#pragma HLS ARRAY_PARTITION variable=table complete
  for (unsigned i=0;i<descriptor_count;++i) {
#pragma HLS PIPELINE II=1
    table[i]=desc[i]; unsigned rows=table[i].range(41,32); unsigned bits=table[i].range(44,42);
    if ((bits!=2&&bits!=4)||rows<8||rows>M89_MAX_ROWS_PER_SHARD||(rows&7)) status=2;
  }
  if (status) return;
  ap_uint<128> x[M89_MAX_GROUPS][M89_TOKEN_LANES][4];
#pragma HLS BIND_STORAGE variable=x type=ram_2p impl=uram latency=2
  m89d_load_activation(tx,x,groups,status); if(status)return;
  for (unsigned i=0;i<descriptor_count;++i) {
#pragma HLS LOOP_TRIPCOUNT min=1 max=10
    unsigned offset=table[i].range(31,0); unsigned rows=table[i].range(41,32); unsigned bits=table[i].range(44,42);
    m89r_four(s0+offset,s1+offset,s2+offset,s3+offset,x,rx,groups,rows,bits,i+1==descriptor_count);
    macros += groups*rows*4*M89_TOKEN_LANES; descriptors_done=i+1;
  }
  calls=1;
}
