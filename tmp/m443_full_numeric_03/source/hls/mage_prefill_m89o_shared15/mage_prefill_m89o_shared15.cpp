// M89-O: retain M89-N's real M56 record decoder but force the W2 and W4
// products through one fixed 15-bit separator.  W2's eight-lane sum fits
// safely in 15 bits too, so this removes the runtime-selected packed-MAC path.
#define m89n_t32_w2w4 m89n_t32_w2w4_reference
#include "../mage_prefill_m89n_t32_w2w4/mage_prefill_m89n_t32_w2w4.cpp"
#undef m89n_t32_w2w4

static void m89o_dot(const ap_int<5> a[M89_GROUP_SIZE],const ap_int<5> b[M89_GROUP_SIZE],const ap_uint<128> x[4],ap_int<24>&y0,ap_int<24>&y1){
#pragma HLS INLINE
 ap_int<24>s0=0,s1=0;for(unsigned c=0;c<8;++c){
#pragma HLS UNROLL
 ap_int<56>sum=0;for(unsigned o=0;o<8;++o){
#pragma HLS UNROLL
 unsigned l=8*c+o;ap_int<8> v=(ap_int<8>)x[l>>4].range(8*(l&15)+7,8*(l&15));ap_int<32>w=m89n_pack(a[l],b[l],4);ap_int<40>p=w*v;
#pragma HLS BIND_OP variable=p op=mul impl=dsp
 sum+=p;}ap_int<15>lo=(ap_int<15>)sum.range(14,0);ap_int<32>hi=(ap_int<32>)(sum>>15);if(lo<0)hi+=1;s0+=lo;s1+=hi;}y0=s0;y1=s1;}
static void m89o_shard(const ap_uint<128>*m,const ap_uint<128>x[M89_MAX_GROUPS][M89_TOKEN_LANES][4],hls::stream<m89d_pair_t>&out,unsigned gcount,unsigned rows,unsigned bits){
#pragma HLS INLINE off
 ap_uint<64>acc[M89_TOKEN_LANES][4];
#pragma HLS ARRAY_PARTITION variable=acc cyclic factor=16 dim=1
#pragma HLS BIND_STORAGE variable=acc type=ram_2p impl=lutram
 unsigned blocks=rows/8,words=1+4*bits;for(unsigned block=0;block<blocks;++block){for(unsigned t=0;t<M89_TOKEN_LANES;++t)for(unsigned p=0;p<4;++p){
#pragma HLS PIPELINE II=1
 acc[t][p]=0;}for(unsigned g=0;g<gcount;++g){unsigned base=g*blocks*words+block*words;ap_uint<128>scale=m[base];for(unsigned p=0;p<4;++p){unsigned at=base+1+p*bits;ap_uint<128>l0=m[at],h0=bits==4?m[at+1]:(ap_uint<128>)0,l1=m[at+bits/2],h1=bits==4?m[at+bits/2+1]:(ap_uint<128>)0;ap_int<5>w0[64],w1[64];
#pragma HLS ARRAY_PARTITION variable=w0 complete
#pragma HLS ARRAY_PARTITION variable=w1 complete
 m89n_decode(l0,h0,scale.range(32*p+15,32*p),bits,w0);m89n_decode(l1,h1,scale.range(32*p+31,32*p+16),bits,w1);for(unsigned tp=0;tp<16;++tp){
#pragma HLS PIPELINE II=1
 unsigned t0=2*tp,t1=t0+1;ap_int<24>a0,b0,a1,b1;m89o_dot(w0,w1,x[g][t0],a0,b0);m89o_dot(w0,w1,x[g][t1],a1,b1);ap_uint<64>n0,n1;n0.range(31,0)=(ap_uint<32>)((ap_int<32>)acc[t0][p].range(31,0)+a0);n0.range(63,32)=(ap_uint<32>)((ap_int<32>)acc[t0][p].range(63,32)+b0);n1.range(31,0)=(ap_uint<32>)((ap_int<32>)acc[t1][p].range(31,0)+a1);n1.range(63,32)=(ap_uint<32>)((ap_int<32>)acc[t1][p].range(63,32)+b1);acc[t0][p]=n0;acc[t1][p]=n1;}}}for(unsigned t=0;t<32;++t)for(unsigned p=0;p<4;++p){
#pragma HLS PIPELINE II=1
 m89d_pair_t i;i.data=acc[t][p];out.write(i);}}}
static void m89o_six(const ap_uint<128>*s0,const ap_uint<128>*s1,const ap_uint<128>*s2,const ap_uint<128>*s3,const ap_uint<128>*s4,const ap_uint<128>*s5,const ap_uint<128>x[M89_MAX_GROUPS][32][4],hls::stream<m89_axis64_t>&rx,unsigned groups,unsigned rows,unsigned bits){
#pragma HLS INLINE off
#pragma HLS DATAFLOW
 hls::stream<m89d_pair_t>r[6];
#pragma HLS ARRAY_PARTITION variable=r complete
#pragma HLS STREAM variable=r depth=64
 m89o_shard(s0,x,r[0],groups,rows,bits);m89o_shard(s1,x,r[1],groups,rows,bits);m89o_shard(s2,x,r[2],groups,rows,bits);m89o_shard(s3,x,r[3],groups,rows,bits);m89o_shard(s4,x,r[4],groups,rows,bits);m89o_shard(s5,x,r[5],groups,rows,bits);m89d_merge(r,rx,rows);}
void m89o_shared15(hls::stream<m89_axis128_t>&tx,const ap_uint<128>*s0,const ap_uint<128>*s1,const ap_uint<128>*s2,const ap_uint<128>*s3,const ap_uint<128>*s4,const ap_uint<128>*s5,hls::stream<m89_axis64_t>&rx,unsigned groups,unsigned rows,unsigned bits,ap_uint<32>&status,ap_uint<32>&build,ap_uint<32>&calls,ap_uint<32>&macros){
#pragma HLS INTERFACE axis port=tx
#pragma HLS INTERFACE m_axi port=s0 offset=slave bundle=w0 depth=524288
#pragma HLS INTERFACE m_axi port=s1 offset=slave bundle=w1 depth=524288
#pragma HLS INTERFACE m_axi port=s2 offset=slave bundle=w2 depth=524288
#pragma HLS INTERFACE m_axi port=s3 offset=slave bundle=w3 depth=524288
#pragma HLS INTERFACE m_axi port=s4 offset=slave bundle=w4 depth=524288
#pragma HLS INTERFACE m_axi port=s5 offset=slave bundle=w5 depth=524288
#pragma HLS INTERFACE axis port=rx
#pragma HLS INTERFACE s_axilite port=return bundle=control
 status=0;build=0x4D38394EU;calls=0;macros=0;if((bits!=2&&bits!=4)||groups<1||groups>M89_MAX_GROUPS||rows<8||rows>M89_MAX_ROWS_PER_SHARD||(rows&7)){status=1;return;}ap_uint<128>x[M89_MAX_GROUPS][32][4];
#pragma HLS BIND_STORAGE variable=x type=ram_2p impl=uram latency=2
 m89d_load_activation(tx,x,groups,status);m89o_six(s0,s1,s2,s3,s4,s5,x,rx,groups,rows,bits);calls=1;macros=groups*rows*M89_SHARDS*M89_TOKEN_LANES;}
