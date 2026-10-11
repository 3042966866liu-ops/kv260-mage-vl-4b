#include "../mage_prefill_m89d_t32_microtile/mage_prefill_m89d_t32_microtile.hpp"
#include <cstdlib>
#include <fstream>
#include <iostream>

void m89r_chain(hls::stream<m89_axis128_t>&,const ap_uint<128>*,const ap_uint<128>*,
                const ap_uint<128>*,const ap_uint<128>*,const ap_uint<128>*,
                hls::stream<m89_axis64_t>&,unsigned,unsigned,ap_uint<32>&,ap_uint<32>&,
                ap_uint<32>&,ap_uint<32>&,ap_uint<32>&);

static unsigned u32(std::ifstream&in){unsigned char b[4];in.read((char*)b,4);return unsigned(b[0])|(unsigned(b[1])<<8)|(unsigned(b[2])<<16)|(unsigned(b[3])<<24);}
static ap_uint<128> word(std::ifstream&in){unsigned char b[16];in.read((char*)b,16);ap_uint<128>w=0;for(unsigned i=0;i<16;++i)w.range(8*i+7,8*i)=b[i];return w;}
static int act(unsigned c,unsigned t,unsigned l){return int((c*19+t*7+l*5+11)%63)-31;}
static int code(const ap_uint<128>*r,unsigned bits,unsigned row,unsigned lane){unsigned p=row>>1,w=row&1;if(bits==2)return int(r[1+p*2+w].range(2*lane+1,2*lane));unsigned z=lane&31;return int(r[1+p*4+w*2+(lane>=32)].range(4*z+3,4*z));}
static int gold(const ap_uint<128>*r,unsigned bits,unsigned c,unsigned t,unsigned row){ap_uint<16>tag=r[0].range(16*row+15,16*row);int h=1<<(bits-1),q=tag[15]?-h+1:-h,sum=0;for(unsigned l=0;l<64;++l)sum+=act(c,t,l)*(q+code(r,bits,row,l));return sum;}

int main(){const char*path=std::getenv("M89R_FIXTURE_PATH");if(!path)return 1;std::ifstream in(path,std::ios::binary);char magic[8];in.read(magic,8);if(!in||std::string(magic,8)!="M89RCHN1")return 2;unsigned chains=u32(in),max_chain=u32(in);if(chains!=144||max_chain!=10)return 3;
 for(unsigned chain=0;chain<chains;++chain){unsigned chain_id=u32(in),count=u32(in);if(chain_id!=chain||count<1||count>10)return 4;static ap_uint<128>w[4][170];ap_uint<128>d[10];unsigned bits[10];for(unsigned i=0;i<count;++i){unsigned char h[4];in.read((char*)h,4);bits[i]=h[0];unsigned words=h[1];if(words!=1+4*bits[i])return 5;unsigned off=i*17;d[i]=0;d[i].range(31,0)=off;d[i].range(41,32)=8;d[i].range(44,42)=bits[i];for(unsigned s=0;s<4;++s)for(unsigned z=0;z<17;++z)w[s][off+z]=word(in);}if(!in)return 6;
  hls::stream<m89_axis128_t>tx;hls::stream<m89_axis64_t>rx;for(unsigned t=0;t<32;++t)for(unsigned z=0;z<4;++z){m89_axis128_t a;a.data=0;a.keep=-1;a.strb=-1;for(unsigned b=0;b<16;++b)a.data.range(8*b+7,8*b)=ap_uint<8>(act(chain,t,16*z+b));a.last=t==31&&z==3;tx.write(a);}ap_uint<32>st,bu,ca,done,ma;m89r_chain(tx,d,w[0],w[1],w[2],w[3],rx,1,count,st,bu,ca,done,ma);if(st||bu!=0x4D383952U||ca!=1||done!=count||ma!=count*1024)return 7;
  for(unsigned i=0;i<count;++i)for(unsigned t=0;t<32;++t)for(unsigned s=0;s<4;++s)for(unsigned p=0;p<4;++p){m89_axis64_t o=rx.read();const ap_uint<128>*r=&w[s][i*17];if(int(ap_int<32>(o.data.range(31,0)))!=gold(r,bits[i],chain,t,2*p)||int(ap_int<32>(o.data.range(63,32)))!=gold(r,bits[i],chain,t,2*p+1))return 8;bool last=i+1==count&&t==31&&s==3&&p==3;if(bool(o.last)!=last)return 9;}if(!rx.empty())return 10;}
 std::cout<<"M89R_REAL_M56_144_CHAINS_252_MODULES_CSIM_PASS\n";return 0;}
