"""Derive versioned COM3 control; retain same fail-safe transfer/recovery order."""
from m351_workflow import HERE,atomic
from m421_prepare import once
def main():
    s=(HERE/'m423_control02.ps1').read_text(encoding='utf-8')
    old="foreach ($key in @('latest_m420_combination_board','latest_m420_combination_closure','latest_m421_saved_language_board','latest_m421_saved_language_closure','latest_m422_borrowed_DMA_component','latest_m423_integrated_preparation','latest_m423_integrated_support')) { VerifyEvidence $key }"
    s=once(s,old,"foreach ($key in @('latest_m423_integrated_board','latest_m423_integrated_closure','latest_m425_warm_protocol','latest_m425_performance_preparation','latest_m425_performance_support')) { VerifyEvidence $key }")
    s=s.replace('candidates/M423-integrated-video-01','candidates/M425-visual-MLP-warm-performance-01').replace('/home/ubuntu/m423_integrated_video_candidate_01','/home/ubuntu/m425_warm_performance_candidate_01')
    s=s.replace('tmp/m42302','tmp/m42501').replace('m423_workflow02.py','m425_workflow.py')
    s=s.replace('latest_m423_integrated_support','latest_m425_performance_support').replace('latest_m423_integrated_transfer','latest_m425_performance_transfer')
    s=s.replace('candidates/M421-combination-saved-language-01','candidates/M423-integrated-video-01')
    s=s.replace('m423_assemble.py','m425_assemble.py').replace('run_m423.sh','run_m425.sh').replace('M423','M425').replace('runs/M425-integrated-video-board-01','runs/M425-warm-performance-board-01')
    s=s.replace('-TimeoutSeconds 1500','-TimeoutSeconds 4200').replace('-TimeoutSeconds 1080','-TimeoutSeconds 1200')
    atomic(HERE/'m425_control.ps1',s.encode('utf-8'),immutable=True)
    print('M425_HOST_PREPARED')
if __name__=='__main__':main()
