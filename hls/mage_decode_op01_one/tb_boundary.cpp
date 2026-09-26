#include "decode_one.hpp"
#include <hls_half.h>
#include <iostream>
#include <vector>
static m89_axis128_t packet(ap_uint<128> data, bool last=false){
  m89_axis128_t p;p.data=data;p.keep=-1;p.strb=-1;p.last=last;return p;
}
static ap_uint<128> descriptor(unsigned rows,unsigned bits){
  ap_uint<128> d=0;d.range(41,32)=rows;d.range(44,42)=bits;return d;
}
static unsigned invoke(hls::stream<m89_axis128_t>&tx,hls::stream<m89_axis64_t>&rx,
                       const ap_uint<128>*w,unsigned config){
  return op01_decode_one_kernel(tx,w,w,w,w,rx,config);
}
static int negative(){
  ap_uint<128> w=0;
  const unsigned configs[]={0x01010400,0x01010499,0x01010301,0x01000401,0x010b0401};
  for(unsigned c:configs){hls::stream<m89_axis128_t> tx;hls::stream<m89_axis64_t> rx;
    if(invoke(tx,rx,&w,c)!=0xE0000001U||!rx.empty())return 1;}
  for(unsigned i=0;i<5;++i){hls::stream<m89_axis128_t> tx;hls::stream<m89_axis64_t> rx;
    const unsigned rows[]={0,7,9,520,8};
    tx.write(packet(descriptor(rows[i],i==4?2:4)));
    if(invoke(tx,rx,&w,0x01010401)!=0xE0000002U||!rx.empty()||!tx.empty())return 2;}
  {hls::stream<m89_axis128_t> tx;hls::stream<m89_axis64_t> rx;
    tx.write(packet(descriptor(8,4),true));
    if(invoke(tx,rx,&w,0x01010401)!=0xE0000002U||!rx.empty())return 3;}
  // Supply all words: malformed TLAST is a numerical protocol test, not a missing-input timeout test.
  for(unsigned early=0;early<2;++early){hls::stream<m89_axis128_t> tx;hls::stream<m89_axis64_t> rx;
    tx.write(packet(descriptor(8,4)));
    for(unsigned i=0;i<160;++i)tx.write(packet(0,early&&i==0));
    if(invoke(tx,rx,&w,0x01010401)!=0xE0000003U||!rx.empty()||!tx.empty())return 4;}
  std::cout<<"OP01_NEGATIVE_PASS cases=13\n";return 0;
}
static int maximum(unsigned bits){
  const unsigned groups=152,rows=512,count=10,words=1+4*bits;
  std::vector<ap_uint<128>> weight(groups*(rows/8)*words);
  ap_uint<128> tag=0,codes=0;
  for(unsigned i=0;i<8;++i)tag.range(16*i+15,16*i)=0x3800; // scale 0.5, symmetric codebook
  for(unsigned i=0;i<128/bits;++i)codes.range(bits*i+bits-1,bits*i)=(1U<<(bits-1))+1;
  for(unsigned i=0;i<weight.size();++i)weight[i]=i%words==0?tag:codes;
  hls::stream<m89_axis128_t> tx;hls::stream<m89_axis64_t> rx;
  for(unsigned i=0;i<count;++i)tx.write(packet(descriptor(rows,bits)));
  for(unsigned g=0;g<groups;++g)for(unsigned t=0;t<32;++t)for(unsigned k=0;k<5;++k){
    ap_uint<128> v=0;
    if(k<4){for(unsigned j=0;j<16;++j)v.range(8*j+7,8*j)=1;}
    else v.range(15,0)=0x3000; // scale 0.125; inactive inputs deliberately nonzero
    tx.write(packet(v,g==151&&t==31&&k==4));
  }
  if(invoke(tx,rx,weight.data(),0x010a0000|(bits<<8)|groups)!=0x4F503131U)return 5;
  // Independent analytic answer: 152 groups * 64 * 1 * 1 * 0.125 * 0.5 = 608.
  const ap_uint<16> answer=0x60c0; // IEEE FP16: exponent24, mantissa192 => 608 exactly.
  unsigned n=0;
  for(unsigned d=0;d<count;++d)for(unsigned b=0;b<64;++b)for(unsigned t=0;t<32;++t)
    for(unsigned s=0;s<4;++s)for(unsigned p=0;p<4;++p){
      if(rx.empty())return 6;auto item=rx.read();ap_uint<64> expected=0;
      if(t==0){expected.range(15,0)=answer;expected.range(47,32)=answer;}
      ++n;if(item.data!=expected||bool(item.last)!=(n==327680)||item.keep!=255||item.strb!=255)return 7;
    }
  if(!tx.empty()||!rx.empty())return 8;
  std::cout<<"OP01_MAXIMUM_PASS bits="<<bits<<" words="<<n<<" groups=152 rows=512 descriptors=10\n";return 0;
}
int main(){int rc=negative();if(rc)return rc;rc=maximum(2);if(rc)return rc;
  rc=maximum(4);if(rc)return rc;std::cout<<"OP01_BOUNDARY_NUMERICAL_PASS\n";return 0;}
