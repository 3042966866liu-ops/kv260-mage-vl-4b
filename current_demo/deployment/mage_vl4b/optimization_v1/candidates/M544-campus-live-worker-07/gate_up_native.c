/* M455 dense wire -> final FP32; software parser only, no device APIs.
 * Integer exponent scaling is exact for half inputs / shifts 0..10: even
 * the smallest half subnormal produces a normal FP32 result. No FP mode,
 * fast-math, rounding, FTZ, or NaN canonicalization dependency is introduced. */
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#if defined(__aarch64__)
#include <arm_neon.h>
#endif

uint32_t m455_parser_abi(void) { return 0x20261024u; }
int m455_parser_neon(void) {
#if defined(__aarch64__)
    return 1;
#else
    return 0;
#endif
}

static inline uint32_t expand(uint16_t h, unsigned shift) {
    uint32_t sign=((uint32_t)h & 0x8000u)<<16;
    uint32_t exponent=(h>>10)&31u, mantissa=h&1023u;
    if (exponent==31u) {
        /* NumPy half->float preserves signaling payload for copy/shift0;
         * ldexp quiets it for shifts 1..10. Nonfinite return remains false. */
        return sign|0x7f800000u|(mantissa<<13)|((shift && mantissa)?0x00400000u:0u);
    }
    if (!exponent) {
        if (!mantissa) return sign;
        unsigned leading=0;
        while (!(mantissa&1024u)) { mantissa<<=1; ++leading; }
        return sign|((113u-leading-shift)<<23)|((mantissa&1023u)<<13);
    }
    return sign|((exponent+112u-shift)<<23)|(mantissa<<13);
}

/* Returns 1 finite, 0 nonfinite, -1 invalid metadata (before any write).
 * dst points to the already validated logical token_start / row_start slice.
 * Source layout: block(8 channels), token(32), shard(4), pair/lane(8).
 * Destination supports positive byte strides, as does the original parser. */
int m455_parse_descriptor(const uint8_t *src, size_t src_bytes,
    uint8_t *dst, size_t dst_row_stride, size_t dst_col_stride,
    unsigned rows, unsigned valid, unsigned tokens, unsigned shift) {
    if (!src || !dst || !rows || rows>4096u || rows%8u ||
        src_bytes!=(size_t)rows*256u || !valid || valid>rows*4u ||
        !tokens || tokens>32u || shift>10u || !dst_row_stride || !dst_col_stride ||
        dst_row_stride>SIZE_MAX/32u || dst_col_stride>SIZE_MAX/16384u) return -1;
    int finite=1;
    for (unsigned t=0;t<tokens;++t) {
        for (unsigned shard=0;shard<4;++shard) {
            unsigned offset=shard*rows;
            unsigned count=valid>offset?valid-offset:0u;
            if (count>rows) count=rows;
            for (unsigned c=0;c<count;c+=8) {
                const uint8_t *s=src+(size_t)(c/8u)*2048u+t*64u+shard*16u;
                uint8_t *d=dst+(size_t)t*dst_row_stride+(offset+c)*dst_col_stride;
                unsigned n=count-c;if(n>8u)n=8u;
#if defined(__aarch64__)
                if (n==8u && dst_col_stride==4u) {
                    uint16x8_t h=vld1q_u16((const uint16_t *)s);
                    uint16x8_t e=vandq_u16(vshrq_n_u16(h,10),vdupq_n_u16(31));
                    uint16x8_t m=vandq_u16(h,vdupq_n_u16(1023));
                    uint16x8_t special=vorrq_u16(vceqq_u16(e,vdupq_n_u16(31)),
                        vandq_u16(vceqq_u16(e,vdupq_n_u16(0)),vcgtq_u16(m,vdupq_n_u16(0))));
                    if (!vmaxvq_u16(special)) {
                        for(unsigned k=0;k<2;++k) {
                            uint32x4_t x=vmovl_u16(k?vget_high_u16(h):vget_low_u16(h));
                            uint32x4_t ex=vandq_u32(vshrq_n_u32(x,10),vdupq_n_u32(31));
                            uint32x4_t sign=vshlq_n_u32(vandq_u32(x,vdupq_n_u32(0x8000)),16);
                            uint32x4_t bits=vorrq_u32(sign,vorrq_u32(
                                vshlq_n_u32(vaddq_u32(ex,vdupq_n_u32(112u-shift)),23),
                                vshlq_n_u32(vandq_u32(x,vdupq_n_u32(1023)),13)));
                            bits=vbslq_u32(vceqq_u32(ex,vdupq_n_u32(0)),sign,bits);
                            vst1q_u8(d+k*16u,vreinterpretq_u8_u32(bits));
                        }
                        continue;
                    }
                }
#endif
                for(unsigned j=0;j<n;++j) {
                    uint16_t h;memcpy(&h,s+j*2u,2);
                    if ((h&0x7c00u)==0x7c00u) finite=0;
                    uint32_t bits=expand(h,shift);memcpy(d+j*dst_col_stride,&bits,4);
                }
            }
        }
    }
    return finite;
}
