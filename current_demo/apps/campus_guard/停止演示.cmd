@echo off
"C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell\pwsh.exe" -NoProfile -File "%~dp0stop_demo_worker.ps1"
if errorlevel 1 pause
