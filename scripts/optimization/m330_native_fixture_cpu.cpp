// M330: native AArch64 CPU implementation of the frozen M128 W2/W4 fixture.
// CPU-only; never a substitute for the FPGA deployment gate.
#include <array>
#include <chrono>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

using Clock = std::chrono::steady_clock;
using Bytes = std::vector<uint8_t>;

static uint16_t u16(const uint8_t *p) { return uint16_t(p[0]) | (uint16_t(p[1]) << 8); }
static uint32_t u32(const uint8_t *p) {
  return uint32_t(p[0]) | (uint32_t(p[1]) << 8) | (uint32_t(p[2]) << 16) | (uint32_t(p[3]) << 24);
}
static uint32_t as_u32(float f) { uint32_t u; std::memcpy(&u, &f, 4); return u; }
static float as_float(uint32_t u) { float f; std::memcpy(&f, &u, 4); return f; }

static float half_to_float(uint16_t h) {
  uint32_t sign = uint32_t(h & 0x8000) << 16;
  uint32_t exp = (h >> 10) & 31;
  uint32_t frac = h & 1023;
  if (exp == 31) return as_float(sign | 0x7f800000 | (frac << 13));
  if (exp == 0) {
    if (frac == 0) return as_float(sign);
    int e = -14;
    while ((frac & 1024) == 0) { frac <<= 1; --e; }
    return as_float(sign | (uint32_t(e + 127) << 23) | ((frac & 1023) << 13));
  }
  return as_float(sign | ((exp + 112) << 23) | (frac << 13));
}

static uint16_t float_to_half(float value) {
  uint32_t x = as_u32(value), sign = (x >> 16) & 0x8000;
  uint32_t exponent = (x >> 23) & 255, fraction = x & 0x7fffff;
  if (exponent == 255) return uint16_t(sign | (fraction ? 0x7e00 : 0x7c00));
  int e = int(exponent) - 127 + 15;
  if (e >= 31) return uint16_t(sign | 0x7c00);
  if (e <= 0) {
    if (e < -10) return uint16_t(sign);
    uint32_t mantissa = fraction | 0x800000;
    int shift = 14 - e;
    uint32_t base = mantissa >> shift;
    uint32_t rem = mantissa & ((uint32_t(1) << shift) - 1);
    uint32_t halfway = uint32_t(1) << (shift - 1);
    if (rem > halfway || (rem == halfway && (base & 1))) ++base;
    return uint16_t(sign | base);
  }
  uint32_t base = fraction >> 13, rem = fraction & 8191;
  if (rem > 4096 || (rem == 4096 && (base & 1))) ++base;
  if (base == 1024) { base = 0; ++e; }
  if (e >= 31) return uint16_t(sign | 0x7c00);
  return uint16_t(sign | (uint32_t(e) << 10) | base);
}

struct Descriptor { std::array<const uint8_t *, 4> shard; uint8_t bits, words, groups; };
struct Case { uint32_t ordinal, groups, bits; std::vector<Descriptor> descriptors; const uint8_t *activation; };
struct Decoded { int8_t weights[8][64]; float scales[8]; };

static std::vector<Case> parse(const Bytes &file) {
  size_t cursor = 0;
  auto take = [&](size_t n) -> const uint8_t * {
    if (n > file.size() - cursor) throw std::runtime_error("fixture truncated");
    const uint8_t *p = file.data() + cursor; cursor += n; return p;
  };
  if (std::memcmp(take(8), "M128CSM1", 8)) throw std::runtime_error("fixture magic mismatch");
  const uint8_t *header = take(16);
  if (u32(header) != 7 || u32(header + 4) != 10 || u32(header + 8) != 32 || u32(header + 12) != 30)
    throw std::runtime_error("fixture header mismatch");
  std::vector<Case> cases;
  for (uint32_t ordinal = 0; ordinal < 7; ++ordinal) {
    const uint8_t *p = take(24);
    uint32_t count = u32(p + 12), groups = u32(p + 16), bits = u32(p + 20);
    if (u32(p) != ordinal || count < 1 || count > 10 || groups < 1 || groups > 255 || (bits != 2 && bits != 4))
      throw std::runtime_error("fixture case header mismatch");
    Case c{ordinal, groups, bits, {}, nullptr};
    for (uint32_t d = 0; d < count; ++d) {
      const uint8_t *q = take(8);
      Descriptor desc{{}, q[0], q[1], q[2]};
      if (desc.bits != bits || desc.words != 1 + 4 * bits || desc.groups != groups)
        throw std::runtime_error("fixture descriptor mismatch");
      for (int s = 0; s < 4; ++s) desc.shard[s] = take(size_t(groups) * 17 * 16);
      c.descriptors.push_back(desc);
    }
    c.activation = take(size_t(groups) * 32 * 80);
    cases.push_back(c);
  }
  if (cursor != file.size()) throw std::runtime_error("fixture trailing bytes");
  return cases;
}

static void decode(const uint8_t *record, int bits, int8_t (&weights)[8][64], float (&scales)[8]) {
  for (int row = 0; row < 8; ++row) {
    uint16_t tag = u16(record + 2 * row);
    scales[row] = half_to_float(tag & 0x7fff);
    int pair = row / 2, which = row % 2;
    int offset = bits == 2 ? ((tag & 0x8000) ? -1 : -2) : ((tag & 0x8000) ? -7 : -8);
    if (bits == 2) {
      const uint8_t *word = record + (1 + pair * 2 + which) * 16;
      for (int lane = 0; lane < 64; ++lane)
        weights[row][lane] = int8_t(((word[lane >> 2] >> ((lane & 3) * 2)) & 3) + offset);
    } else {
      const uint8_t *word = record + (1 + pair * 4 + which * 2) * 16;
      for (int lane = 0; lane < 64; ++lane)
        weights[row][lane] = int8_t(((word[lane >> 1] >> ((lane & 1) * 4)) & 15) + offset);
    }
  }
}

static std::vector<Decoded> predecode(const Case &c, size_t descriptor_count) {
  std::vector<Decoded> decoded(descriptor_count * c.groups * 4);
  for (size_t d = 0; d < descriptor_count; ++d)
    for (uint32_t g = 0; g < c.groups; ++g)
      for (int shard = 0; shard < 4; ++shard) {
        Decoded &value = decoded[(d * c.groups + g) * 4 + shard];
        decode(c.descriptors[d].shard[shard] + size_t(g) * 17 * 16,
               c.bits, value.weights, value.scales);
      }
  return decoded;
}

static Bytes calculate(const Case &c, size_t descriptor_count, const std::vector<Decoded> *predecoded) {
  if (descriptor_count < 1 || descriptor_count > c.descriptors.size()) throw std::runtime_error("bad descriptor count");
  Bytes output(descriptor_count * 32 * 4 * 4 * 8, 0);
  for (size_t d = 0; d < descriptor_count; ++d) {
    float acc[4][32][8] = {};
    for (uint32_t g = 0; g < c.groups; ++g) {
      for (int shard = 0; shard < 4; ++shard) {
        Decoded temporary;
        const Decoded *weight = nullptr;
        if (predecoded) {
          weight = &(*predecoded)[(d * c.groups + g) * 4 + shard];
        } else {
          decode(c.descriptors[d].shard[shard] + size_t(g) * 17 * 16,
                 c.bits, temporary.weights, temporary.scales);
          weight = &temporary;
        }
        for (int token = 0; token < 32; ++token) {
          const uint8_t *a = c.activation + (size_t(g) * 32 + token) * 80;
          float as = half_to_float(u16(a + 64));
          for (int row = 0; row < 8; ++row) {
            int32_t dot = 0;
            for (int lane = 0; lane < 64; ++lane)
              dot += int32_t(int8_t(a[lane])) * int32_t(weight->weights[row][lane]);
            float term = float(dot) * as;
            term = term * weight->scales[row];
            acc[shard][token][row] = acc[shard][token][row] + term;
          }
        }
      }
    }
    for (int token = 0; token < 32; ++token)
      for (int shard = 0; shard < 4; ++shard)
        for (int pair = 0; pair < 4; ++pair) {
          size_t pos = (((d * 32 + token) * 4 + shard) * 4 + pair) * 8;
          uint16_t lo = float_to_half(acc[shard][token][pair * 2]);
          uint16_t hi = float_to_half(acc[shard][token][pair * 2 + 1]);
          output[pos] = uint8_t(lo); output[pos + 1] = uint8_t(lo >> 8);
          output[pos + 4] = uint8_t(hi); output[pos + 5] = uint8_t(hi >> 8);
        }
  }
  return output;
}

int main(int argc, char **argv) {
  try {
    if (argc != 6 && argc != 7)
      throw std::runtime_error("usage: m330_native_fixture_cpu FIXTURE CASE DESCRIPTORS REPEATS OUTPUT [packed|predecoded]");
    std::ifstream input(argv[1], std::ios::binary);
    if (!input) throw std::runtime_error("fixture open failed");
    Bytes file((std::istreambuf_iterator<char>(input)), std::istreambuf_iterator<char>());
    auto cases = parse(file);
    int ordinal = std::stoi(argv[2]), descriptors = std::stoi(argv[3]), repeats = std::stoi(argv[4]);
    if (ordinal < 0 || ordinal >= int(cases.size()) || repeats < 1 || repeats > 20)
      throw std::runtime_error("case/repeat outside bounds");
    std::string mode = argc == 7 ? argv[6] : "packed";
    if (mode != "packed" && mode != "predecoded") throw std::runtime_error("unsupported mode");
    auto setup_start = Clock::now();
    std::vector<Decoded> decoded;
    if (mode == "predecoded") decoded = predecode(cases[ordinal], size_t(descriptors));
    double setup_ms = std::chrono::duration<double, std::milli>(Clock::now() - setup_start).count();
    std::cout << "M330_CPU_SETUP case=" << ordinal << " mode=" << mode << " ms=" << setup_ms
              << " predecoded_bytes=" << decoded.size() * sizeof(Decoded) << "\n";
    Bytes output;
    for (int i = 0; i < repeats; ++i) {
      auto start = Clock::now();
      Bytes current = calculate(cases[ordinal], size_t(descriptors), mode == "predecoded" ? &decoded : nullptr);
      double ms = std::chrono::duration<double, std::milli>(Clock::now() - start).count();
      if (i && current != output) throw std::runtime_error("repeat output mismatch");
      output = std::move(current);
      std::cout << "M330_CPU_RUN case=" << ordinal << " repeat=" << i << " ms=" << ms
                << " output_bytes=" << output.size() << "\n";
    }
    std::ofstream out(argv[5], std::ios::binary | std::ios::trunc);
    out.write(reinterpret_cast<const char *>(output.data()), std::streamsize(output.size()));
    if (!out) throw std::runtime_error("output write failed");
    std::cout << "M330_CPU_COMPLETE case=" << ordinal << "\n";
    return 0;
  } catch (const std::exception &e) {
    std::cerr << "M330_CPU_FAIL " << e.what() << "\n";
    return 1;
  }
}
