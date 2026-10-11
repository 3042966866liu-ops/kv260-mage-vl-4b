"""Versioned actual host control derivation; no shell interpolation of Python."""
from m351_workflow import HERE,atomic,sha
from m427_prepare import once

def main():
    c=(HERE/'m427_control.ps1').read_text(encoding='utf-8').replace('m427','m429').replace('M427','M429')
    c=c.replace('M429-half-ranges-software-01','M429-late11-visual-PL-numeric-02').replace('/home/ubuntu/m429_half_ranges_candidate_01','/home/ubuntu/m429_late11_visual_candidate_02')
    c=c.replace('tmp/m42901/','tmp/m42902/').replace('M429-half-software-board-01','M429-late11-visual-PL-board-01')
    c=c.replace('latest_m429_half_transfer','latest_m429_late11_visual_transfer').replace('latest_m429_half_support','latest_m429_numeric_support')
    c=once(c,"'latest_m425_warm_closure','latest_m426_range_closure','latest_m429_half_protocol','latest_m429_half_component','latest_m429_half_preparation','latest_m429_numeric_support'",
        "'latest_m427_half_closure','latest_m428_saved_language_closure','latest_m429_streamed_scope_component','latest_m429_final_packet','latest_m429_numeric_support'")
    c=c.replace('M429_ENABLE_SOFTWARE_RANGE=1','M429_ENABLE_PL_NUMERICAL=1').replace('4800','1800')
    c=c.replace('Software range gate/export failed','Visual PL numerical gate/export failed').replace('M429_SOFTWARE_RANGE_SYNCHRONIZED_TASK_PENDING','M429_VISUAL_PL_NUMERICAL_SYNCHRONIZED')
    atomic(HERE/'m429_control.ps1',c.encode('utf-8'),immutable=True)
    print('M429_HOST_CONTROL_PREPARED',sha(HERE/'m429_control.ps1'))

if __name__=='__main__':main()
