#include "mage_m86_activation_prefetch.hpp"
#include "mage_m84_three_shard_lane.hpp"
#define M84_EXPECT_BUILD_ID M86_EXPECT_BUILD_ID
#define mage_m84_three_shard_lane mage_m86_activation_prefetch
#include "tb_mage_m84_three_shard_lane.cpp"
