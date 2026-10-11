"""Persist UART layer evidence, including failures, with report/state backups."""
import argparse
import json
from pathlib import Path
import re
import shutil
from measurement import sha256, write_json, exclusive_lock

parser=argparse.ArgumentParser();parser.add_argument('mode',choices=('import','stable','candidate'))
parser.add_argument('--ab', action='store_true')
args=parser.parse_args()
root=Path(__file__).resolve().parents[2];base=root/'deployment/mage_vl4b/optimization_v1'
log=root/('tmp/op01_decode_one_ab01' if args.ab else 'tmp/op01_decode_one_layer01')/ (args.mode+'.log')
text=log.read_text(encoding='utf-8-sig')
if text.count('LAYER_JSON_BEGIN')!=1 or text.count('LAYER_JSON_END')!=1:raise RuntimeError('Incomplete envelope')
result=json.loads(text.split('LAYER_JSON_BEGIN')[1].split('LAYER_JSON_END')[0])
match=re.search(r'__OP01_LAYER_RC_(\d+)__',text)
if not match:raise RuntimeError('Process has not exited; do not infer termination')
code=int(match[1]);result['controller_exit_code']=code
if result['status'].startswith('PASS_') and code!=0:raise RuntimeError('Contradictory exit')
if args.mode!='import' and result['status'].startswith('PASS_'):
    if not result['stable_restored'] or result['recovery_required']:raise RuntimeError('Recovery not verified')
    if not result['boot_unchanged'] or not result['cmdline_unchanged']:raise RuntimeError('Boot state changed')
if args.mode=='candidate' and result['status']=='PASS_CANDIDATE_LAYER_EXACT':
    if set(result['comparisons'])!={'hidden','key','value'} or not all(v['bit_exact'] for v in result['comparisons'].values()):
        raise RuntimeError('Exact tensor coverage missing')
if args.mode=='candidate' and result['status']=='PASS_CANDIDATE_DECODE_EXACT':
    stable=json.loads((base/'runs/OP01-decode-one-ab-stable-01/result.json').read_text())
    if set(result['comparisons'])!={'logits'} or not result['comparisons']['logits']['bit_exact']:
        raise RuntimeError('Full logits comparison missing')
    if result['kv_sha256']!=stable['kv_sha256'] or len(result['kv_sha256'])!=72:
        raise RuntimeError('Full KV comparison missing')
    if result['output_token']!=stable['output_token']:raise RuntimeError('Token differs')
tag='ab' if args.ab else 'layer'
out=base/('runs/OP01-decode-one-'+tag+'-'+args.mode+'-01')
next_action='Run candidate layer with exact stable reference SHA' if args.mode=='stable' else (
    'Run fixed KV852 stable/candidate complete Decode A/B with matched cache preparation' if args.mode=='candidate' and result['status'].startswith('PASS_') else
    'Run stable layer reference' if args.mode=='import' else 'Debug only failed layer/import level; no full Decode')
if args.ab:
    next_action=('Run candidate complete Decode with exact stable reference SHA' if args.mode=='stable' else
                 'Review matched single-step costs, then short continuous Decode and bounded repeated A/B' if args.mode=='candidate' and result['status'].startswith('PASS_') else
                 'Run stable complete Decode reference' if args.mode=='import' else 'Debug failed Decode level only')
note=f'''## Decode-one {('完整单步' if args.ab else '单层')}阶段：{args.mode}（2026-09-25）

状态{result['status']}，Build {result['build_id']}，计算段耗时{result.get('decode_seconds',result.get('layer_seconds','未运行'))}秒。
输入Token {result.get('input_token')} / KV852；稳定恢复{result['stable_restored']}，恢复待办{result['recovery_required']}。
{('完整单步使用固定两遍预读；预读成本单列，不证明页面始终驻留，也不代表128 Token正式吞吐。' if args.ab else '此为单层/导入证据，不是完整Decode性能；缓存条件未作性能配对，禁止据此宣布加速比。')}
错误：{result['errors']}。
证据{out.relative_to(root).as_posix()}/result.json；保存原始串口日志、板端完整结果SHA和更新前状态。
下一步：{next_action}。容量专项仍STOPPED_BY_USER_NOT_PASS，稳定boot/DTB/CMA不修改。

'''
with exclusive_lock(base/'evidence.lock'):
    out.mkdir(parents=True,exist_ok=False);backup=out/'state_before_update';backup.mkdir()
    board_path=root/'deployment/mage_vl4b/BOARD_GATE_RESULT.json'
    for p in (root/'CURRENT_STATE.md',root/'docsMILESTONES.md',board_path,base/'STATE.json'):shutil.copy2(p,backup/p.name)
    shutil.copy2(log,out/'uart.log');write_json(out/'result.json',result)
    (out/'REPORT.md').write_text('# Decode-one 验证\n\n'+note,encoding='utf-8')
    for p in (root/'CURRENT_STATE.md',root/'docsMILESTONES.md'):
        old=p.read_bytes();split=old.find(b'\n')+1;tmp=p.with_suffix('.layer.partial')
        tmp.write_bytes(old[:split]+b'\n'+note.encode('utf-8')+old[split:]);tmp.replace(p)
    board=json.loads(board_path.read_text(encoding='utf-8-sig'))
    board['latest_decode_one_'+tag+'_'+args.mode]=dict(status=result['status'],build_id=result['build_id'],
        result=str((out/'result.json').relative_to(root)),sha256=sha256(out/'result.json'),
        stable_restored=result['stable_restored'],performance_pass=False,next_action=next_action)
    write_json(board_path,board)
    state=json.loads((base/'STATE.json').read_text(encoding='utf-8-sig'))
    state['results']['decode_one_'+tag+'_'+args.mode]=str((out/'result.json').relative_to(root))
    state['next_action']=next_action;write_json(base/'STATE.json',state)
    write_json(out/'BACKUP_MANIFEST.json',{p.relative_to(out).as_posix():sha256(p) for p in out.rglob('*') if p.is_file()})
print(result['status'])
