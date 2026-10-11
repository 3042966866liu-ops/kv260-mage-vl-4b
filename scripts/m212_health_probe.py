#!/usr/bin/env python3
"""Bounded local health probe and atomic M212 board service result."""
import argparse,json,os,time,urllib.request
from pathlib import Path
p=argparse.ArgumentParser(); p.add_argument('--url',required=True); p.add_argument('--preflight',type=Path,required=True); p.add_argument('--package-manifest-sha256',required=True); p.add_argument('--pid',type=int,required=True); p.add_argument('--result',type=Path,required=True); a=p.parse_args()
pre=json.loads(a.preflight.read_text(encoding='utf-8'))
if pre.get('status')!='PASS': raise RuntimeError('M212 service preflight is not PASS')
deadline=time.monotonic()+20; health=None; error=None
while time.monotonic()<deadline:
 try:
  with urllib.request.urlopen(a.url,timeout=3) as response: health=json.loads(response.read().decode('utf-8'))
  if health.get('mode')=='continuous-latest-only' and health.get('status')=='idle': break
 except Exception as exc: error=f'{type(exc).__name__}: {exc}'
 time.sleep(1)
status='PASS' if health and health.get('mode')=='continuous-latest-only' and health.get('status')=='idle' else 'FAIL'
value={'date':'2026-09-01','gate':'M212-real-KV260-live-service-control-plane','status':status,'classification':'Real-KV260 hash-verified latest-only HTTP/SSE service process and local health endpoint; no camera frames or model inference executed yet.','package_manifest_sha256':a.package_manifest_sha256,'service_pid':a.pid,'local_health':health,'error':error,'candidate_build_id':'0x4D395832','continuous_stream_inference_executed':False,'web_deployed':False,'boot_dtb_cma_partitions_services_changed':False,'stable_rollback_preserved':True,'next_gate':'Verify Windows-to-board HTTP, then submit a real continuous camera stream and retain the first complete FPGA-backed window.'}
a.result.parent.mkdir(parents=True,exist_ok=True); temporary=a.result.with_name(a.result.name+'.partial'); temporary.write_text(json.dumps(value,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8'); os.replace(temporary,a.result)
print('__M212_BOARD_RESULT_BEGIN__'); print(json.dumps(value,ensure_ascii=False,separators=(',',':'))); print('__M212_BOARD_RESULT_END__'); print('M212_LIVE_SERVICE_BOARD_CONTROL_PASS' if status=='PASS' else 'M212_LIVE_SERVICE_BOARD_CONTROL_FAIL')
raise SystemExit(0 if status=='PASS' else 1)
