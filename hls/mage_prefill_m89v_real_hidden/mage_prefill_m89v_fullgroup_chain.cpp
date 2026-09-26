// Keep the verified M89-T source unchanged at its default 40-group geometry.
// This candidate specializes the same arithmetic/control path for the largest
// real Mage-VL language input (9728 / 64 = 152 groups).
#define M89_MAX_GROUPS_VALUE 152
#define m89t_scale_chain m89v_fullgroup_chain
#include "../mage_prefill_m89t_scale_chain/mage_prefill_m89t_scale_chain.cpp"
#undef m89t_scale_chain
#undef M89_MAX_GROUPS_VALUE
