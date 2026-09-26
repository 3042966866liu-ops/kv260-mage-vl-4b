#include "decode_one.hpp"
#include <fstream>
#include <iostream>
#include <vector>
#include <cstdlib>
#include <string>
static unsigned read32(std::ifstream &f) {
  unsigned char b[4];f.read((char*)b,4);
  return unsigned(b[0])|(unsigned(b[1])<<8)|(unsigned(b[2])<<16)|(unsigned(b[3])<<24);
}
template<int N> static ap_uint<N> readword(std::ifstream &f) {
  unsigned char b[N/8];f.read((char*)b,N/8);ap_uint<N> v=0;
  for(unsigned i=0;i<N/8;++i)v.range(i*8+7,i*8)=b[i];return v;
}
int main() {
  const char *path=std::getenv("OP01_REAL_FIXTURE");if(!path)return 1;
  std::ifstream f(path,std::ios::binary);char magic[8];f.read(magic,8);
  if(!f||std::string(magic,8)!="OP1REAL1")return 2;
  unsigned wb=read32(f),ib=read32(f),ob=read32(f),config=read32(f);
  if(wb!=6617088||ib!=102560||ob!=2490368||config!=0x010a0428)return 3;
  std::vector<ap_uint<128> > weights[4];
  for(unsigned s=0;s<4;++s){weights[s].resize(wb/16);for(auto &v:weights[s])v=readword<128>(f);}
  hls::stream<m89_axis128_t> tx;hls::stream<m89_axis64_t> rx;
  for(unsigned i=0;i<ib/16;++i){m89_axis128_t v;v.data=readword<128>(f);v.keep=-1;v.strb=-1;v.last=(i+1==ib/16);tx.write(v);}
  if(!f)return 4;
  ap_uint<32> status=op01_decode_one_kernel(tx,weights[0].data(),weights[1].data(),weights[2].data(),weights[3].data(),rx,config);
  if(status!=0x4F503131U)return 5;
  for(unsigned i=0;i<ob/8;++i){
    if(rx.empty())return 6;
    auto item=rx.read();ap_uint<64> expected=readword<64>(f);
    if(item.data!=expected||bool(item.last)!=(i+1==ob/8)||item.keep!=255||item.strb!=255){
      std::cerr<<"REAL_GATE_UP_MISMATCH word="<<i<<"\n";return 7;
    }
  }
  if(!f||!rx.empty()||!tx.empty()||f.peek()!=std::char_traits<char>::eof())return 8;
  std::cout<<"OP01_REAL_GATE_UP_CSIM_PASS words="<<ob/8<<" active_values=19456\n";return 0;
}
