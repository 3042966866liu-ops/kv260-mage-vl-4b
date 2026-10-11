import json
import argparse
from pathlib import Path
from measurement import sha256,write_json,exclusive_lock
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'deployment/mage_vl4b/optimization_v1'
parser=argparse.ArgumentParser();parser.add_argument('--attempt',type=int,default=3)
parser.add_argument('--revision',type=int,choices=(1,2,3,4,5),default=2);args=parser.parse_args()
log=ROOT/f'tmp/op01_sys_import{args.attempt:02d}/run.log'
text=log.read_text(encoding='utf-8-sig')
result=dict(status='FAIL',scope='Board import closure only',overlay_loaded=False,errors=[])
try:
    if '__OP01_IMPORT_RC_0__' not in text:raise RuntimeError('No successful exit marker')
    measured=json.loads(text.split('OP01_IMPORTS_JSON_BEGIN',1)[1].split('OP01_IMPORTS_JSON_END',1)[0])
    manifest=BASE/f'candidates/OP01-SYS-{args.revision:02d}/PACKAGE_MANIFEST.json'
    if measured['package_manifest_sha256']!=sha256(manifest):raise RuntimeError('Candidate SHA differs')
    if measured['status']!='PASS_IMPORT_ONLY' or measured['overlay_loaded'] or measured['model_loaded']:
        raise RuntimeError('Scope mismatch')
    if len(measured['imports'])!=(15 if args.revision>=3 else 10):raise RuntimeError('Missing dependency')
    if args.revision>=3 and not measured.get('decode_trace_interface_verified'):raise RuntimeError('Trace interface unverified')
    if args.revision>=2 and measured.get('tokenizer_vocabulary_size')!=151665:raise RuntimeError('Tokenizer not loaded')
    result.update(status='PASS',board=measured)
except Exception as exc:result['errors'].append(repr(exc))
result['uart_log']=dict(path=str(log.relative_to(ROOT)),sha256=sha256(log))
gate=BASE/f'gates/G01-SYS-imports/attempt_{args.attempt:02d}/result.json'
if gate.exists():raise RuntimeError('Immutable result exists')
with exclusive_lock(BASE/'control.lock'):
    write_json(gate,result)
    index_path=ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json'
    index=json.loads(index_path.read_text(encoding='utf-8-sig'))
    index['latest_optimization_v1_sys_imports']=dict(status=result['status'],result=str(gate.relative_to(ROOT)),
        sha256=sha256(gate),model_executed=False)
    write_json(index_path,index)
    state_path=BASE/'STATE.json';state=json.loads(state_path.read_text())
    state['results']['sys_imports']=str(gate.relative_to(ROOT))
    write_json(state_path,state)
print(json.dumps(result))
raise SystemExit(0 if result['status']=='PASS' else 1)
