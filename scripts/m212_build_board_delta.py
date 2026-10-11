#!/usr/bin/env python3
"""Build a clean hash-closed M212 board service delta and minimal predecessor summary."""
from __future__ import annotations
import hashlib,json,os,shutil,sys
from pathlib import Path

sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'tmp/m212_live_service/m212_live_delta'
RESULT=ROOT/'deployment/mage_vl4b/M212_LIVE_SERVICE_BOARD_DELTA_RESULT.json'
BOARD=ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json'
OFFLINE=ROOT/'deployment/mage_vl4b/M212_LATEST_ONLY_LIVE_HTTP_SSE_OFFLINE_RESULT.json'
SOURCE=ROOT/'deployment/mage_vl4b/m212_live_stream_source'

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
 board=json.loads(BOARD.read_text(encoding='utf-8')); offline=json.loads(OFFLINE.read_text(encoding='utf-8'))
 if offline.get('status')!='PASS' or sha(OFFLINE)!='c7ec9b9926c62baab8f7d84064d848a0dce68e286b6bd9a0f9e94a536c293983': raise RuntimeError('M212 offline predecessor mismatch')
 m179=board.get('latest_m120_fixed_text_board_gate',{});m198=board.get('latest_m198_ps_vision_optimization',{});m208=board.get('latest_m208_ps_vision_board_gate',{});m209=board.get('latest_m209_continuous_stream_core',{})
 if not (m179.get('status')=='PASS' and m179.get('formal_result_sha256')=='3a798eafd2e66974774dcdcac39de86243830a6a4771eb182cd535220b4aacd3' and m198.get('status')=='PASS' and m208.get('status')=='PASS' and m208.get('formal_result_sha256')=='2ff1d5823b97e349613abd15199e9db37630314a2d2c9b60fb4964658d47b23a' and str(m209.get('status','')).startswith('OFFLINE_PASS') and board.get('stable_rollback_preserved') is True): raise RuntimeError('M212 board predecessor closure mismatch')
 summary={'date':'2026-09-01','gate':'M212-live-predecessor-summary','status':'PASS','source_board_gate_sha256':sha(BOARD),'stable_rollback_preserved':True,'m179':{k:m179[k] for k in ('status','candidate_build_id','fpga_execution_proved','cpu_linear_fallback','formal_result_sha256')},'m198':{k:m198[k] for k in ('status','candidate_build_id','fp32_encoder_layers','formal_result_sha256')},'m208':{k:m208[k] for k in ('status','candidate_build_id','metrics','bf16_gemm_warning_count','formal_result_sha256')},'m209':{k:m209[k] for k in ('status','runtime_load_count','last_window_sequences','formal_result_sha256')},'m212_offline_result_sha256':sha(OFFLINE)}
 partial=OUT.with_name(OUT.name+'.partial')
 if OUT.exists(): shutil.rmtree(OUT)
 if partial.exists(): shutil.rmtree(partial)
 partial.mkdir(parents=True)
 summary_path=partial/'M212_PREDECESSOR_SUMMARY.json'; summary_path.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 sources={
  'video_server.py':SOURCE/'video_server.py','live_stream_core.py':SOURCE/'live_stream_core.py','m206_ps_vision_runtime.py':SOURCE/'m206_ps_vision_runtime.py','m207_ps_vision_runtime.py':SOURCE/'m207_ps_vision_runtime.py',
  'static/index.html':SOURCE/'static/index.html','static/app.js':SOURCE/'static/app.js','static/style.css':SOURCE/'static/style.css',
  'm212_verify_board_delta.py':ROOT/'scripts/m212_verify_board_delta.py','m212_health_probe.py':ROOT/'scripts/m212_health_probe.py','m212_board_preflight_and_start.sh':ROOT/'scripts/m212_board_preflight_and_start.sh',
  'M212_LATEST_ONLY_LIVE_HTTP_SSE_OFFLINE_RESULT.json':OFFLINE,
 }
 for name,source in sources.items():
  dest=partial/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,dest)
 entries=[]
 for path in sorted(p for p in partial.rglob('*') if p.is_file()):
  name=path.relative_to(partial).as_posix();entries.append({'path':name,'bytes':path.stat().st_size,'sha256':sha(path)})
 if any('__pycache__' in x['path'] or x['path'].endswith(('.pyc','.log','.partial')) for x in entries): raise RuntimeError('M212 forbidden package member')
 manifest={'date':'2026-09-01','gate':'M212-live-service-board-delta','status':'PASS','build_id':'0x4D395832','m208_formal_result_sha256':m208['formal_result_sha256'],'m212_offline_result_sha256':sha(OFFLINE),'files':entries,'file_count':len(entries),'total_bytes':sum(x['bytes'] for x in entries),'excluded_patterns':['__pycache__','*.pyc','*.log','*.partial'],'board_state_changed':False}
 (partial/'PACKAGE_MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');os.replace(partial,OUT)
 result={'date':'2026-09-01','gate':'M212-live-service-board-delta-build','status':'PASS','directory':OUT.relative_to(ROOT).as_posix(),'package_manifest_sha256':sha(OUT/'PACKAGE_MANIFEST.json'),'file_count':len(entries),'total_bytes':manifest['total_bytes'],'board_state_changed':False,'next_gate':'COM3 same-terminal sudo preflight, hash upload, board preflight and service start.'}
 RESULT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print('M212_BOARD_DELTA_BUILD_PASS');print(json.dumps(result,ensure_ascii=False,indent=2));return 0
if __name__=='__main__':raise SystemExit(main())
