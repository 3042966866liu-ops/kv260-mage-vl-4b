"""Adapt actual assembly and transfer fixtures without touching prior evidence."""
from m351_workflow import HERE, atomic
from m427_prepare import once


def main():
    s = (HERE / 'm432_transfer_support.py').read_text(encoding='utf-8')
    s = s.replace('m432_control02.ps1', 'm433_control.ps1').replace('m432_control03.ps1', 'm433_control02.ps1')
    s = s.replace('M432', 'M433').replace('m432', 'm433')
    s = s.replace('import m433_workflow02 as w', 'import m433_workflow as w')
    s = s.replace("b['latest_m433_integrated_support']", "b['latest_m433_performance_support']")
    s = s.replace('candidates/M428-late11-saved-language-02', 'candidates/M432-late11-integrated-video-02')
    s = s.replace('/home/ubuntu/m428_saved_feature_candidate_01', '/home/ubuntu/m432_late11_integrated_candidate_02')
    s = s.replace('runs/M433-integrated-transfer-01', 'runs/M433-performance-transfer-01').replace('latest_m433_integrated_transfer', 'latest_m433_performance_transfer')
    old = "foreach ($key in @('latest_m431_borrowed_CPU_closure','latest_m430_complete_visual_closure','latest_m428_saved_language_board','latest_m433_integrated_packet','latest_m433_provider_component','latest_m433_integrated_support')) { VerifyEvidence $key }"
    new = "foreach ($key in @('latest_m432_integrated_board','latest_m432_integrated_closure','latest_m433_complete_request_protocol','latest_m433_complete_request_preparation','latest_m433_timed_provider_component','latest_m433_performance_support')) { VerifyEvidence $key }"
    s = once(s, old, new)
    s = once(s, "                fixture_first_attempt_rejection=dict(reason='Sandbox BASE redirected upload_names to an absent fixture old manifest; copy only that exact original manifest into sandbox. No production change.',original_harness_sha256=sha(ROOT/'tmp/m43302/transfer_support_before_fixture_fix.py')),\n", '')
    s = s.replace('2026-10-07', '2026-10-07')
    s = s.replace('03控制', '02控制').replace('control03_actual_failure_collection_selftest', 'control02_actual_failure_collection_selftest')
    s = s.replace('固定环境及两请求数值', '固定环境及预定4预热＋8正式完整请求')
    atomic(HERE / 'm433_transfer_support.py', s.encode('utf-8'), immutable=True)
    print('M433_TRANSFER_SUPPORT_SOURCE_READY')


if __name__ == '__main__':
    main()
