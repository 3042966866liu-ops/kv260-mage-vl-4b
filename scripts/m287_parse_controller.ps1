$ErrorActionPreference = 'Stop'
$tokens = $null
$errors = $null
[void][System.Management.Automation.Language.Parser]::ParseFile(
    (Join-Path $PSScriptRoot 'm287_run_natural_prompt_uart.ps1'),
    [ref]$tokens,
    [ref]$errors
)
if ($errors.Count -ne 0) {
    $errors | ForEach-Object { Write-Error $_.Message }
    throw 'M287_POWERSHELL_PARSE_FAIL'
}
Write-Output 'M287_POWERSHELL_PARSE_PASS'
