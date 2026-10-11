#!/usr/bin/env bash
set -euo pipefail

root=/home/ubuntu/tellme_m120_m89x2_20260901
bootstrap=$root/m155_bootstrap
mountpoint=/mnt/tellme_m120_usb
source_root=$mountpoint/tellme_m120_fulltext_0x4D395832
destination=$root/m120_fulltext_weights_0x4D395832
m140=$bootstrap/M140_M120_SINGLE_CHAIN_BOARD_RESULT_01.json
result=$root/results/M155_M120_FULLTEXT_USB_BOARD_IMPORT_RESULT.json
mounted_here=0

finish() {
  rc=$?
  trap - EXIT
  if [[ $mounted_here -eq 1 ]]; then
    umount "$mountpoint" || true
  fi
  echo "__M155_USB_IMPORT_RC_${rc}__"
  exit "$rc"
}
trap finish EXIT

if [[ $(id -u) -ne 0 ]]; then
  echo M155_ROOT_REQUIRED >&2
  exit 1
fi
if [[ ! -f "$m140" ]]; then
  echo M155_M140_RESULT_MISSING >&2
  exit 1
fi
mapfile -t devices < <(lsblk -nrpo NAME,TYPE,TRAN,FSTYPE | awk '$2 == "part" && $3 == "usb" && $4 != "" {print $1}')
if [[ ${#devices[@]} -ne 1 ]]; then
  echo "M155_USB_PARTITION_IDENTITY_FAIL count=${#devices[@]} devices=${devices[*]-}" >&2
  exit 1
fi
if findmnt -rn -S "${devices[0]}" >/dev/null; then
  echo "M155_USB_ALREADY_MOUNTED_REFUSED device=${devices[0]}" >&2
  exit 1
fi
mkdir -p "$mountpoint" "$root/results"
mount -o ro,nodev,nosuid,noexec "${devices[0]}" "$mountpoint"
mounted_here=1
if [[ ! -f "$source_root/USB_READY.json" ]]; then
  echo M155_USB_READY_MISSING >&2
  exit 1
fi

python3 "$bootstrap/m155_m120_usb_board_import.py" \
  --usb-root "$source_root" \
  --destination "$destination" \
  --m140-result "$m140" \
  --result "$result"

echo __M155_RESULT_BEGIN__
cat "$result"
echo __M155_RESULT_END__
echo M155_M120_USB_BOARD_IMPORT_RUNNER_PASS
