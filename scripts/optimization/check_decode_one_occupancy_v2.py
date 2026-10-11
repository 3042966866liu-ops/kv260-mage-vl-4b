"""Fail-closed occupancy evidence parser; synthetic selftest is not RTL evidence."""
import argparse
import json
import re
from pathlib import Path
from measurement import sha256

ROOT = Path(__file__).resolve().parents[2]
STAGE = ROOT/'tmp/op01_decode_one_occupancy_v3'

def parse_log(log):
    if re.search(r'^\s*(Fatal:|ERROR:)|^\s*UVM_(?:ERROR|FATAL)\b(?!\s*:\s*0\s*$)', log, re.M):
        raise ValueError('Simulator or UVM error')
    if not re.search(r'RTL Simulation\s*:\s*4\s*/\s*4', log):
        raise ValueError('Incomplete transactions')
    peaks = re.findall(r'OP01_FIFO_OCCUPANCY_PASS peaks=(\d+),(\d+),(\d+),(\d+)', log)
    if len(peaks) != 1:
        raise ValueError('Missing or duplicate final peaks')
    peaks = list(map(int, peaks[0]))
    if any(p < 0 or p > 8192 for p in peaks) or peaks[3] != 8192:
        raise ValueError('Invalid peaks / shard3 boundary not reached')
    transactions = re.findall(r'OP01_OCC_TX_COMPLETE tx=(\d+) time=\s*(\d+) peaks=(\d+),(\d+),(\d+),(\d+)', log)
    if [int(t[0]) for t in transactions] != [0,1,2,3]:
        raise ValueError('Missing / repeated transaction completion')
    previous = [0]*4
    for tx,time,*peak in transactions:
        peak = list(map(int,peak))
        if any(p < prev or p > final for p,prev,final in zip(peak,previous,peaks)):
            raise ValueError('Inconsistent cumulative peaks')
        previous = peak
    modes = []
    for tx in [0,2]:
        if log.count(f'OP01_FIFO_FULL tx={tx} shard=3 occupancy=8192') != 1:
            raise ValueError('Missing / repeated full marker')
        releases = re.findall(rf'OP01_FULL_HOLD_PASS tx={tx} cycles=256 release_time=\s*(\d+)',log)
        if len(releases) != 1:
            raise ValueError('Full hold not proven')
        end = int(transactions[tx][1]); start = int(releases[0])
        if end <= start:
            raise ValueError('Completion before release')
        modes.append(dict(mode='T32' if tx==0 else 'Decode-one',transaction=tx,
            hold_cycles=256,release_time_ps=start,complete_time_ps=end,
            release_to_completion_ps=end-start))
    return dict(peaks=peaks,modes=modes,transactions_completed=4,
        peak_units='32-bit FIFO words',timing_scope='RTL simulation ps, NOT board performance')

def audit():
    manifest=json.loads((STAGE/'PREPARATION.json').read_text())
    tb=STAGE/'verilog/op01_decode_one_kernel.autotb.v'
    if sha256(tb)!=manifest['tb_sha256']:
        raise ValueError('Testbench changed')
    for name,digest in manifest['dut_files'].items():
        if sha256(STAGE/'verilog'/name)!=digest:
            raise ValueError('DUT changed: '+name)
    result=parse_log((STAGE/'verilog/xsim.log').read_text(errors='replace'))
    for name,digest in manifest['expected_outputs'].items():
        if sha256(STAGE/'tv/rtldatafile'/name)!=digest:
            raise ValueError('Frozen output mismatch: '+name)
    if len(manifest['expected_outputs'])!=5:
        raise ValueError('Five streams required')
    result['expected_outputs']=manifest['expected_outputs']
    result['evidence']={str(p.relative_to(ROOT)):sha256(p) for p in [
        STAGE/'PREPARATION.json',tb,STAGE/'verilog/xsim.log']}
    return result

def selftest():
    text=''
    for tx in range(4):
        if tx in [0,2]:
            text+=f'OP01_FIFO_FULL tx={tx} shard=3 occupancy=8192\nOP01_FULL_HOLD_PASS tx={tx} cycles=256 release_time={tx*1000+100}\n'
        text+=f'OP01_OCC_TX_COMPLETE tx={tx} time={tx*1000+200} peaks=8188,8192,8192,8192\n'
    text+='OP01_FIFO_OCCUPANCY_PASS peaks=8188,8192,8192,8192\nRTL Simulation : 4 / 4\nUVM_ERROR : 0\n'
    assert parse_log(text)['peaks'][0]==8188
    bad=[text+'Fatal: timeout\n',text+'UVM_ERROR file_write_agent.sv mismatch\n',
         text.replace('cycles=256','cycles=255'),text.replace('4 / 4','3 / 4'),
         text.replace('8188','8193'),text.replace('time=200','time=99'),
         text.replace('tx=2 shard=3 occupancy=8192','tx=9 shard=3 occupancy=8192'),
         text.replace('tx=3 time=3200','tx=2 time=3200')]
    for case in bad:
        try: parse_log(case)
        except ValueError: continue
        raise AssertionError('Bad log accepted')
    print('OCCUPANCY_PARSER_SELFTEST_PASS positive=1 negative=8 synthetic_only=true')

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--selftest',action='store_true')
    args=parser.parse_args()
    if args.selftest: selftest()
    else: print(json.dumps(audit(),indent=2))
