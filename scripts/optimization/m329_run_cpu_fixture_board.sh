#!/usr/bin/env bash
set -euo pipefail

# CPU-only M329 diagnostic. No overlay load or service mutation is permitted.
root=/home/ubuntu/tellme_m329_cpu_reference_20260926
runtime=/home/ubuntu/tellme_m120_m89x2_20260901/m120_text4b_board_candidate/runtime
fixture=/home/ubuntu/tellme_m120_m89x2_20260901/m120_text4b_board_candidate/reference/m128_m120_real_record_csim_fixture.bin
result_dir="$root/results"
mkdir -p "$result_dir"
export PYTHONDONTWRITEBYTECODE=1

verify() {
  local path=$1 expected=$2 actual
  actual=$(sha256sum "$path")
  actual=${actual%% *}
  if [[ "$actual" != "$expected" ]]; then
    printf 'M329_HASH_FAIL path=%s expected=%s actual=%s\n' "$path" "$expected" "$actual" >&2
    exit 1
  fi
}

verify "$root/PACKAGE_MANIFEST.json" 2b5f4980dbca95bb277df181c7f973a4875b1a91030da748c1b5be9f62efe9fb
verify "$root/runtime/m329_cpu_fixture_baseline.py" 6e93d00587eb542ade6d63baae3550745f4a846ec35d26a4a44dfe5040c3f777
verify "$root/runtime/m120_group_reference.py" b275a71b67be281eea96c62b356ecdae91c2079e0ae22903704e26e32b1597c5
verify "$runtime/m120_fixture.py" 6a7fb1f5377fd2ba09c8350ba557819a01348d8a96d44db7bd26e1dc1a3f871c
verify "$fixture" f384f45eea4bc14110a7add49dd0944f0a025403aecc3360369ec999e28257d9

for case_spec in 0:2 1:2 2:2 3:10 4:2 5:4 6:10; do
  ordinal=${case_spec%%:*}
  descriptors=${case_spec##*:}
  result="$result_dir/case_${ordinal}.json"
  if [[ -e "$result" ]]; then
    printf 'M329_REFUSE_OVERWRITE %s\n' "$result" >&2
    exit 1
  fi
  set +e
  python3 "$root/runtime/m329_cpu_fixture_baseline.py" \
    --runtime-dir "$runtime" --fixture "$fixture" \
    --fixture-sha256 f384f45eea4bc14110a7add49dd0944f0a025403aecc3360369ec999e28257d9 \
    --case-ordinal "$ordinal" --descriptor-count "$descriptors" --repeat 3 \
    --result "$result"
  gate_rc=$?
  set -e
  if (( gate_rc != 0 )); then
    printf 'M329_CPU_CASE_FAIL ordinal=%s rc=%s result=%s\n' "$ordinal" "$gate_rc" "$result" >&2
    exit "$gate_rc"
  fi
done

printf 'M329_CPU_BOARD_NUMERICAL_PASS result_dir=%s\n' "$result_dir"
