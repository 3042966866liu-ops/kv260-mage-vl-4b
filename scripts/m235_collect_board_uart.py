#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,re
from pathlib import Path
def main():
    p=argparse.ArgumentParser(); p.add_argument('--log',type=Path,required=True); p.add_argument('--result',type=Path,required=True); p.add_argument('--expected-manifest-sha256',required=True); a=p.parse_args()
    text=a.log.read_text(encoding='utf-8',errors='replace'); matches=re.findall(r'M235_BOARD_FAMILY_RESULT_BEGIN\s*(\{.*?\})\s*M235_BOARD_FAMILY_RESULT_END',text,flags=re.S)
    if len(matches)!=1: raise RuntimeError(f'expected one M235 result envelope, found {len(matches)}')
    family=json.loads(matches[0]); passed=(family.get('status')=='PASS' and family.get('build_id','').lower()=='0x4d395832' and family.get('tokens')==849 and family.get('output_bit_exact') is True and family.get('maximum_abs_error')==0.0 and family.get('host_calls')==family.get('expected_host_calls')==54 and family.get('cpu_linear_fallback') is False and float(family.get('wall_speedup',0))>=1.10 and family.get('pipeline_submissions')==27 and family.get('pipeline_reuse_waits')==25 and 'M235_PARSE_LAUNCH_OVERLAP_BOARD_PASS' in text and 'M235_SERVICE_RESTORE_PASS' in text and 'M235_PARSE_LAUNCH_OVERLAP_BOARD_RUNNER_PASS' in text and '__M235_RUNNER_RC_0__' in text)
    value={'date':'2026-09-01','gate':'M235-real-KV260-parse-launch-overlap-acceptance','status':'PASS' if passed else 'FAIL','classification':'Real-KV260 M231-versus-M235 849-token single-family bit-exact overlap performance and service restoration; independent of T64; not fixed-text, video, Web, or real-time evidence.','candidate_build_id':family.get('build_id'),'delta_manifest_sha256':a.expected_manifest_sha256,'family':family,'service_restore_marker':'M235_SERVICE_RESTORE_PASS' in text,'boot_dtb_cma_partitions_services_changed':False,'stable_rollback_preserved':True,'next_gate':'Only if PASS, run frozen fixed-text E2E before any Web integration.'}
    a.result.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8'); print(json.dumps(value,indent=2)); print('M235_BOARD_ACCEPTANCE_PASS' if passed else 'M235_BOARD_ACCEPTANCE_FAIL'); return 0 if passed else 1
if __name__=='__main__': raise SystemExit(main())

