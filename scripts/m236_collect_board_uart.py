#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, re
from pathlib import Path

def main():
    p=argparse.ArgumentParser(); p.add_argument('--log',type=Path,required=True); p.add_argument('--result',type=Path,required=True); p.add_argument('--expected-manifest-sha256',required=True); a=p.parse_args()
    text=a.log.read_text(encoding='utf-8',errors='replace')
    matches=re.findall(r'M236_BOARD_FAMILY_RESULT_BEGIN\s*(\{.*?\})\s*M236_BOARD_FAMILY_RESULT_END',text,flags=re.S)
    if len(matches)!=1: raise RuntimeError(f'M236 expected one family envelope, found {len(matches)}')
    family=json.loads(matches[0])
    service_restored=('M236_SERVICE_RESTORE_PASS' in text or 'M236_SERVICE_RESTORE_AFTER_FAILURE_PASS' in text)
    passed=(family.get('status')=='PASS' and service_restored and 'M236_FUSED_PARSE_OVERLAP_BOARD_RUNNER_PASS' in text)
    value={'date':'2026-09-01','gate':'M236-real-KV260-fused-parse-overlap-acceptance','status':'PASS' if passed else 'FAIL','classification':'Real-KV260 M231-versus-M236 849-token single-family bit-exact fused-parse overlap and service restoration; independent of T64; not fixed-text, video, Web, or real-time evidence.','candidate_build_id':family.get('build_id'),'delta_manifest_sha256':a.expected_manifest_sha256,'family':family,'service_restore_marker':service_restored,'boot_dtb_cma_partitions_services_changed':False,'stable_rollback_preserved':True,'next_gate':'Only if PASS, run frozen fixed-text E2E before any Web integration.'}
    partial=a.result.with_name(a.result.name+'.partial'); partial.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8'); partial.replace(a.result)
    print(json.dumps(value,indent=2)); print('M236_BOARD_ACCEPTANCE_PASS' if passed else 'M236_BOARD_ACCEPTANCE_FAIL'); return 0 if passed else 1
if __name__=='__main__': raise SystemExit(main())
