#!/usr/bin/env bash
set -euo pipefail
root=/home/ubuntu/tellme_m120_m89x2_20260901
bootstrap=$root/m193_bootstrap
temporary_address=192.168.0.2/24
added=0
finish(){ rc=$?; trap - EXIT; if [[ $added -eq 1 ]]; then ip address del "$temporary_address" dev eth0 || true; fi; echo "__M193_RUNNER_RC_${rc}__"; exit "$rc"; }
trap finish EXIT
if [[ $(id -u) -ne 0 ]]; then echo M193_ROOT_REQUIRED >&2; exit 1; fi
if [[ $(cat /sys/class/net/eth0/carrier) != 1 ]]; then echo M193_ETHERNET_CARRIER_REQUIRED >&2; exit 1; fi
if ! ip -4 address show dev eth0 | grep -Fq '192.168.0.2/24'; then ip address add "$temporary_address" dev eth0; added=1; fi
export PYTHONDONTWRITEBYTECODE=1
/usr/bin/python3 "$bootstrap/m193_pillow_board_repair.py" --result "$root/results/M193_PILLOW_RUNTIME_REPAIR_RESULT.json"
