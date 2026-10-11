"""Prepare a saved-only adjudication with the existing prespecified statistics."""
from m351_workflow import HERE, atomic
from m427_prepare import once


def main():
    s = (HERE / 'm425_close.py').read_text(encoding='utf-8')
    s = s.replace('from m425_workflow02 import check', 'from m433_workflow import check')
    s = s.replace('M425', 'M433').replace('latest_m425_warm_board', 'latest_m433_warm_board').replace('latest_m425_warm_closure', 'latest_m433_warm_closure').replace("sha(HERE/'m425_close.py')", "sha(HERE/'m433_close.py')")
    s = s.replace('MLP12+13 PL', 'MLP13..23 PL').replace('第12＋13层', '第13–23层').replace('第12＋13层', '第13–23层')
    s = s.replace('两层视觉', '后11层视觉').replace('2026-10-06', '2026-10-07')
    s = once(s, "    result['offline_report_repair']='First report construction rejected duplicate temperature_measurement_enabled keyword before writing any verdict. Only dictionary merge corrected; saved board raw and prespecified statistics unchanged, no hardware rerun.'\n", '')
    atomic(HERE / 'm433_close.py', s.encode('utf-8'), immutable=True)
    print('M433_SAVED_CLOSURE_SOURCE_READY')


if __name__ == '__main__':
    main()
