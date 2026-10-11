#!/usr/bin/env bash
set -euo pipefail

WORKSPACE_WIN_MOUNT=/mnt/c/Users/30429/Desktop/TeLLMe_FPGA_2026
KEY_SOURCE="$WORKSPACE_WIN_MOUNT/tmp/m2_ssh/id_ed25519"
BOARD=ubuntu@192.168.0.2
REMOTE_ROOT=/home/ubuntu/tellme_mage_m75c_full_20260829_01
LANGUAGE_SRC=/home/lyy/artifacts/tellme-mage-vl/m60-language-high1664/
HEAD_SRC=/home/lyy/artifacts/tellme-mage-vl/m64-lmhead-lowcma/

tmpdir="$(mktemp -d)"
cleanup() {
    case "$tmpdir" in
        /tmp/tmp.*) rm -rf "$tmpdir" ;;
    esac
}
trap cleanup EXIT

install -m 0600 "$KEY_SOURCE" "$tmpdir/id_ed25519"
ssh_common=(
    -i "$tmpdir/id_ed25519"
    -o BatchMode=yes
    -o ConnectTimeout=10
    -o StrictHostKeyChecking=accept-new
)

ssh "${ssh_common[@]}" "$BOARD" "hostname; uname -m; mkdir -p '$REMOTE_ROOT/language' '$REMOTE_ROOT/lmhead'"
rsync -a --info=progress2 -e "ssh -i '$tmpdir/id_ed25519' -o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=accept-new" \
    "$LANGUAGE_SRC" "$BOARD:$REMOTE_ROOT/language/"
rsync -a --info=progress2 -e "ssh -i '$tmpdir/id_ed25519' -o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=accept-new" \
    "$HEAD_SRC" "$BOARD:$REMOTE_ROOT/lmhead/"
ssh "${ssh_common[@]}" "$BOARD" "find '$REMOTE_ROOT' -maxdepth 2 -type f | sort; du -sh '$REMOTE_ROOT'"
echo MAGE_M75C_FULL_LAYOUT_SYNC_PASS
