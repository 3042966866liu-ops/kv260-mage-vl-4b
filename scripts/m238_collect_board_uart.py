#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, re
from pathlib import Path

def main():
    p=argparse.ArgumentParser(); p.add_argument('--log',type=Path,required=True); p.add_argument('--result',type=Path,required=True); p.add_argument('--expected-manifest-sha256',required=True); a=p.parse_args()
    text=a.log.read_text(encoding='utf-8',errors='replace')
    matches=re.findall(r'M238_BOARD_FAMILY_RESULT_BEGIN\s*(\{.*?\})\s*M238_BOARD_FAMILY_RESULT_END',text,flags=re.S)
    if len(matches)!=1: raise RuntimeError(f'M238 expected one family envelope, found {len(matches)}')
    family=json.loads(matches[0])
    restored=('M238_SERVICE_RESTORE_PASS' in text or 'M238_SERVICE_RESTORE_AFTER_FAILURE_PASS' in text)
    passed=family.get('status')=='PASS' and restored and 'M238_INPUT_PREFETCH_BOARD_RUNNER_PASS' in text
    value={'date':'2026-09-01','gate':'M238-real-KV260-input-pack-prefetch-acceptance','status':'PASS' if passed else 'FAIL','classification':'Real KV260 M236-versus-M238 849-token q-family bit-exact host-pipeline gate; independent of T64; not fixed-text, video, Web, or real-time evidence.','candidate_build_id':family.get('build_id'),'delta_manifest_sha256':a.expected_manifest_sha256,'family':family,'service_restore_marker':restored,'boot_dtb_cma_partitions_services_changed':False,'stable_rollback_preserved':True,'next_gate':'If PASS, profile full 849-token language Prefill by phase before deciding Web integration; if rejected, retain M236.'}
    partial=a.result.with_name(a.result.name+'.partial'); partial.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8'); partial.replace(a.result)
    print(json.dumps(value,indent=2)); print('M238_BOARD_ACCEPTANCE_PASS' if passed else 'M238_BOARD_ACCEPTANCE_FAIL'); return 0 if passed else 1
if __name__=='__main__': raise SystemExit(main())
