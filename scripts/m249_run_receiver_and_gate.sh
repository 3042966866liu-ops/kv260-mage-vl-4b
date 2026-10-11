#!/usr/bin/env bash
set -euo pipefail

root=/home/ubuntu/tellme_m120_m89x2_20260901
bootstrap=$root/m249_bootstrap
candidate=$root/m249_ssdlite_board_candidate
import_result=$root/results/M249_SSDLITE_IMPORT_RESULT.json
temporary_address=192.168.0.2/24
interface=eth0
added_address=0

finish() {
  rc=$?
  trap - EXIT
  if [[ $added_address -eq 1 ]]; then
    ip address del "$temporary_address" dev "$interface" || true
  fi
  echo "__M249_NETWORK_RUNNER_RC_${rc}__"
  exit "$rc"
}
trap finish EXIT

if [[ $(id -u) -ne 0 ]]; then
  echo M249_ROOT_REQUIRED >&2
  exit 1
fi
mkdir -p "$root/results"
if [[ $(cat /sys/class/net/$interface/carrier) != 1 ]]; then
  echo M249_ETHERNET_CARRIER_REQUIRED >&2
  exit 1
fi
if ! ip -4 address show dev "$interface" | grep -Fq '192.168.0.2/24'; then
  ip address add "$temporary_address" dev "$interface"
  added_address=1
fi
export PYTHONDONTWRITEBYTECODE=1
/usr/bin/python3 "$bootstrap/m249_board_receiver.py" \
  --bind 192.168.0.2 --port 8769 \
  --destination "$candidate" --result "$import_result"
bash "$candidate/run_m249_board_gate.sh"
echo M249_RECEIVER_AND_BOARD_GATE_PASS
