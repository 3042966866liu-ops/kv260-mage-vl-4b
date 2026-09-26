#!/usr/bin/env bash
set -euo pipefail

# CPU-only candidate. Never loads an overlay or mutates the stable installation.
root=/home/ubuntu/tellme_m330_native_cpu_20260926
runtime=/home/ubuntu/tellme_m120_m89x2_20260901/m120_text4b_board_candidate/runtime
fixture=/home/ubuntu/tellme_m120_m89x2_20260901/m120_text4b_board_candidate/reference/m128_m120_real_record_csim_fixture.bin
source_sha=5255437d244b62eb65560e17c3926fee3efde7d880968db5dcc76bb2f05ff506
verifier_sha=04c2a3c5451edc93372bc4cf79fd2c524ae8f74be88c1515d78d2a3ba8adc0ba
fixture_sha=f384f45eea4bc14110a7add49dd0944f0a025403aecc3360369ec999e28257d9
runtime_sha=6a7fb1f5377fd2ba09c8350ba557819a01348d8a96d44db7bd26e1dc1a3f871c
result_dir="$root/results"

mkdir -p "$result_dir"
on_exit() {
  local rc=$?
  if (( rc != 0 )); then
    printf '{"gate":"M330-native-A53-CPU","status":"FAIL","exit_code":%d,"note":"See immutable UART log and per-case result"}\n' "$rc" > "$result_dir/run_failure.json.partial"
    mv "$result_dir/run_failure.json.partial" "$result_dir/run_failure.json"
    printf 'M330_NATIVE_CPU_FAIL rc=%d result=%s\n' "$rc" "$result_dir/run_failure.json" >&2
  fi
}
trap on_exit EXIT

[[ $(id -u) -ne 0 ]] || { echo M330_REFUSE_ROOT >&2; exit 1; }
[[ ! -e "$result_dir/run_failure.json" ]] || { echo M330_REFUSE_PREVIOUS_FAILURE_OVERWRITE >&2; exit 1; }
[[ -z $(ss -H -ltn sport = :8001) ]] || { echo M330_REFUSE_ACTIVE_WEB_SERVICE >&2; exit 1; }
[[ -f "$root/m330_native_fixture_cpu.cpp" && -f "$root/m330_verify_native_fixture.py" ]] || { echo M330_MISSING_ASSET >&2; exit 1; }
[[ $(sha256sum "$root/m330_native_fixture_cpu.cpp" | cut -d' ' -f1) == "$source_sha" ]] || { echo M330_SOURCE_HASH_FAIL >&2; exit 1; }
[[ $(sha256sum "$root/m330_verify_native_fixture.py" | cut -d' ' -f1) == "$verifier_sha" ]] || { echo M330_VERIFIER_HASH_FAIL >&2; exit 1; }
[[ $(sha256sum "$fixture" | cut -d' ' -f1) == "$fixture_sha" ]] || { echo M330_FIXTURE_HASH_FAIL >&2; exit 1; }
[[ $(sha256sum "$runtime/m120_fixture.py" | cut -d' ' -f1) == "$runtime_sha" ]] || { echo M330_RUNTIME_HASH_FAIL >&2; exit 1; }

export PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
printf 'M330_COMPILER %s\n' "$(g++ --version | head -n1)"
printf 'M330_FLAGS -O3 -std=c++17 -ffp-contract=off -fno-fast-math -march=armv8-a+simd\n'
printf 'M330_AFFINITY core=1 threads=1\n'
g++ -O3 -std=c++17 -ffp-contract=off -fno-fast-math -march=armv8-a+simd \
  -o "$root/m330_native_fixture_cpu" "$root/m330_native_fixture_cpu.cpp"
sha256sum "$root/m330_native_fixture_cpu"

# Only two representative M329 cases are new: W2 and W4, each two descriptors.
# The other five numerical cases were already closed by M329 and are not repeated.
for mode in packed predecoded; do
  for ordinal in 0 1; do
    label="case_${ordinal}_${mode}"
    output="$result_dir/${label}.bin"
    log="$result_dir/${label}.log"
    result="$result_dir/${label}.json"
    [[ ! -e "$output" && ! -e "$log" && ! -e "$result" ]] || { echo "M330_REFUSE_OVERWRITE $label" >&2; exit 1; }
    taskset -c 1 "$root/m330_native_fixture_cpu" "$fixture" "$ordinal" 2 10 "$output" "$mode" > "$log"
    python3 "$root/m330_verify_native_fixture.py" \
      --fixture "$fixture" --runtime "$runtime" --case "$ordinal" \
      --descriptors 2 --repeats 10 --output "$output" --native-log "$log" --result "$result"
  done
done
printf 'M330_NATIVE_A53_NUMERICAL_PASS result_dir=%s\n' "$result_dir"
