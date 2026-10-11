#define m89o_shared15 m89o_shared15_reference
#include "../mage_prefill_m89o_shared15/mage_prefill_m89o_shared15.cpp"
#undef m89o_shared15
#include <hls_half.h>
#include <hls_math.h>

static half m89s_bits_half(ap_uint<16> bits){
#pragma HLS INLINE
  fp_struct<half> value(bits); return value.to_half();
}
static ap_uint<16> m89s_half_bits(half value){
#pragma HLS INLINE
  fp_struct<half> encoded(value); return encoded.data();
}

struct m89s_pair_t { ap_uint<32> data; };

static void m89s_load(hls::stream<m89_axis128_t>&tx,
                      ap_uint<128>x[M89_MAX_GROUPS][M89_TOKEN_LANES][4],
                      ap_uint<16>scale[M89_MAX_GROUPS][M89_TOKEN_LANES],
                      unsigned groups,ap_uint<32>&status){
#pragma HLS INLINE off
 for(unsigned g=0;g<groups;++g)for(unsigned t=0;t<M89_TOKEN_LANES;++t)for(unsigned w=0;w<5;++w){
#pragma HLS PIPELINE II=1
  m89_axis128_t item=tx.read();bool last=g+1==groups&&t+1==M89_TOKEN_LANES&&w==4;if((bool)item.last!=last)status=2;if(w<4)x[g][t][w]=item.data;else scale[g][t]=item.data.range(15,0);}}

static void m89s_shard(const ap_uint<128>*m,const ap_uint<128>x[M89_MAX_GROUPS][M89_TOKEN_LANES][4],
                       const ap_uint<16>as[M89_MAX_GROUPS][M89_TOKEN_LANES],hls::stream<m89s_pair_t>&out,
                       unsigned groups,unsigned rows,unsigned bits){
#pragma HLS INLINE off
 half acc0[M89_TOKEN_LANES][4],acc1[M89_TOKEN_LANES][4];
#pragma HLS ARRAY_PARTITION variable=acc0 cyclic factor=16 dim=1
#pragma HLS ARRAY_PARTITION variable=acc1 cyclic factor=16 dim=1
#pragma HLS BIND_STORAGE variable=acc0 type=ram_2p impl=lutram
#pragma HLS BIND_STORAGE variable=acc1 type=ram_2p impl=lutram
 unsigned blocks=rows/8,words=1+4*bits;
 for(unsigned block=0;block<blocks;++block){
  for(unsigned t=0;t<M89_TOKEN_LANES;++t)for(unsigned p=0;p<4;++p){
#pragma HLS PIPELINE II=1
   acc0[t][p]=(half)0.0f;acc1[t][p]=(half)0.0f;}
  for(unsigned g=0;g<groups;++g){unsigned base=g*blocks*words+block*words;ap_uint<128>tag=m[base];
   for(unsigned p=0;p<4;++p){unsigned at=base+1+p*bits;ap_uint<128>l0=m[at],h0=bits==4?m[at+1]:(ap_uint<128>)0,l1=m[at+bits/2],h1=bits==4?m[at+bits/2+1]:(ap_uint<128>)0;ap_uint<16>tag0=tag.range(32*p+15,32*p),tag1=tag.range(32*p+31,32*p+16);ap_int<5>w0[64],w1[64];
#pragma HLS ARRAY_PARTITION variable=w0 complete
#pragma HLS ARRAY_PARTITION variable=w1 complete
    m89n_decode(l0,h0,tag0,bits,w0);m89n_decode(l1,h1,tag1,bits,w1);half ws0=m89s_bits_half(tag0&0x7fff),ws1=m89s_bits_half(tag1&0x7fff);
    for(unsigned tp=0;tp<16;++tp){
#pragma HLS PIPELINE II=1
     unsigned t0=2*tp,t1=t0+1;ap_int<24>d00,d01,d10,d11;m89o_dot(w0,w1,x[g][t0],d00,d01);m89o_dot(w0,w1,x[g][t1],d10,d11);half a0=m89s_bits_half(as[g][t0]),a1=m89s_bits_half(as[g][t1]);
     half v00=(half)((half)d00*a0)*ws0, v01=(half)((half)d01*a0)*ws1;
     half v10=(half)((half)d10*a1)*ws0, v11=(half)((half)d11*a1)*ws1;
     acc0[t0][p]=(half)(acc0[t0][p]+v00);acc1[t0][p]=(half)(acc1[t0][p]+v01);
     acc0[t1][p]=(half)(acc0[t1][p]+v10);acc1[t1][p]=(half)(acc1[t1][p]+v11);
    }} }
  for(unsigned t=0;t<32;++t)for(unsigned p=0;p<4;++p){
#pragma HLS PIPELINE II=1
   m89s_pair_t item;item.data.range(15,0)=m89s_half_bits(acc0[t][p]);item.data.range(31,16)=m89s_half_bits(acc1[t][p]);out.write(item);}
 }}

static void m89s_merge(hls::stream<m89s_pair_t>r[4],hls::stream<m89_axis64_t>&rx,unsigned rows){
#pragma HLS INLINE off
#pragma HLS ARRAY_PARTITION variable=r complete
 for(unsigned b=0;b<rows/8;++b)for(unsigned t=0;t<32;++t)for(unsigned s=0;s<4;++s)for(unsigned p=0;p<4;++p){
#pragma HLS PIPELINE II=1
  m89_axis64_t item;ap_uint<32>v=r[s].read().data;item.data=0;item.data.range(15,0)=v.range(15,0);item.data.range(47,32)=v.range(31,16);item.keep=-1;item.strb=-1;item.last=b+1==rows/8&&t==31&&s==3&&p==3;rx.write(item);}}

static void m89s_four(const ap_uint<128>*s0,const ap_uint<128>*s1,const ap_uint<128>*s2,const ap_uint<128>*s3,
                      const ap_uint<128>x[M89_MAX_GROUPS][32][4],const ap_uint<16>as[M89_MAX_GROUPS][32],
                      hls::stream<m89_axis64_t>&rx,unsigned groups,unsigned rows,unsigned bits){
#pragma HLS INLINE off
#pragma HLS DATAFLOW
 hls::stream<m89s_pair_t>r[4];
#pragma HLS ARRAY_PARTITION variable=r complete
#pragma HLS STREAM variable=r depth=64
 m89s_shard(s0,x,as,r[0],groups,rows,bits);m89s_shard(s1,x,as,r[1],groups,rows,bits);m89s_shard(s2,x,as,r[2],groups,rows,bits);m89s_shard(s3,x,as,r[3],groups,rows,bits);m89s_merge(r,rx,rows);}

void m89s_scaleaware(hls::stream<m89_axis128_t>&tx,const ap_uint<128>*s0,const ap_uint<128>*s1,
                     const ap_uint<128>*s2,const ap_uint<128>*s3,hls::stream<m89_axis64_t>&rx,
                     unsigned groups,unsigned rows,unsigned bits,ap_uint<32>&status,ap_uint<32>&build,
                     ap_uint<32>&calls,ap_uint<32>&macros){
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
 status=0;build=0x4D383953U;calls=0;macros=0;if((bits!=2&&bits!=4)||groups<1||groups>M89_MAX_GROUPS||rows<8||rows>M89_MAX_ROWS_PER_SHARD||(rows&7)){status=1;return;}ap_uint<128>x[M89_MAX_GROUPS][32][4];ap_uint<16>as[M89_MAX_GROUPS][32];
#pragma HLS BIND_STORAGE variable=x type=ram_2p impl=uram latency=2
#pragma HLS BIND_STORAGE variable=as type=ram_2p impl=bram latency=2
 m89s_load(tx,x,as,groups,status);if(status)return;m89s_four(s0,s1,s2,s3,x,as,rx,groups,rows,bits);calls=1;macros=groups*rows*4*32;}
