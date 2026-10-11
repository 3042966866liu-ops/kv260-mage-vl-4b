if(Test-Path (Join-Path $PSScriptRoot '../../tmp/m441_cma12/Run.log')){throw 'Existing attempt; collect only'}
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$taskRoot=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$taskUART=Join-Path $taskRoot 'scripts/m75c_uart_command.ps1'
& $taskUART -Command 'sudo -n true' -LogPath 'tmp/m441_cma12/sudo.log' -TimeoutSeconds 15 -MarkerPrefix '__M441C_AUTH_RC_'
foreach($taskName in @('PACKAGE_MANIFEST.json','probe.py','run.sh','SHA256SUMS')){
 & (Join-Path $taskRoot 'scripts/m212_uart_put_file_chunked.ps1') -LocalPath ('deployment/mage_vl4b/optimization_v1/candidates/M441-cma-source-only-12/'+$taskName) -RemotePath ('/home/ubuntu/m441_cma_source_candidate_12/'+$taskName) -LogPrefix ('tmp/m441_cma12/upload_'+$taskName.Replace('.','_')) -ChunkBytes 900 -TimeoutSeconds 25
}
& $taskUART -Command 'sudo -n bash -n /home/ubuntu/m441_cma_source_candidate_12/run.sh' -LogPath 'tmp/m441_cma12/syntax.log' -TimeoutSeconds 15 -MarkerPrefix '__M441C_SYNTAX_RC_'
& $taskUART -Command 'sudo -n bash /home/ubuntu/m441_cma_source_candidate_12/run.sh 45e116a9cd7c1e1ff817e2db08714b387a630a9b9a774ab32a5f330e1de226d6 --read-source-only' -LogPath 'tmp/m441_cma12/Run.log' -TimeoutSeconds 60 -MarkerPrefix '__M441C_SOURCE_RC_'
