"""Small immutable read-only source package; no Overlay or inference."""
import shutil
import m351_workflow as w
from m441_host_io08 import atomic

def main():
    pkg=w.BASE/'candidates/M441-cma-source-only-12'
    pkg.mkdir(exist_ok=False)
    shutil.copyfile(w.HERE/'m441_cma_source_probe12.py',pkg/'probe.py')
    digest=w.sha(pkg/'probe.py')
    runner='\n'.join(['#!/usr/bin/env bash','set -euo pipefail','cd "$(dirname "${BASH_SOURCE[0]}")"','[[ "${2:-}" == "--read-source-only" ]] || exit 2','printf "%s  PACKAGE_MANIFEST.json\\n" "${1:?manifest SHA}" | sha256sum -c -','sha256sum -c SHA256SUMS','[[ $(id -u) == 0 ]] || exit 2','[[ ! -e /home/ubuntu/m441_cma_source_evidence_12 ]] || exit 2','set +e',f'/usr/local/share/pynq-venv/bin/python -B ./probe.py {digest}','gate_rc=$?','set -e','printf "M441C_RUN_DONE gate_rc=%s\\n" "$gate_rc"','exit "$gate_rc"',''])
    atomic(pkg/'run.sh',runner.encode('utf-8'),immutable=True)
    atomic(pkg/'SHA256SUMS',''.join(w.sha(pkg/n)+'  '+n+'\n' for n in ['probe.py','run.sh']).encode(),immutable=True)
    rows=[dict(path=n,bytes=(pkg/n).stat().st_size,sha256=w.sha(pkg/n)) for n in ['probe.py','run.sh','SHA256SUMS']]
    atomic(pkg/'PACKAGE_MANIFEST.json',w.encoded(dict(schema='m441-read-source-only-12',files=rows,file_count=len(rows),total_bytes=sum(r['bytes'] for r in rows))),immutable=True)
    relative=pkg.relative_to(w.ROOT).as_posix();manifest=w.sha(pkg/'PACKAGE_MANIFEST.json')
    control="""$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$taskRoot=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$taskUART=Join-Path $taskRoot 'scripts/m75c_uart_command.ps1'
& $taskUART -Command 'sudo -n true' -LogPath 'tmp/m441_cma12/sudo.log' -TimeoutSeconds 15 -MarkerPrefix '__M441C_AUTH_RC_'
foreach($taskName in @('PACKAGE_MANIFEST.json','probe.py','run.sh','SHA256SUMS')){
 & (Join-Path $taskRoot 'scripts/m212_uart_put_file_chunked.ps1') -LocalPath 'RELATIVE_PLACEHOLDER/'.Replace('RELATIVE_PLACEHOLDER','RELATIVE_ACTUAL')$taskName
}
"""
    control=control[:control.index('foreach')]+'foreach($taskName in @(\'PACKAGE_MANIFEST.json\',\'probe.py\',\'run.sh\',\'SHA256SUMS\')){\n'+f' & (Join-Path $taskRoot \'scripts/m212_uart_put_file_chunked.ps1\') -LocalPath (\'{relative}/\'+$taskName) -RemotePath (\'/home/ubuntu/m441_cma_source_candidate_12/\'+$taskName) -LogPrefix (\'tmp/m441_cma12/upload_\'+$taskName.Replace(\'.\',\'_\')) -ChunkBytes 900 -TimeoutSeconds 25\n'+'}\n'+"& $taskUART -Command 'sudo -n bash -n /home/ubuntu/m441_cma_source_candidate_12/run.sh' -LogPath 'tmp/m441_cma12/syntax.log' -TimeoutSeconds 15 -MarkerPrefix '__M441C_SYNTAX_RC_'\n"+f"& $taskUART -Command 'sudo -n bash /home/ubuntu/m441_cma_source_candidate_12/run.sh {manifest} --read-source-only' -LogPath 'tmp/m441_cma12/Run.log' -TimeoutSeconds 60 -MarkerPrefix '__M441C_SOURCE_RC_'\n"
    control="if(Test-Path (Join-Path $PSScriptRoot '../../tmp/m441_cma12/Run.log')){throw 'Existing attempt; collect only'}\n"+control
    atomic(w.HERE/'m441_source_control12.ps1',control.encode('utf-8'),immutable=True)
    print(manifest,w.sha(w.HERE/'m441_source_control12.ps1'))

if __name__=='__main__':main()
