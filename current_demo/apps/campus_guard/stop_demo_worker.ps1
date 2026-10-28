$ErrorActionPreference='Stop'
# A data message consumed at a known idle boundary. No process signal or device write.
Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8766/api/board/stop' -ContentType 'application/json' -Body '{}' -TimeoutSec 5 | Out-Null
Write-Host 'Normal stop requested. Keep the bridge open until its original board cleanup result returns.'
