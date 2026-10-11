#!/usr/bin/env bash
set -euo pipefail

key='ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIAi5sQsBx/0MREorhpFNgJIl18ClACHhQQE+FPzD2A9a tellme-m2-temporary'
directory=/home/ubuntu/.ssh
keys="$directory/authorized_keys"

mkdir -p "$directory"
chmod 700 "$directory"
touch "$keys"
chmod 600 "$keys"
if ! grep -qxF "$key" "$keys"; then
    printf '%s\n' "$key" >> "$keys"
fi
echo M89X1_SSH_AUTHORIZATION_PASS
