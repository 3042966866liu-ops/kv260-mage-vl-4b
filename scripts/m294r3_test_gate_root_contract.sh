#!/usr/bin/env bash
set -euo pipefail

workspace=/mnt/c/Users/30429/Desktop/TeLLMe_FPGA_2026
gate=${workspace}/deployment/mage_vl4b/m294_counterbalanced_boundary_source/run_m294_counterbalanced_boundary_gate.sh
root=/home/ubuntu/tellme_m120_m89x2_20260901

check_accepted() {
  local name=$1
  local output rc
  set +e
  output=$(bash "${gate}" deadbeef deadbeef deadbeef 05 "${root}/${name}_05" 2>&1)
  rc=$?
  set -e
  [[ $rc -ne 0 ]]
  [[ $output != *M294_CANDIDATE_ROOT_INVALID* ]]
  [[ $output == *M294_ROOT_REQUIRED* ]]
}

check_accepted m294_counterbalanced_boundary_candidate
check_accepted m294r1_counterbalanced_boundary_candidate
check_accepted m294r3_counterbalanced_boundary_candidate

set +e
rejected=$(bash "${gate}" deadbeef deadbeef deadbeef 05 "${root}/unexpected_candidate_05" 2>&1)
rc=$?
set -e
[[ $rc -eq 2 ]]
[[ $rejected == *M294_CANDIDATE_ROOT_INVALID* ]]
echo M294R3_GATE_ROOT_CONTRACT_PASS accepted=3 rejected=1
