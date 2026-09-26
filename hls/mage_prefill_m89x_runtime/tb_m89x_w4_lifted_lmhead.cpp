#include "mage_prefill_m89x_runtime.hpp"
#include <hls_half.h>
#include <hls_math.h>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <string>

static unsigned u32(std::ifstream &in) {
  unsigned char b[4]; in.read((char*)b, 4);
  return unsigned(b[0]) | (unsigned(b[1]) << 8) |
         (unsigned(b[2]) << 16) | (unsigned(b[3]) << 24);
}
static ap_uint<128> word(std::ifstream &in) {
  unsigned char b[16]; in.read((char*)b, 16); ap_uint<128> value = 0;
  for (unsigned i=0; i<16; ++i) value.range(8*i+7,8*i)=b[i];
  return value;
}
static half bh(ap_uint<16> bits) { fp_struct<half> value(bits); return value.to_half(); }
static ap_uint<16> hb(half value) { fp_struct<half> bits(value); return bits.data(); }
static int activation(const ap_uint<128> value[5], unsigned lane) {
  ap_uint<8> raw=value[lane>>4].range(8*(lane&15)+7,8*(lane&15));
  return raw[7] ? int(raw)-256 : int(raw);
}
static int code4(const ap_uint<128>*record,unsigned row,unsigned lane) {
  unsigned base=1+row*2;
  if(lane<32)return int(record[base].range(4*lane+3,4*lane));
  return int(record[base+1].range(4*(lane-32)+3,4*(lane-32)));
}
static half golden(const ap_uint<128>*base,const ap_uint<128> act[40][32][5],
                   unsigned token,unsigned row) {
  half acc=(half)0.0f;
  for(unsigned group=0;group<40;++group){
    const ap_uint<128>*record=base+group*17;
    ap_uint<16>tag=record[0].range(16*row+15,16*row);
    int qmin=tag[15]?-7:-8,dot=0;
    for(unsigned lane=0;lane<64;++lane)
      dot+=activation(act[group][token],lane)*(qmin+code4(record,row,lane));
    half term=(half)((half)dot*bh(act[group][token][4].range(15,0)))*bh(tag&0x7fff);
    acc=(half)(acc+term);
  }
  return acc;
}

int main(){
  const char*path=std::getenv("M89Z2_FIXTURE_PATH"); if(!path)return 1;
  std::ifstream in(path,std::ios::binary); char magic[8];in.read(magic,8);
  if(!in||std::string(magic,8)!="M89Z2W41")return 2;
  unsigned groups=u32(in),bits=u32(in),rows=u32(in),tokens=u32(in),shards=u32(in),block=u32(in);
  if(groups!=40||bits!=4||rows!=8||tokens!=32||shards!=4||block!=1)return 3;
  static ap_uint<128> weights[4][680];
  static ap_uint<128> act[40][32][5];
  for(unsigned shard=0;shard<4;++shard)
    for(unsigned group=0;group<40;++group)
      for(unsigned z=0;z<17;++z)weights[shard][group*17+z]=word(in);
  for(unsigned group=0;group<40;++group)
    for(unsigned token=0;token<32;++token)
      for(unsigned z=0;z<5;++z)act[group][token][z]=word(in);
  if(!in)return 4;
  hls::stream<m89_axis128_t>tx;hls::stream<m89_axis64_t>rx;
  m89_axis128_t descriptor;descriptor.data=0;descriptor.data.range(41,32)=8;
  descriptor.data.range(44,42)=4;descriptor.keep=-1;descriptor.strb=-1;descriptor.last=0;tx.write(descriptor);
  for(unsigned group=0;group<40;++group)for(unsigned token=0;token<32;++token)
    for(unsigned z=0;z<5;++z){m89_axis128_t item;item.data=act[group][token][z];item.keep=-1;item.strb=-1;
      item.last=group==39&&token==31&&z==4;tx.write(item);}
  ap_uint<32>result=m89x_runtime_kernel(tx,weights[0],weights[1],weights[2],weights[3],rx,40|(4<<8)|(1<<16));
  if(result!=0x4D395831U)return 5;
  for(unsigned token=0;token<32;++token)for(unsigned shard=0;shard<4;++shard)
    for(unsigned pair=0;pair<4;++pair){m89_axis64_t item=rx.read();
      ap_uint<16>e0=hb(golden(weights[shard],act,token,2*pair));
      ap_uint<16>e1=hb(golden(weights[shard],act,token,2*pair+1));
      if(item.data.range(15,0)!=e0||item.data.range(47,32)!=e1)return 6;
      bool last=token==31&&shard==3&&pair==3;if(bool(item.last)!=last)return 7;}
  if(!rx.empty())return 8;
  std::cout<<"M89X_REAL_EXACT_LIFTED_W4_LMHEAD_CSIM_PASS\n";return 0;
}
