param(
    [string]$Port = 'COM3',
    [string]$ExpectedFtdiSerial = 'XFL1PL5N11BJB',
    [string]$LogPath = 'tmp\m75c_full_layout\read_status_uart.log',
    [int]$TimeoutSeconds = 180
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$command = @'
sudo -n bash -lc 'echo CMDLINE; cat /proc/cmdline; echo BOOT; sha256sum /boot/firmware/boot.scr.uimg 2>/dev/null || true; test ! -e /boot/firmware/user-override.dtb && echo ACTIVE_DTB_ABSENT || sha256sum /boot/firmware/user-override.dtb; echo SERVICES; systemctl is-active mage-m75c-full-layout-cycle.service mage-m75c-full-layout-cleanup.service 2>/dev/null || true; echo FILES; ls -l /home/ubuntu/tellme_mage_m75c_full_20260829_01/M75C_FULL_LAYOUT_*RESULT.json /home/ubuntu/tellme_mage_m75c_full_20260829_01/M75C_FULL_LAYOUT_CYCLE.log 2>/dev/null || true; echo CYCLE_STATUS; systemctl --no-pager --full status mage-m75c-full-layout-cycle.service 2>/dev/null | tail -80 || true; echo CLEANUP_STATUS; systemctl --no-pager --full status mage-m75c-full-layout-cleanup.service 2>/dev/null | tail -60 || true; echo GATE_JSON; sed -n "1,220p" /home/ubuntu/tellme_mage_m75c_full_20260829_01/M75C_FULL_LAYOUT_GATE_RESULT.json 2>/dev/null || true; echo CYCLE_JSON; sed -n "1,220p" /home/ubuntu/tellme_mage_m75c_full_20260829_01/M75C_FULL_LAYOUT_CYCLE_RESULT.json 2>/dev/null || true'
'@

$workspace = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
& (Join-Path $PSScriptRoot 'm75c_uart_command.ps1') `
    -Command $command `
    -Port $Port `
    -ExpectedFtdiSerial $ExpectedFtdiSerial `
    -LogPath $LogPath `
    -TimeoutSeconds $TimeoutSeconds
