"""Draft controller from proven single-source capture controller; no UART."""
from m351_workflow import HERE,atomic

def main():
    s=(HERE/'m390_control.ps1').read_text(encoding='utf-8-sig').replace('M390','M392').replace('m390','m392')
    s=s.replace('M392-gate-up-capture-01','M392-silu-layer-02').replace('m392_gate_up_capture_candidate_01','m392_silu_layer_candidate_02')
    s=s.replace('M387-ps-video-01','M385-ps-layer-02').replace('latest_m392_capture_','latest_m392_silu_layer_')
    s=s.replace('run_m392_capture.sh','run_m392_silu_layer.sh').replace('M392_ENABLE_CAPTURE','M392_ENABLE_SILU_LAYER')
    s=s.replace('M392-gate-up-capture-board-01','M392-silu-layer-board-01')
    old="    if (-not (Get-Content -LiteralPath (Join-Path $workspace 'tmp/m392/sudo_precheck_02.log') -Raw -Encoding UTF8).Contains('__M392_CHECK_SUDO_RC_0__')) { throw 'No confirmed human recovery' }\n"
    assert s.count(old)==1
    s=s.replace(old,"    & $uart -Command 'sudo -n true' -LogPath 'tmp/m392/sudo_upload_precheck_01.log' -TimeoutSeconds 15 -MarkerPrefix '__M392_UPLOAD_SUDO_RC_'\n    if (-not $?) { throw 'Sudo expired; no upload or gate' }\n")
    atomic(HERE/'m392_control.ps1',s.encode('utf-8'))
    s=(HERE/'m390_workflow.py').read_text(encoding='utf-8').replace('M390','M392').replace('m390','m392')
    s=s.replace('M392-gate-up-capture-01','M392-silu-layer-02').replace('M387-ps-video-01','M385-ps-layer-02')
    s=s.replace('latest_m392_capture_','latest_m392_silu_layer_').replace('M392-capture-transfer-01','M392-silu-layer-transfer-01')
    s=s.replace('仅一次原layer0捕获','仅一次原layer0 SiLU数值门禁').replace('下一步一次有界layer0捕获','下一步一次独立layer0 SiLU数值门禁')
    atomic(HERE/'m392_workflow.py',s.encode('utf-8'))
    print('M392_DRAFT_CONTROL_GENERATED')

if __name__=='__main__':main()
