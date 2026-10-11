"""Prepare and check prospective saved-only statistics; no real measurements."""
from m351_workflow import HERE,atomic


def main():
    code=(HERE/'m433_close.py').read_text(encoding='utf-8').replace('M433','M437').replace('m433','m437')
    code=code.replace('from m425_warm import adjudicate','from m437_sequence import adjudicate')
    code=code.replace('latest_m437_warm_board','latest_m437_natural_IO_board').replace('latest_m437_warm_closure','latest_m437_natural_IO_closure')
    code=code.replace('PASS_M437_CONTROLLED_WARM_MEASUREMENTS_COLLECTED','PASS_M437_NATURAL_IO_MEASUREMENTS_COLLECTED')
    code=code.replace('CLOSED_M437_WARM_CONDITIONS_NOT_ESTABLISHED','CLOSED_M437_EXPERIMENT_CONDITIONS_NOT_ESTABLISHED')
    code=code.replace('M437-warm-performance-closure-01','M437-natural-IO-closure-01')
    code=code.replace('Fixed159 last-frame two-view warm requests only','Fixed159 last-frame two-view resident-runtime requests including natural I/O')
    code=code.replace('完整暖请求','包含自然I/O的完整请求').replace('暖态对照','预定对照').replace('暖请求结论','包含自然I/O的请求结论')
    code=code.replace('不删样本、不追加。','读盘不排除样本，不删样本、不追加。')
    atomic(HERE/'m437_close.py',code.encode('utf-8'),immutable=True)
    test=(HERE/'m433_closure_support.py').read_text(encoding='utf-8').replace('M433','M437').replace('m433','m437')
    test=test.replace('tmp/m43705/export_fixture','tmp/m43703/export_fixture').replace('tmp/m43706/closure_fixture','tmp/m43701/closure_fixture')
    test=test.replace('latest_m437_warm_board','latest_m437_natural_IO_board').replace('latest_m437_warm_closure','latest_m437_natural_IO_closure')
    test=test.replace('M437-warm-performance-closure-01','M437-natural-IO-closure-01')
    test=test.replace('PASS_CONTROLLED_WARM_FULL_REQUEST_BENEFIT','PASS_NATURAL_IO_FULL_REQUEST_BENEFIT')
    test=test.replace('NET_BENEFIT_NOT_RELIABLY_MEASURED_CLOSE_VARIANT','NET_BENEFIT_NOT_RELIABLY_MEASURED_CLOSE_THIS_EXPERIMENT')
    test=test.replace('M437-closure-support-01','M437-natural-IO-closure-support-01')
    atomic(HERE/'m437_closure_support.py',test.encode('utf-8'),immutable=True)
    print('M437_CLOSURE_PREPARED')


if __name__=='__main__':main()
