#!/usr/bin/env bash
set -euo pipefail

# Isolated CPU-only microgate. Never loads an overlay or touches stable runtime.
package_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
result_dir="/home/ubuntu/m332_parser_scale_board_01"
python_bin="/usr/local/share/pynq-venv/bin/python"

cd "$package_dir"
sha256sum -c SHA256SUMS
test -x "$python_bin"
"$python_bin" -c 'import numpy; print("M332_NUMPY", numpy.__version__)'
mkdir -p "$result_dir"

started="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
set +e
taskset -c 1 "$python_bin" "$package_dir/m332_parser_scale_bench.py" \
  --repeat 15 --warmup 3 --shift 4 \
  --output "$result_dir/RESULT.json.partial" \
  > "$result_dir/stdout.log" 2> "$result_dir/stderr.log"
gate_rc=$?
set -e
if (( gate_rc != 0 )); then
  printf 'M332_BOARD_MICRO_FAIL rc=%s started=%s stderr=%s\n' \
    "$gate_rc" "$started" "$result_dir/stderr.log"
  exit "$gate_rc"
fi

mv "$result_dir/RESULT.json.partial" "$result_dir/RESULT.json"
"$python_bin" - "$result_dir/RESULT.json" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as stream:
    result = json.load(stream)
cases = result["cases"]
speedups = [case["baseline_median_ms"] / case["candidate_median_ms"] for case in cases]
no_regression = all(case["candidate_median_ms"] <= case["baseline_median_ms"] * 1.05 for case in cases)
numerical = result["status"] == "PASS_MICROGATE_NOT_VIDEO" and all(case["complete_output_bit_exact"] for case in cases)
trigger = numerical and sum(speedup >= 1.2 for speedup in speedups) >= 2 and no_regression
print("M332_BOARD_MICRO_NUMERICAL=" + ("PASS" if numerical else "FAIL"))
print("M332_BOARD_MICRO_SPEEDUPS=" + ",".join(f"{speedup:.4f}" for speedup in speedups))
print("M332_BOARD_MICRO_VIDEO_TRIGGER=" + ("PASS" if trigger else "FAIL"))
PY
sha256sum "$result_dir/RESULT.json"
printf 'M332_BOARD_MICRO_DONE started=%s finished=%s result=%s\n' \
  "$started" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$result_dir/RESULT.json"
