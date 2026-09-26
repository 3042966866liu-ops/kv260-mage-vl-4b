#include "decode_one.hpp"
#include <iostream>
static int run(unsigned groups,unsigned bits,unsigned rows){
  static ap_uint<128> weights[4][524288];
  unsigned words=1+4*bits,blocks=rows/8;
  ap_uint<128> tag=0,codes=0,activation=0;
  for(unsigned j=0;j<8;++j)tag.range(j*16+15,j*16)=0x3800;
  for(unsigned j=0;j<128/bits;++j)codes.range(j*bits+bits-1,j*bits)=(1U<<(bits-1))+1;
  for(unsigned j=0;j<16;++j)activation.range(j*8+7,j*8)=1;
  for(unsigned s=0;s<4;++s)for(unsigned i=0;i<groups*blocks*words;++i)weights[s][i]=(i%words==0)?tag:codes;
  hls::stream<m89_axis128_t> tx;hls::stream<m89_axis64_t> rx;
  m89_axis128_t d;d.data=0;d.data.range(41,32)=rows;d.data.range(44,42)=bits;
  d.keep=-1;d.strb=-1;d.last=0;tx.write(d);
  for(unsigned g=0;g<groups;++g)for(unsigned t=0;t<32;++t)for(unsigned w=0;w<5;++w){
    m89_axis128_t p;p.data=w==4?ap_uint<128>(0x3000):activation;
    p.keep=-1;p.strb=-1;p.last=g+1==groups&&t==31&&w==4;tx.write(p);}
  auto status=op01_decode_one_kernel(tx,weights[0],weights[1],weights[2],weights[3],rx,0x01010000|(bits<<8)|groups);
  if(status!=0x4F503131U)return 1;
  unsigned n=0,total=blocks*32*4*4;
  // Independent exact half constants: 64*0.125*0.5*groups => 4 or 608.
  ap_uint<16> answer=groups==152?0x60c0:0x4400;
  for(unsigned b=0;b<blocks;++b)for(unsigned t=0;t<32;++t)for(unsigned s=0;s<4;++s)for(unsigned p=0;p<4;++p){
    if(rx.empty())return 2;auto v=rx.read();ap_uint<64> expected=0;
    if(t==0){expected.range(15,0)=answer;expected.range(47,32)=answer;}
    ++n;if(v.data!=expected||v.keep!=255||v.strb!=255||bool(v.last)!=(n==total))return 3;
  }
  if(!tx.empty()||!rx.empty())return 4;
  std::cout<<"OP01_SHAPE_CASE_PASS groups="<<groups<<" bits="<<bits<<" rows="<<rows<<" words="<<n<<"\n";
  return 0;
}
int main(){int rc=run(152,2,8);if(rc)return rc;rc=run(152,4,8);if(rc)return rc;
  rc=run(1,4,384);if(rc)return rc;std::cout<<"OP01_SHAPE_TRANSACTIONS_PASS\n";return 0;}
