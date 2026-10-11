#!/usr/bin/env bash
set -euo pipefail

root=/home/ubuntu/tellme_m120_m89x2_20260901
bootstrap=$root/m190_bootstrap
result=$root/results/M190_ARM64_MAGE_RUNTIME_INSTALL_RESULT.json
temporary_address=192.168.0.2/24
interface=eth0
added_address=0

finish() {
  rc=$?
  trap - EXIT
  if [[ $added_address -eq 1 ]]; then
    ip address del "$temporary_address" dev "$interface" || true
  fi
  echo "__M190_RUNTIME_RUNNER_RC_${rc}__"
  exit "$rc"
}
trap finish EXIT

if [[ $(id -u) -ne 0 ]]; then
  echo M190_ROOT_REQUIRED >&2
  exit 1
fi
mkdir -p "$root/results"
if [[ $(cat /sys/class/net/$interface/carrier) != 1 ]]; then
  echo M190_ETHERNET_CARRIER_REQUIRED >&2
  exit 1
fi
if ! ip -4 address show dev "$interface" | grep -Fq '192.168.0.2/24'; then
  ip address add "$temporary_address" dev "$interface"
  added_address=1
fi
export PYTHONDONTWRITEBYTECODE=1
/usr/bin/python3 "$bootstrap/m190_runtime_board_receiver.py" --bind 192.168.0.2 --port 8768 --result "$result"
echo M190_ARM64_RUNTIME_RECEIVER_RUNNER_PASS
