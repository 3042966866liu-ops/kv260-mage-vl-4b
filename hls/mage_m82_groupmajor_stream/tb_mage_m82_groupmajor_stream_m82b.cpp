// Compile the exact M82-A golden test against the M82-B top without copying
// the test vector or weakening its bit-level checks.
#include "mage_m82_groupmajor_stream_m82b.hpp"
#define M82A_BUILD_ID M82B_EXPECT_BUILD_ID
#define mage_m82_groupmajor_stream mage_m82_groupmajor_stream_m82b
#include "tb_mage_m82_groupmajor_stream.cpp"
