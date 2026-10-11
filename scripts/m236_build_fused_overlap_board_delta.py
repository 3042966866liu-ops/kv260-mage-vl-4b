#!/usr/bin/env python3
"""Build a clean, hash-closed M236 runtime-only board delta."""
from __future__ import annotations
import hashlib, json, shutil
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'deployment/mage_vl4b/m236_fused_parse_overlap_source'
M230=ROOT/'deployment/mage_vl4b/m230_prefill_stage_once_source'
M231=ROOT/'deployment/mage_vl4b/m231_prefill_parse_reuse_source'
OUTPUT=ROOT/'deployment/mage_vl4b/m236_fused_parse_overlap_board_candidate'
OFFLINE=ROOT/'deployment/mage_vl4b/M236_FUSED_PARSE_OVERLAP_OFFLINE_RESULT.json'
RESULT=ROOT/'deployment/mage_vl4b/M236_FUSED_PARSE_OVERLAP_BOARD_DELTA_RESULT.json'
FILES=((M230/'m230_prefill_runtime.py','m230_prefill_runtime.py'),(M231/'m231_prefill_runtime.py','m231_prefill_runtime.py'),(SOURCE/'m236_prefill_runtime.py','m236_prefill_runtime.py'),(SOURCE/'m236_board_gate.py','m236_board_gate.py'),(M230/'m230_verify_package.py','m230_verify_package.py'),(SOURCE/'run_m236_board_gate.sh','run_m236_board_gate.sh'))
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    if OUTPUT.exists() or OUTPUT.with_name(OUTPUT.name+'.partial').exists(): raise RuntimeError(f'M236 clean output required: {OUTPUT}')
    offline=json.loads(OFFLINE.read_text(encoding='utf-8'))
    if offline.get('status')!='PASS' or offline.get('output_bit_exact') is not True or offline.get('injected_adaptive_retry_pass') is not True or offline.get('standalone_raw_finite_scan') is not False: raise RuntimeError('M236 offline predecessor mismatch')
    partial=OUTPUT.with_name(OUTPUT.name+'.partial'); partial.mkdir(parents=True); records=[]
    for source,relative in FILES:
        if not source.is_file(): raise RuntimeError(f'M236 missing source: {source}')
        destination=partial/relative; shutil.copy2(source,destination); records.append({'path':relative,'bytes':destination.stat().st_size,'sha256':sha(destination)})
    forbidden=[p.relative_to(partial).as_posix() for p in partial.rglob('*') if p.is_file() and (p.suffix=='.pyc' or '__pycache__' in p.parts)]
    if forbidden: raise RuntimeError(f'M236 forbidden cache files: {forbidden}')
    manifest={'date':'2026-09-01','gate':'M236-fused-parse-overlap-runtime-board-delta','status':'PASS','classification':'Clean runtime-only M231 dual-output fused-parse overlap delta for accepted M120 T32; independent of T64; no bitstream, weights, quantization, boot, DTB, CMA, partition, or persistent service mutation.','base_build_id':'0x4D395832','base_package_manifest_sha256':'406dcca340e4604baeb761445795391c43ec26bd99fa06ffae893d597b17414f','offline_result_sha256':sha(OFFLINE),'files':records,'file_count':len(records),'total_file_bytes':sum(r['bytes'] for r in records),'forbidden_cache_file_count':0,'board_state_changed':False}
    mp=partial/'PACKAGE_MANIFEST.json'; mp.write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8'); partial.replace(OUTPUT)
    result={'date':'2026-09-01','gate':'M236-fused-parse-overlap-board-delta-build','status':'PASS','directory':OUTPUT.relative_to(ROOT).as_posix(),'package_manifest_sha256':sha(OUTPUT/'PACKAGE_MANIFEST.json'),'file_count':len(records),'total_file_bytes':manifest['total_file_bytes'],'board_state_changed':False,'next_gate':'COM3 M231-versus-M236 849-token q-family bit-exact performance; require wall speedup >= 1.10 and service recovery on PASS or FAIL.'}
    tmp=RESULT.with_name(RESULT.name+'.partial'); tmp.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8'); tmp.replace(RESULT)
    print(json.dumps(result,indent=2)); print('M236_FUSED_PARSE_OVERLAP_BOARD_DELTA_BUILD_PASS'); return 0
if __name__=='__main__': raise SystemExit(main())
