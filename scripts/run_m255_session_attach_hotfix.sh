#!/usr/bin/env bash
set -euo pipefail

root=/home/ubuntu/tellme_m120_m89x2_20260901
control=$root/m255_session_attach_control
current=$root/m254_dual_path_web_candidate
staging=$root/m254_dual_path_web_candidate_m255_staging
rollback=$root/m254_dual_path_web_candidate_r3_m255_rollback
result=$control/M255_SESSION_ATTACH_BOARD_RESULT_01.json
old_manifest=${1:?old manifest SHA-256 required}
new_manifest=${2:?new manifest SHA-256 required}
app_sha=${3:?app.js SHA-256 required}
verifier_sha=${4:?verifier SHA-256 required}
runner_sha=${5:?runner SHA-256 required}

finish(){ rc=$?; trap - EXIT; echo "__M255_RUNNER_RC_${rc}__"; exit "$rc"; }
trap finish EXIT

[[ $(sha256sum "$control/m255_verify_and_swap.py" | awk '{print $1}') == "$verifier_sha" ]] || { echo M255_VERIFIER_HASH_FAIL >&2; exit 1; }
[[ $(sha256sum "$control/run_m255_session_attach_hotfix.sh" | awk '{print $1}') == "$runner_sha" ]] || { echo M255_RUNNER_HASH_FAIL >&2; exit 1; }
[[ $(sha256sum "$control/PACKAGE_MANIFEST.json" | awk '{print $1}') == "$new_manifest" ]] || { echo M255_MANIFEST_PAYLOAD_HASH_FAIL >&2; exit 1; }
[[ $(sha256sum "$control/app.js" | awk '{print $1}') == "$app_sha" ]] || { echo M255_APP_PAYLOAD_HASH_FAIL >&2; exit 1; }
[[ $(sha256sum "$current/PACKAGE_MANIFEST.json" | awk '{print $1}') == "$old_manifest" ]] || { echo M255_ACTIVE_R3_IDENTITY_FAIL >&2; exit 1; }
[[ ! -e $staging && ! -e $rollback && ! -e $result ]] || { echo M255_CLEAN_PATHS_REQUIRED >&2; exit 1; }

cp -a "$current" "$staging"
install -m 0644 "$control/app.js" "$staging/static/app.js"
install -m 0644 "$control/PACKAGE_MANIFEST.json" "$staging/PACKAGE_MANIFEST.json"

python3 "$control/m255_verify_and_swap.py" \
  --current "$current" --staging "$staging" --rollback "$rollback" \
  --old-manifest-sha256 "$old_manifest" --new-manifest-sha256 "$new_manifest" \
  --app-js-sha256 "$app_sha" --result "$result"
grep -q '"status": "PASS"' "$result"
echo M255_SESSION_ATTACH_HOTFIX_RUNNER_PASS
