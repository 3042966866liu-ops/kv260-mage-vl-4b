#define m89o_shared15 m89o_shared15_reference
#include "../mage_prefill_m89o_shared15/mage_prefill_m89o_shared15.cpp"
#undef m89o_shared15

static const unsigned M89P_SHARDS=4;
static void m89p_merge(hls::stream<m89d_pair_t> r[M89P_SHARDS],hls::stream<m89_axis64_t>&rx,unsigned rows){
#pragma HLS INLINE off
#pragma HLS ARRAY_PARTITION variable=r complete
 for(unsigned block=0;block<rows/8;++block)for(unsigned token=0;token<M89_TOKEN_LANES;++token)for(unsigned shard=0;shard<M89P_SHARDS;++shard)for(unsigned pair=0;pair<4;++pair){
#pragma HLS PIPELINE II=1
  m89_axis64_t item;item.data=r[shard].read().data;item.keep=-1;item.strb=-1;item.last=block+1==rows/8&&token+1==M89_TOKEN_LANES&&shard+1==M89P_SHARDS&&pair==3;rx.write(item);}}
static void m89p_four(const ap_uint<128>*s0,const ap_uint<128>*s1,const ap_uint<128>*s2,const ap_uint<128>*s3,const ap_uint<128>x[M89_MAX_GROUPS][M89_TOKEN_LANES][4],hls::stream<m89_axis64_t>&rx,unsigned groups,unsigned rows,unsigned bits){
#pragma HLS INLINE off
#pragma HLS DATAFLOW
 hls::stream<m89d_pair_t>r[M89P_SHARDS];
#pragma HLS ARRAY_PARTITION variable=r complete
#pragma HLS STREAM variable=r depth=64
 m89o_shard(s0,x,r[0],groups,rows,bits);m89o_shard(s1,x,r[1],groups,rows,bits);m89o_shard(s2,x,r[2],groups,rows,bits);m89o_shard(s3,x,r[3],groups,rows,bits);m89p_merge(r,rx,rows);}
void m89p_fourshard(hls::stream<m89_axis128_t>&tx,const ap_uint<128>*s0,const ap_uint<128>*s1,const ap_uint<128>*s2,const ap_uint<128>*s3,hls::stream<m89_axis64_t>&rx,unsigned groups,unsigned rows,unsigned bits,ap_uint<32>&status,ap_uint<32>&build,ap_uint<32>&calls,ap_uint<32>&macros){
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
#pragma HLS INTERFACE s_axilite port=groups bundle=control
#pragma HLS INTERFACE s_axilite port=rows bundle=control
#pragma HLS INTERFACE s_axilite port=bits bundle=control
#pragma HLS INTERFACE s_axilite port=status bundle=control
#pragma HLS INTERFACE s_axilite port=build bundle=control
#pragma HLS INTERFACE s_axilite port=calls bundle=control
#pragma HLS INTERFACE s_axilite port=macros bundle=control
#pragma HLS INTERFACE s_axilite port=return bundle=control
 status=0;build=0x4D383950U;calls=0;macros=0;if((bits!=2&&bits!=4)||groups<1||groups>M89_MAX_GROUPS||rows<8||rows>M89_MAX_ROWS_PER_SHARD||(rows&7)){status=1;return;}ap_uint<128>x[M89_MAX_GROUPS][M89_TOKEN_LANES][4];
#pragma HLS BIND_STORAGE variable=x type=ram_2p impl=uram latency=2
 m89d_load_activation(tx,x,groups,status);m89p_four(s0,s1,s2,s3,x,rx,groups,rows,bits);calls=1;macros=groups*rows*M89P_SHARDS*M89_TOKEN_LANES;}
