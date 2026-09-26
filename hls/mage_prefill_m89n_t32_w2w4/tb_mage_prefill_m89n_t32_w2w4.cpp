#include "../mage_prefill_m89d_t32_microtile/mage_prefill_m89d_t32_microtile.hpp"
#include <iostream>
#include <random>

void m89n_t32_w2w4(hls::stream<m89_axis128_t> &, const ap_uint<128> *, const ap_uint<128> *, const ap_uint<128> *, const ap_uint<128> *, const ap_uint<128> *, const ap_uint<128> *, hls::stream<m89_axis64_t> &, unsigned, unsigned, unsigned, ap_uint<32> &, ap_uint<32> &, ap_uint<32> &, ap_uint<32> &);

static void set_code(ap_uint<128> &low, ap_uint<128> &high, unsigned lane, unsigned bits, unsigned value) {
    if (bits == 2) low.range(2 * lane + 1, 2 * lane) = value;
    else if (lane < 32) low.range(4 * lane + 3, 4 * lane) = value;
    else high.range(4 * (lane - 32) + 3, 4 * (lane - 32)) = value;
}
static int minimum(unsigned bits, bool orientation) { const int half=1<<(bits-1); return orientation ? -half+1 : -half; }

static int run(unsigned bits) {
    const unsigned groups=3, rows=16, blocks=2, words=1+4*bits;
    static ap_uint<128> memory[M89_SHARDS][M89_MAX_GROUPS*(M89_MAX_ROWS_PER_SHARD/8)*17];
    static ap_int<8> activation[groups][M89_TOKEN_LANES][M89_GROUP_SIZE];
    static int expected[M89_TOKEN_LANES][M89_SHARDS][rows];
    hls::stream<m89_axis128_t> tx; hls::stream<m89_axis64_t> rx;
    std::mt19937 rng(0x4d38394eU+bits); std::uniform_int_distribution<int> act(-31,31), code(0,(1<<bits)-1), flag(0,1);
    for(unsigned g=0;g<groups;++g) for(unsigned t=0;t<M89_TOKEN_LANES;++t) {
        for(unsigned l=0;l<M89_GROUP_SIZE;++l) activation[g][t][l]=act(rng);
        for(unsigned word=0;word<4;++word){m89_axis128_t item;item.data=0;for(unsigned b=0;b<16;++b)item.data.range(8*b+7,8*b)=(ap_uint<8>)activation[g][t][16*word+b];item.keep=-1;item.strb=-1;item.last=g+1==groups&&t+1==M89_TOKEN_LANES&&word==3;tx.write(item);}
    }
    for(unsigned t=0;t<M89_TOKEN_LANES;++t)for(unsigned s=0;s<M89_SHARDS;++s)for(unsigned r=0;r<rows;++r)expected[t][s][r]=0;
    for(unsigned s=0;s<M89_SHARDS;++s)for(unsigned g=0;g<groups;++g)for(unsigned block=0;block<blocks;++block){
        const unsigned base=g*blocks*words+block*words; ap_uint<128> scale=0; bool orient[8]; for(unsigned r=0;r<8;++r){orient[r]=flag(rng);scale.range(16*r+15,16*r)=(ap_uint<16>)orient[r]<<15;} memory[s][base]=scale;
        for(unsigned pair=0;pair<4;++pair){ap_uint<128> lo0=0,hi0=0,lo1=0,hi1=0;for(unsigned lane=0;lane<M89_GROUP_SIZE;++lane){const int c0=code(rng),c1=code(rng);set_code(lo0,hi0,lane,bits,c0);set_code(lo1,hi1,lane,bits,c1);for(unsigned t=0;t<M89_TOKEN_LANES;++t){expected[t][s][8*block+2*pair]+=activation[g][t][lane]*(minimum(bits,orient[2*pair])+c0);expected[t][s][8*block+2*pair+1]+=activation[g][t][lane]*(minimum(bits,orient[2*pair+1])+c1);}}
            const unsigned p=base+1+pair*bits; memory[s][p]=lo0; if(bits==4)memory[s][p+1]=hi0; memory[s][p+bits/2]=lo1; if(bits==4)memory[s][p+bits/2+1]=hi1;}
    }
    ap_uint<32> status=0,build=0,calls=0,macros=0;m89n_t32_w2w4(tx,memory[0],memory[1],memory[2],memory[3],memory[4],memory[5],rx,groups,rows,bits,status,build,calls,macros);
    // The W2 and W4 subtests share the kernel's persistent diagnostic
    // counters, so only require a nonzero call count here.  The per-call MAC
    // increment is checked by its monotonic value rather than pretending both
    // invocations are the first one.
    if(status||build!=0x4D38394EU||calls<1||macros<groups*rows*M89_SHARDS*M89_TOKEN_LANES){std::cerr<<"status failure bits="<<bits<<" status="<<status<<" build="<<build<<" calls="<<calls<<" macros="<<macros<<std::endl;return 1;}
    for(unsigned block=0;block<blocks;++block)for(unsigned t=0;t<M89_TOKEN_LANES;++t)for(unsigned s=0;s<M89_SHARDS;++s)for(unsigned pair=0;pair<4;++pair){const m89_axis64_t item=rx.read();const unsigned row=8*block+2*pair;const int got0=(int)(ap_int<32>)item.data.range(31,0),got1=(int)(ap_int<32>)item.data.range(63,32);if(got0!=expected[t][s][row]||got1!=expected[t][s][row+1]){std::cerr<<"dot failure bits="<<bits<<" block="<<block<<" token="<<t<<" shard="<<s<<" pair="<<pair<<" got="<<got0<<","<<got1<<" expected="<<expected[t][s][row]<<","<<expected[t][s][row+1]<<std::endl;return 1;}}
    if(!rx.empty()){std::cerr<<"leftover bits="<<bits<<std::endl;return 1;}return 0;
}
int main(){if(run(2)||run(4))return 1;std::cout<<"M89N_T32_W2W4_CSIM_PASS bits=2,4 tokens=32"<<std::endl;return 0;}
