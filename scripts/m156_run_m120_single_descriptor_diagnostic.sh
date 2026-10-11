#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 5 ]]; then
  echo "usage: $0 CANDIDATE DIAGNOSTIC RESULT_DIR EXPECTED_PACKAGE_MANIFEST_SHA256 EXPECTED_DIAGNOSTIC_SHA256" >&2
  exit 2
fi
candidate=$1
diagnostic=$2
result_dir=$3
expected_manifest=$4
expected_diagnostic=$5

export XILINX_XRT=/usr
export TMPDIR=/dev/shm
export PATH=/usr/local/share/pynq-venv/bin:/usr/local/bin:/usr/bin:/bin
export PYTHONDONTWRITEBYTECODE=1
mkdir -p "$result_dir"

observed=$(sha256sum "$diagnostic" | awk '{print $1}')
if [[ "$observed" != "$expected_diagnostic" ]]; then
  echo "M156_DIAGNOSTIC_HASH_FAIL expected=$expected_diagnostic observed=$observed" >&2
  exit 1
fi
python3 "$candidate/runtime/m120_board_env_preflight.py" \
  --candidate "$candidate" \
  --expected-package-manifest-sha256 "$expected_manifest" \
  --result "$result_dir/environment.json"
python3 "$diagnostic" --candidate "$candidate" --result "$result_dir/diagnostic.json"
echo __M156_RESULT_BEGIN__
cat "$result_dir/diagnostic.json"
echo __M156_RESULT_END__
echo M156_M120_SINGLE_DESCRIPTOR_RUNNER_PASS
