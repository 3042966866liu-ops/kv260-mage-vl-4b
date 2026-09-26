#include "decode_one.hpp"
#include <iostream>
static int run(bool decode,unsigned count,unsigned rows){
  static ap_uint<128> weights[4][524288];
  const unsigned groups=1,bits=4,words=17,blocks=rows/8;
  ap_uint<128> tag=0,codes=0,activation=0;
  for(unsigned j=0;j<8;++j)tag.range(j*16+15,j*16)=0x3800;
  for(unsigned j=0;j<32;++j)codes.range(j*4+3,j*4)=9;
  for(unsigned j=0;j<16;++j)activation.range(j*8+7,j*8)=1;
  for(unsigned s=0;s<4;++s)for(unsigned i=0;i<blocks*words;++i)weights[s][i]=(i%words==0)?tag:codes;
  hls::stream<m89_axis128_t> tx;hls::stream<m89_axis64_t> rx;
  for(unsigned d=0;d<count;++d){m89_axis128_t p;p.data=0;p.data.range(41,32)=rows;p.data.range(44,42)=bits;
    p.keep=-1;p.strb=-1;p.last=0;tx.write(p);}
  for(unsigned t=0;t<32;++t)for(unsigned w=0;w<5;++w){m89_axis128_t p;p.data=w==4?ap_uint<128>(0x3000):activation;
    p.keep=-1;p.strb=-1;p.last=t==31&&w==4;tx.write(p);}
  unsigned config=groups|(bits<<8)|(count<<16)|(decode?1U<<24:0);
  auto status=op01_decode_one_kernel(tx,weights[0],weights[1],weights[2],weights[3],rx,config);
  if(status!=0x4F503131U)return 1;
  unsigned n=0,total=count*blocks*32*4*4;
  for(unsigned d=0;d<count;++d)for(unsigned b=0;b<blocks;++b)for(unsigned t=0;t<32;++t)
    for(unsigned s=0;s<4;++s)for(unsigned p=0;p<4;++p){
      if(rx.empty())return 2;auto v=rx.read();ap_uint<64> expected=0;
      // 64 unit products * 0.125 * 0.5 = 4, exact IEEE half 0x4400.
      if(!decode||t==0){expected.range(15,0)=0x4400;expected.range(47,32)=0x4400;}
      ++n;if(v.data!=expected||v.keep!=255||v.strb!=255||bool(v.last)!=(n==total))return 3;
    }
  if(!tx.empty()||!rx.empty())return 4;
  std::cout<<"OP01_RTL_CASE_PASS decode="<<decode<<" rows="<<rows<<" descriptors="<<count<<" words="<<n<<"\n";
  return 0;
}
int main(){for(unsigned m=0;m<2;++m){int rc=run(m,1,512);if(rc)return rc;
    rc=run(m,10,8);if(rc)return rc;}
  std::cout<<"OP01_RTL_TRANSACTIONS_PASS\n";return 0;}
