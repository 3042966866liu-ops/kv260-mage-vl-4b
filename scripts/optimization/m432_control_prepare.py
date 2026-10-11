"""Versioned 02 host/control; no COM3 access in preparation."""
from m351_workflow import HERE, atomic
from m427_prepare import once


def main():
    s = (HERE / 'm432_workflow.py').read_text(encoding='utf-8')
    s = once(s, 'candidates/M432-late11-integrated-video-01', 'candidates/M432-late11-integrated-video-02')
    atomic(HERE / 'm432_workflow02.py', s.encode('utf-8'), immutable=True)
    s = (HERE / 'm423_control.ps1').read_text(encoding='utf-8')
    anchor = "foreach ($key in @('latest_m420_combination_board','latest_m420_combination_closure','latest_m421_saved_language_board','latest_m421_saved_language_closure','latest_m422_borrowed_DMA_component','latest_m423_integrated_preparation','latest_m423_integrated_support')) { VerifyEvidence $key }"
    s = once(s, anchor, '__CURRENT_PREREQUISITES__')
    s = s.replace('m423', 'm432').replace('M423', 'M432')
    s = s.replace('candidates/M432-integrated-video-01', 'candidates/M432-late11-integrated-video-02')
    s = s.replace('/home/ubuntu/m432_integrated_video_candidate_01', '/home/ubuntu/m432_late11_integrated_candidate_02')
    s = s.replace('candidates/M421-combination-saved-language-01', 'candidates/M428-late11-saved-language-02')
    s = s.replace('tmp/m43201/', 'tmp/m43201/board/')
    s = s.replace("'m432_workflow.py'", "'m432_workflow02.py'")
    s = s.replace('M432_ENABLE_SAVED_FEATURES=1', 'M432_ENABLE_INTEGRATED_VIDEO=1')
    s = s.replace('__CURRENT_PREREQUISITES__', "foreach ($key in @('latest_m431_borrowed_CPU_closure','latest_m430_complete_visual_closure','latest_m428_saved_language_board','latest_m432_integrated_packet','latest_m432_provider_component','latest_m432_integrated_support')) { VerifyEvidence $key }")
    s = s.replace('M432_LANGUAGE_QUALITY_SYNCHRONIZED', 'M432_INTEGRATED_NUMERICAL_SYNCHRONIZED')
    atomic(HERE / 'm432_control02.ps1', s.encode('utf-8'), immutable=True)
    print('M432_CONTROL02_PREPARED')


if __name__ == '__main__':
    main()
