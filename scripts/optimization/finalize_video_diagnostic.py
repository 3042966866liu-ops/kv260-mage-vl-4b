"""Persist measured diagnostic, without promoting board/performance gates."""
import json
import argparse
from pathlib import Path
from measurement import exclusive_lock,sha256,write_json
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'deployment/mage_vl4b/optimization_v1'
parser=argparse.ArgumentParser();parser.add_argument('--wording',action='store_true');args=parser.parse_args()
kind='wording' if args.wording else 'order'
run=BASE/f'runs/OP01-video-{kind}-diagnostic-v1'
data=json.loads((run/'result.json').read_text())
if data['status']!='MEASURED' or len(data['cases'])!=6:
    raise RuntimeError('Temporal diagnostic incomplete')
if data['native_cli']['exit_code']!=0 or not data['native_cli']['entry_unchanged']:
    raise RuntimeError('Native CLI not confirmed')
for case in data['cases']:
    capture=run/(case['case']+'_vision_input.npz')
    if sha256(capture)!=case['capture_sha256']:raise RuntimeError('Capture changed')
    if case['reconstruction_max_u8_error']!=0:raise RuntimeError('Unexpected visual reconstruction difference')
out=BASE/f'gates/G01-video-{kind}-diagnostic/attempt_01/result.json'
if out.exists():raise RuntimeError('Immutable diagnostic exists')
with exclusive_lock(BASE/'control.lock'):
    write_json(out,dict(status='MEASURED',scope='software controlled-input diagnosis, no FPGA execution',
        result_path=str((run/'result.json').relative_to(ROOT)),result_sha256=sha256(run/'result.json'),
        runner_sha256=sha256(ROOT/'scripts/optimization/diagnose_video_order.py'),
        conclusions=(['Six predetermined wording/order cases complete; no board execution',
            'Swapping choices did not fix direction; open forward question answered correctly',
            'Structured first/last/direction response correct in both orders on this one video',
            'Prompt sensitivity observed; retain original failure and validate new inputs before quality claims'] if args.wording else
            ['Actual official vision Conv2d input reconstructs exactly to each selected RGB frame',
            'Untouched official CLI also answers right to left on forward video',
            'First and last position answers correct in both orders',
            'Direction answers forward:right to left; reverse:left; insufficient reliable temporal reasoning']),
        formal_quality_pass=False,numerical_acceptance=False,board_executed=False,achieved_level=None))
    state_path=BASE/'STATE.json';state=json.loads(state_path.read_text())
    # Repair prior host-selftest status regression only from authoritative gates.
    for gate in ('G00.1','G00.2'):
        prior=json.loads((BASE/f'gates/{gate}/attempt_01/result.json').read_text())
        if prior['status']!='PASS':raise RuntimeError('OP00 gates not proven')
    state['steps']['OP00']['status']='PASS'
    state['results'][f'video_{kind}_diagnostic']=str(out.relative_to(ROOT))
    state['next_action']='Bounded prompt diagnosis finished. Proceed stable-T32 same-quant SYS numeric/timing baseline; preserve all quality failures, no compression promotion.'
    write_json(state_path,state)
    index_path=ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json'
    index=json.loads(index_path.read_text(encoding='utf-8-sig'))
    index['latest_optimization_v1_offline_video_diagnostic']=dict(status='MEASURED',board_executed=False,
        result=str(out.relative_to(ROOT)),sha256=sha256(out),formal_quality_pass=False)
    write_json(index_path,index)
print(str(out))
