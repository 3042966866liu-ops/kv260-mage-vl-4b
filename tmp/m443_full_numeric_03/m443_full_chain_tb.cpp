#include "mage_prefill_m89x_runtime.hpp"
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

static unsigned read32(std::ifstream &in) {
  unsigned char b[4]; in.read((char*)b,4);
  return unsigned(b[0])|(unsigned(b[1])<<8)|(unsigned(b[2])<<16)|(unsigned(b[3])<<24);
}
static ap_uint<128> read128(std::ifstream &in) {
  unsigned char b[16]; in.read((char*)b,16); ap_uint<128> v=0;
  for(unsigned j=0;j<16;++j) v.range(j*8+7,j*8)=b[j];
  return v;
}
static ap_uint<64> read64(std::ifstream &in) {
  unsigned char b[8]; in.read((char*)b,8); ap_uint<64> v=0;
  for(unsigned j=0;j<8;++j) v.range(j*8+7,j*8)=b[j];
  return v;
}
int main() {
  const char *root=std::getenv("M441_FULL_FIXTURE_ROOT"); if(!root) return 1;
  unsigned long long total_words=0;
  for(unsigned ordinal=0;ordinal<3;++ordinal) {
    std::string name=std::string(root)+"/case"+std::to_string(ordinal)+".bin";
    std::ifstream in(name,std::ios::binary); char magic[8]; in.read(magic,8);
    if(!in||std::string(magic,8)!="M441FUL1") return 2;
    unsigned config=read32(in), count=read32(in), packet_bytes=read32(in);
    unsigned output_bytes=read32(in), window_bytes=read32(in);
    if(!in||count<1||count>10||count!=((config>>16)&15)||packet_bytes%16||output_bytes%8||window_bytes%16) return 3;
    hls::stream<m89_axis128_t> tx; hls::stream<m89_axis64_t> rx;
    for(unsigned j=0;j<packet_bytes/16;++j) {
      m89_axis128_t item; item.data=read128(in); item.keep=-1; item.strb=-1;
      item.last=(j+1==packet_bytes/16); tx.write(item);
    }
    std::vector<ap_uint<128> > weights[4];
    for(unsigned shard=0;shard<4;++shard) {
      weights[shard].resize(window_bytes/16);
      for(unsigned j=0;j<window_bytes/16;++j) weights[shard][j]=read128(in);
    }
    std::vector<ap_uint<64> > expected(output_bytes/8);
    for(unsigned j=0;j<output_bytes/8;++j) expected[j]=read64(in);
    if(!in||in.peek()!=std::char_traits<char>::eof()) return 4;
    std::cout<<"M441_FULL_CASE_START ordinal="<<ordinal<<" groups="<<(config&255)
             <<" bits="<<((config>>8)&7)<<" descriptors="<<count
             <<" output_words="<<expected.size()<<std::endl;
    ap_uint<32> status=m89x_runtime_kernel(tx,weights[0].data(),weights[1].data(),weights[2].data(),weights[3].data(),rx,config);
    if(status!=0x4D343433U) {std::cerr<<"M441 wrong status "<<status<<std::endl;return 5;}
    for(unsigned j=0;j<expected.size();++j) {
      if(rx.empty()) {std::cerr<<"M441 short output "<<j<<std::endl;return 6;}
      m89_axis64_t item=rx.read();
      if(item.data!=expected[j]||item.keep!=0xff||item.strb!=0xff||bool(item.last)!=(j+1==expected.size())) {
        std::cerr<<"M441 full output mismatch ordinal="<<ordinal<<" word="<<j<<std::endl;return 7;
      }
    }
    if(!rx.empty()||!tx.empty()) return 8;
    total_words+=expected.size();
    std::cout<<"M441_FULL_CHAIN_PASS ordinal="<<ordinal<<" output_words="<<expected.size()<<std::endl;
  }
  std::cout<<"M441_FULL_TOTAL_OUTPUT_WORDS="<<total_words<<std::endl;
  std::cout<<"M441_FULL_REAL_WEIGHT_NUMERICAL_PASS"<<std::endl;
  return 0;
}
