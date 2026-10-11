"""Versioned strict collector and COM3 controller; no board operations."""
from m351_workflow import HERE, atomic
from m427_prepare import once


def main():
    w = (HERE / 'm425_workflow02.py').read_text(encoding='utf-8')
    w = w.replace('M425', 'M433').replace('m425', 'm433')
    # Statistics/environment code is reused byte-for-byte, not renamed or rescanned.
    w = w.replace('from m433_warm import', 'from m425_warm import')
    w = w.replace('candidates/M433-visual-MLP-warm-performance-02', 'candidates/M433-late11-complete-request-warm-01')
    w = w.replace("r['selected_layers']!=[12,13]", "r['selected_layers']!=list(range(13,24))")
    w = w.replace("r['fpga_transactions']!=9685", "r['fpga_transactions']!=11089").replace("r['completed_visual_physical']!=312", "r['completed_visual_physical']!=1716")
    w = w.replace("board['latest_m421_saved_language_board']", "board['latest_m428_saved_language_board']")
    w = w.replace('(52 if index else 0)', '(286 if index else 0)').replace('for a in (12,13)', 'for a in range(13,24)')
    w = w.replace('all_four_bindings_restored', 'all_visual_bindings_restored').replace('Candidate four stages differ', 'Candidate twenty-two stages differ')
    w = once(w, "            for k in ('physical_record_SHA_after_timer','visual_record_SHA_after_timer'):", "            expected_records=json.loads((ROOT/src['result']).read_bytes())['transactions'][index*781:(index+1)*781]\n            if s['physical_record_SHA_after_timer']!=hashlib.sha256(json.dumps(expected_records,sort_keys=True,separators=(',',':')).encode()).hexdigest():raise ValueError('Complete post-timer language physical sequence differs')\n            for k in ('physical_record_SHA_after_timer','visual_record_SHA_after_timer'):")
    w = w.replace("candidates/M423-integrated-video-01/PACKAGE_MANIFEST.json", "candidates/M432-late11-integrated-video-02/PACKAGE_MANIFEST.json")
    w = w.replace("folder=ROOT/'tmp/m43302'", "folder=ROOT/'tmp/m43301/board'")
    w = w.replace('2026-10-06', '2026-10-07')
    atomic(HERE / 'm433_workflow.py', w.encode('utf-8'), immutable=True)
    control = (HERE / 'm432_control02.ps1').read_text(encoding='utf-8')
    control = control.replace('M432', 'M433').replace('m432', 'm433')
    control = control.replace('candidates/M433-late11-integrated-video-02', 'candidates/M433-late11-complete-request-warm-01')
    control = control.replace('/home/ubuntu/m433_late11_integrated_candidate_02', '/home/ubuntu/m433_late11_warm_candidate_01')
    control = control.replace('m433_workflow02.py', 'm433_workflow.py')
    control = control.replace("@('latest_m431_borrowed_CPU_closure','latest_m430_complete_visual_closure','latest_m428_saved_language_board','latest_m433_integrated_packet','latest_m433_provider_component','latest_m433_integrated_support')", "@('latest_m432_integrated_board','latest_m432_integrated_closure','latest_m433_complete_request_protocol','latest_m433_complete_request_preparation','latest_m433_timed_provider_component','latest_m433_performance_support')")
    control = control.replace('latest_m433_integrated_support', 'latest_m433_performance_support')
    control = control.replace('latest_m433_integrated_transfer', 'latest_m433_performance_transfer')
    control = control.replace('candidates/M428-late11-saved-language-02/PACKAGE_MANIFEST.json', 'candidates/M432-late11-integrated-video-02/PACKAGE_MANIFEST.json')
    control = control.replace('runs/M433-integrated-video-board-01', 'runs/M433-warm-performance-board-01')
    control = control.replace('-TimeoutSeconds 1500', '-TimeoutSeconds 4200')
    atomic(HERE / 'm433_control.ps1', control.encode('utf-8'), immutable=True)
    print('M433_HOST_PREPARED')


if __name__ == '__main__':
    main()
