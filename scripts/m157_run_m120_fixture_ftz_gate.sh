#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 8 ]]; then
  echo "usage: $0 CANDIDATE GATE LEVEL POLICY RESULT_DIR MANIFEST_SHA GATE_SHA POLICY_SHA" >&2
  exit 2
fi
candidate=$1
gate=$2
level=$3
policy=$4
result_dir=$5
manifest=$6
gate_sha=$7
policy_sha=$8

export XILINX_XRT=/usr
export TMPDIR=/dev/shm
export PATH=/usr/local/share/pynq-venv/bin:/usr/local/bin:/usr/bin:/bin
export PYTHONDONTWRITEBYTECODE=1
mkdir -p "$result_dir"
[[ $(sha256sum "$gate" | awk '{print $1}') == "$gate_sha" ]] || { echo M157_GATE_HASH_FAIL >&2; exit 1; }
[[ $(sha256sum "$policy" | awk '{print $1}') == "$policy_sha" ]] || { echo M157_POLICY_HASH_FAIL >&2; exit 1; }
python3 "$candidate/runtime/m120_board_env_preflight.py" --candidate "$candidate" \
  --expected-package-manifest-sha256 "$manifest" --result "$result_dir/environment.json"
python3 "$gate" --candidate "$candidate" --level "$level" --policy "$policy" --result "$result_dir/measurement.json"
echo __M157_RESULT_BEGIN__
cat "$result_dir/measurement.json"
echo __M157_RESULT_END__
echo M157_M120_FIXTURE_FTZ_RUNNER_PASS
