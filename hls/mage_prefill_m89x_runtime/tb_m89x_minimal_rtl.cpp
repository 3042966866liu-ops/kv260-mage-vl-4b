#include "mage_prefill_m89x_runtime.hpp"
#include <iostream>

int main() {
  // Match the synthesized m_axi depth exactly.  RTL CoSim's generated wrapper
  // copies the declared interface depth, so a 9-word C array is insufficient
  // even though this bounded test touches only its first nine words.
  static ap_uint<128> weights[4][524288];
  for (unsigned shard = 0; shard < 4; ++shard)
    for (unsigned word = 0; word < 9; ++word)
      weights[shard][word] = 0;

  hls::stream<m89_axis128_t> tx;
  hls::stream<m89_axis64_t> rx;
  m89_axis128_t descriptor;
  descriptor.data = 0;
  descriptor.data.range(41, 32) = 8;
  descriptor.data.range(44, 42) = 2;
  descriptor.keep = -1;
  descriptor.strb = -1;
  descriptor.last = 0;
  tx.write(descriptor);

  for (unsigned token = 0; token < 32; ++token)
    for (unsigned word = 0; word < 5; ++word) {
      m89_axis128_t item;
      item.data = 0;
      if (word == 4) item.data.range(15, 0) = 0x3c00;  // IEEE FP16 1.0
      item.keep = -1;
      item.strb = -1;
      item.last = token == 31 && word == 4;
      tx.write(item);
    }

  const ap_uint<32> config = 1U | (2U << 8) | (1U << 16);
  ap_uint<32> returned = m89x_runtime_kernel(
      tx, weights[0], weights[1], weights[2], weights[3], rx, config);
  if (returned != 0x4D395831U) {
    std::cerr << "M89X_MINIMAL_RETURN_FAIL value=0x" << std::hex
              << returned.to_uint() << std::dec << "\n";
    return 1;
  }
  for (unsigned index = 0; index < 512; ++index) {
    m89_axis64_t item = rx.read();
    if (item.data != 0 || bool(item.last) != (index == 511)) {
      std::cerr << "M89X_MINIMAL_OUTPUT_FAIL index=" << index << "\n";
      return 2;
    }
  }
  if (!rx.empty()) return 3;
  std::cout << "M89X_MINIMAL_RTL_TRANSACTION_PASS\n";
  return 0;
}
