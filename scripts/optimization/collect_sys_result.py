"""Collect full raw-byte result only after terminal runner and export markers."""
import base64
import argparse
import hashlib
import json
from pathlib import Path
import re
import zlib
from measurement import sha256,write_json,exclusive_lock
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'deployment/mage_vl4b/optimization_v1'
parser=argparse.ArgumentParser();parser.add_argument('--revision',type=int,choices=(1,2,5),default=2);args=parser.parse_args()
runlog=ROOT/f'tmp/op01_sys{args.revision:02d}/run.log'
log=ROOT/f'tmp/op01_sys{args.revision:02d}/export.log'
text=log.read_text(encoding='utf-8-sig');runtext=runlog.read_text(encoding='utf-8-sig')
if not re.search(r'__OP01_SYS_RC_[01]__',runtext):raise RuntimeError('No terminal board marker; do not classify a live process')
if '__OP01_EXPORT_RC_0__' not in text or 'OP01_RESULT_EXPORT_END' not in text:raise RuntimeError('Export incomplete')
summary=json.loads(runtext.split('OP01_SYS_JSON_BEGIN',1)[1].split('OP01_SYS_JSON_END',1)[0])
metadata=json.loads(re.search(r'OP01_RESULT_META (.+)',text).group(1))
chunks=re.findall(r'OP01_RESULT_CHUNK (\d+) ([A-Za-z0-9+/=]+)',text)
if [int(i) for i,_ in chunks]!=list(range(len(chunks))):raise RuntimeError('Missing/reordered result chunk')
packed=base64.b64decode(''.join(value for _,value in chunks),validate=True)
if len(packed)!=metadata['compressed_bytes'] or hashlib.sha256(packed).hexdigest()!=metadata['compressed_sha256']:
    raise RuntimeError('Compressed result mismatch')
raw=zlib.decompress(packed)
if len(raw)!=metadata['raw_bytes'] or hashlib.sha256(raw).hexdigest()!=metadata['raw_sha256']:
    raise RuntimeError('Raw result mismatch')
if metadata['raw_sha256']!=summary['full_result_sha256']:raise RuntimeError('UART summary identity mismatch')
board=json.loads(raw)
if args.revision==5 and board.get('timing_eligible') is not False:
    raise RuntimeError('SYS05 must remain diagnostic, not a performance sample')
if board['status']=='PROVISIONAL':
    calls=board['board_evidence']['host_calls'];transactions=board['transactions']
    if calls!=len(transactions) or not transactions or any(t['ap_return']!=0x4D395832 for t in transactions):
        raise RuntimeError('FPGA physical identity/counter proof differs')
    if not board['boot_unchanged'] or not board['cmdline_unchanged'] or not board['cleanup']['buffers_released']:
        raise RuntimeError('Cleanup/rollback invariant differs')
out=BASE/f'gates/G01-SYS-development/attempt_{args.revision:02d}'
with exclusive_lock(BASE/'control.lock'):
    out.mkdir(parents=True,exist_ok=False)
    (out/'board_result.json').write_bytes(raw)
    scope=('Real raw4s SYS05 instrumented Decode diagnostic; checkpoint I/O can perturb timing/cache; not a performance, numerical or quality acceptance'
           if args.revision==5 else 'Real raw4s SYS2 development baseline, not numerical/quality/tier acceptance')
    result=dict(status=board['status'],scope=scope,
        board_result_sha256=sha256(out/'board_result.json'),uart_log_sha256=sha256(runlog),
        export_log_sha256=sha256(log),numerical_acceptance=False,formal_quality_pass=False,achieved_level=None,
        board_result=board)
    write_json(out/'result.json',result)
    path=ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json';index=json.loads(path.read_text(encoding='utf-8-sig'))
    index['latest_optimization_v1_sys_development']=dict(status=board['status'],result=str((out/'result.json').relative_to(ROOT)),
        sha256=sha256(out/'result.json'),numerical_acceptance=False,achieved_level=None)
    write_json(path,index)
    path=BASE/'STATE.json';state=json.loads(path.read_text())
    state['results']['sys_development']=str((out/'result.json').relative_to(ROOT))
    state['next_action']='Review measured SYS and compare same-quant numerical tensors before G01.2; preserve failed levels'
    write_json(path,state)
print(json.dumps(dict(status=board['status'],request=summary.get('request'),errors=board['errors'])))
