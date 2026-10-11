#!/usr/bin/env bash
set -euo pipefail

root=/home/ubuntu/tellme_m120_m89x2_20260901
bootstrap=$root/m162_bootstrap_v2
destination=$root/m120_fulltext_weights_0x4D395832
result=$root/results/M162_M120_NETWORK_BOARD_IMPORT_RESULT.json
temporary_address=192.168.0.2/24
interface=eth0
added_address=0

finish() {
  rc=$?
  trap - EXIT
  if [[ $added_address -eq 1 ]]; then
    ip address del "$temporary_address" dev "$interface" || true
  fi
  echo "__M162_NETWORK_RUNNER_RC_${rc}__"
  exit "$rc"
}
trap finish EXIT

if [[ $(id -u) -ne 0 ]]; then
  echo M162_ROOT_REQUIRED >&2
  exit 1
fi
mkdir -p "$root/results"
if [[ $(cat /sys/class/net/$interface/carrier) != 1 ]]; then
  echo M162_ETHERNET_CARRIER_REQUIRED >&2
  exit 1
fi
if ! ip -4 address show dev "$interface" | grep -Fq '192.168.0.2/24'; then
  ip address add "$temporary_address" dev "$interface"
  added_address=1
fi
python3 "$bootstrap/m162_m120_network_board_import.py" \
  --base-url http://192.168.0.10:8765/tellme_m120_fulltext_0x4D395832 \
  --destination "$destination" \
  --m140-result "$bootstrap/M140_M120_SINGLE_CHAIN_BOARD_RESULT_01.json" \
  --result "$result"

echo M162_M120_NETWORK_IMPORT_RUNNER_PASS
