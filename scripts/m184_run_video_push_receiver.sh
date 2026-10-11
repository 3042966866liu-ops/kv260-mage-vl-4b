#!/usr/bin/env bash
set -euo pipefail

root=/home/ubuntu/tellme_m120_m89x2_20260901
bootstrap=$root/m184_bootstrap
destination=$root/m181_m120_video_board_candidate
result=$root/results/M184_M181_VIDEO_BOARD_IMPORT_RESULT.json
temporary_address=192.168.0.2/24
interface=eth0
added_address=0

finish() {
  rc=$?
  trap - EXIT
  if [[ $added_address -eq 1 ]]; then
    ip address del "$temporary_address" dev "$interface" || true
  fi
  echo "__M184_VIDEO_NETWORK_RUNNER_RC_${rc}__"
  exit "$rc"
}
trap finish EXIT

if [[ $(id -u) -ne 0 ]]; then
  echo M184_ROOT_REQUIRED >&2
  exit 1
fi
mkdir -p "$root/results"
if [[ $(cat /sys/class/net/$interface/carrier) != 1 ]]; then
  echo M184_ETHERNET_CARRIER_REQUIRED >&2
  exit 1
fi
if ! ip -4 address show dev "$interface" | grep -Fq '192.168.0.2/24'; then
  ip address add "$temporary_address" dev "$interface"
  added_address=1
fi
export PYTHONDONTWRITEBYTECODE=1
python3 "$bootstrap/m184_video_board_receiver.py" \
  --bind 192.168.0.2 --port 8767 \
  --destination "$destination" \
  --m182-result "$bootstrap/M182_M181_VIDEO_CANDIDATE_OFFLINE_GATE_RESULT.json" \
  --result "$result"
echo M184_M181_VIDEO_PUSH_RECEIVER_RUNNER_PASS
