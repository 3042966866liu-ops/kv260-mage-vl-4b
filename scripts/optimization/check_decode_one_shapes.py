"""Read-only supplemental RTL check. Never infer PASS from CSim or a live log."""
import argparse
import json
import re
from pathlib import Path
from measurement import sha256

ROOT = Path(__file__).resolve().parents[2]

def check_text(report, log, tb, env):
    if not re.search(r'Verilog\s*\|\s*Pass', report):
        raise ValueError('Missing formal supplemental Verilog PASS')
    if not re.search(r'RTL Simulation\s*:\s*3\s*/\s*3', log):
        raise ValueError('Missing three completed RTL transactions')
    if re.search(r'(?im)^\s*(?:Fatal:|FATAL_ERROR|ERROR:)', log):
        raise ValueError('Fatal/error in simulator log')
    if not re.search(r'parameter\s+AUTOTB_TRANSACTION_NUM\s*=\s*3\s*;', tb):
        raise ValueError('Wrong generated transaction count')
    for name in ['svr_latency_tx', 'svr_latency_rx', 'axi_latency_w0',
                 'axi_latency_w1', 'axi_latency_w2', 'axi_latency_w3']:
        if 'class ' + name not in env:
            raise ValueError('Missing backpressure class: ' + name)
    if 'delay inside {[0:256]}' not in env:
        raise ValueError('Missing randomized delay configuration')

def audit():
    project = ROOT / 'tmp/op01_decode_one_shapes'
    sim = project / 'hls/sim'
    paths = [sim / 'report/op01_decode_one_kernel_cosim.rpt',
             sim / 'verilog/xsim.log',
             sim / 'verilog/op01_decode_one_kernel.autotb.v',
             sim / 'verilog/op01_decode_one_kernel_subsystem/op01_decode_one_kernel_env.sv']
    check_text(*(p.read_text(errors='replace') for p in paths))
    reused = json.loads((project / 'REUSED_SYNTHESIS.json').read_text())
    identities = {
        'kernel_sha256': ROOT / 'hls/mage_decode_op01_one/decode_one.cpp',
        'original_cosim_sha256': ROOT / 'tmp/op01_decode_one_rtl/hls/sim/report/op01_decode_one_kernel_cosim.rpt',
        'original_synthesis_sha256': ROOT / 'tmp/op01_decode_one_rtl/hls/syn/report/op01_decode_one_kernel_csynth.rpt'}
    for key, path in identities.items():
        if sha256(path) != reused[key]:
            raise ValueError('Original identity changed: ' + key)
    return dict(status='PASS_SUPPLEMENTAL_RTL_ARTIFACT_CHECK_ONLY',
                transactions=3, board_deployed=False, performance_pass=False,
                limitations=['Requires runner terminal exit and final postcheck collection',
                             'No measured maximum FIFO occupancy or routed timing claim'],
                evidence={p.relative_to(ROOT).as_posix(): sha256(p)
                          for p in paths + list(identities.values())})

def selftest():
    report = '| Verilog | Pass |'
    log = '// RTL Simulation : 3 / 3'
    tb = 'parameter AUTOTB_TRANSACTION_NUM = 3;'
    env = 'delay inside {[0:256]} ' + ' '.join('class ' + x for x in
          ['svr_latency_tx', 'svr_latency_rx', 'axi_latency_w0',
           'axi_latency_w1', 'axi_latency_w2', 'axi_latency_w3'])
    check_text(report, log, tb, env)
    bad = [(report, log.replace('3 / 3', '0 / 3'), tb, env),
           (report, log.replace('3 / 3', '4 / 4'), tb, env),
           (report.replace('Pass', 'Fail'), log, tb, env),
           (report, log + '\nFatal: watchdog', tb, env),
           (report, log, tb.replace('= 3', '= 4'), env),
           (report, log, tb, env.replace('class axi_latency_w3', 'missing'))]
    for sample in bad:
        try:
            check_text(*sample)
        except ValueError:
            continue
        raise AssertionError('Invalid evidence accepted')
    print('SHAPES_CHECKER_SELFTEST_PASS positives=1 negatives=6; not RTL evidence')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--selftest', action='store_true')
    args = parser.parse_args()
    if args.selftest:
        selftest()
    else:
        print(json.dumps(audit(), indent=2))
