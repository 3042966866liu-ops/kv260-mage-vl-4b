#!/usr/bin/env bash
set -euo pipefail
root=/home/ubuntu/tellme_m120_m89x2_20260901
gate=$root/m212_live_delta
video=$root/m181_m120_video_board_candidate
text=$root/m175_m120_fixed_text_candidate
weights=$root/m120_fulltext_weights_0x4D395832
result_dir=$root/results/m212_live_service_01
formal=$root/results/M212_LIVE_SERVICE_BOARD_RESULT_01.json
text_manifest=406dcca340e4604baeb761445795391c43ec26bd99fa06ffae893d597b17414f
package_manifest_sha256=${1:?M212 package manifest SHA-256 required}
finish(){ rc=$?; trap - EXIT; echo "__M212_LIVE_RUNNER_RC_${rc}__"; exit "$rc"; }
trap finish EXIT
[[ $(id -u) -eq 0 ]] || { echo M212_ROOT_REQUIRED >&2; exit 1; }
[[ ! -e $formal ]] || { echo M212_FORMAL_RESULT_ALREADY_EXISTS >&2; exit 1; }
mkdir -p "$result_dir"
export XILINX_XRT=/usr TMPDIR=/dev/shm PYTHONDONTWRITEBYTECODE=1 TRANSFORMERS_OFFLINE=1 HF_HUB_OFFLINE=1
export PATH=/usr/local/share/pynq-venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export PYTHONPATH=$gate:$video:$root/m190_mage_runtime
/usr/local/share/pynq-venv/bin/python "$gate/m212_verify_board_delta.py" --root "$gate" --expected-manifest-sha256 "$package_manifest_sha256"
/usr/local/share/pynq-venv/bin/python "$text/runtime/m120_board_env_preflight.py" --candidate "$text" --expected-package-manifest-sha256 "$text_manifest" --result "$result_dir/environment.json"
/usr/local/share/pynq-venv/bin/python "$gate/video_server.py" --candidate "$video" --text-candidate "$text" --weights-root "$weights" --board-gate "$gate/M212_PREDECESSOR_SUMMARY.json" --preflight --result "$result_dir/service_preflight.json"
if [[ -e $root/results/m212_live_service.pid ]]; then echo M212_SERVICE_PID_ALREADY_EXISTS >&2; exit 1; fi
if ! ip -4 addr show dev eth0 | grep -q '192.168.0.2/24'; then ip addr add 192.168.0.2/24 dev eth0; echo added > "$result_dir/temporary_ip_state"; else echo existing > "$result_dir/temporary_ip_state"; fi
M200_STATIC_ROOT=$gate/static nohup /usr/local/share/pynq-venv/bin/python "$gate/video_server.py" --candidate "$video" --text-candidate "$text" --weights-root "$weights" --board-gate "$gate/M212_PREDECESSOR_SUMMARY.json" --host 0.0.0.0 --port 8001 > "$root/results/m212_live_service.log" 2>&1 &
pid=$!
echo "$pid" > "$root/results/m212_live_service.pid"
/usr/local/share/pynq-venv/bin/python "$gate/m212_health_probe.py" --url http://127.0.0.1:8001/api/health --preflight "$result_dir/service_preflight.json" --package-manifest-sha256 "$package_manifest_sha256" --pid "$pid" --result "$formal"
echo M212_LIVE_SERVICE_BOARD_START_PASS
