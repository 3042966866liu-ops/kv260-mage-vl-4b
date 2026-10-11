#!/usr/bin/env python3
"""Build a clean hash-locked M235 runtime-only board delta."""
from __future__ import annotations
import hashlib, json, shutil
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'deployment/mage_vl4b/m235_parse_launch_overlap_source'
M230=ROOT/'deployment/mage_vl4b/m230_prefill_stage_once_source'
M231=ROOT/'deployment/mage_vl4b/m231_prefill_parse_reuse_source'
OUTPUT=ROOT/'deployment/mage_vl4b/m235_parse_launch_overlap_board_candidate'
FILES=((M230/'m230_prefill_runtime.py','m230_prefill_runtime.py'),(M231/'m231_prefill_runtime.py','m231_prefill_runtime.py'),(SOURCE/'m235_prefill_runtime.py','m235_prefill_runtime.py'),(SOURCE/'m235_board_gate.py','m235_board_gate.py'),(M230/'m230_verify_package.py','m230_verify_package.py'),(SOURCE/'run_m235_board_gate.sh','run_m235_board_gate.sh'))
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    if OUTPUT.exists(): raise RuntimeError(f'M235 clean output already exists: {OUTPUT}')
    OUTPUT.mkdir(parents=True); records=[]
    for source,relative in FILES:
        if not source.is_file(): raise RuntimeError(f'M235 missing source: {source}')
        destination=OUTPUT/relative; shutil.copy2(source,destination)
        records.append({'path':relative,'bytes':destination.stat().st_size,'sha256':sha(destination)})
    manifest={'date':'2026-09-01','gate':'M235-parse-launch-overlap-runtime-board-delta','status':'PASS','classification':'Clean runtime-only M231 dual-output-buffer overlap delta for accepted M120 T32; independent of T64; no bitstream, weights, quantization, boot, DTB, CMA configuration, partition, or persistent service mutation.','base_build_id':'0x4D395832','base_package_manifest_sha256':'406dcca340e4604baeb761445795391c43ec26bd99fa06ffae893d597b17414f','offline_result_sha256':sha(ROOT/'deployment/mage_vl4b/M235_PARSE_LAUNCH_OVERLAP_OFFLINE_RESULT.json'),'files':records,'file_count':len(records),'total_file_bytes':sum(r['bytes'] for r in records),'forbidden_cache_file_count':0,'board_state_changed':False}
    mp=OUTPUT/'PACKAGE_MANIFEST.json'; mp.write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    result={'date':'2026-09-01','gate':'M235-parse-launch-overlap-board-delta-build','status':'PASS','directory':OUTPUT.relative_to(ROOT).as_posix(),'package_manifest_sha256':sha(mp),'file_count':len(records),'total_file_bytes':manifest['total_file_bytes'],'board_state_changed':False,'next_gate':'COM3 M231-versus-M235 849-token q-family bit-exact performance; require wall speedup >= 1.10.'}
    (ROOT/'deployment/mage_vl4b/M235_PARSE_LAUNCH_OVERLAP_BOARD_DELTA_RESULT.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2)); print('M235_PARSE_LAUNCH_OVERLAP_BOARD_DELTA_BUILD_PASS'); return 0
if __name__=='__main__': raise SystemExit(main())

