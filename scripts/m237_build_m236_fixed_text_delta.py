#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,shutil
from pathlib import Path
R=Path(__file__).resolve().parents[1]; S=R/'deployment/mage_vl4b/m237_m236_fixed_text_source'; M230=R/'deployment/mage_vl4b/m230_prefill_stage_once_source'; M231=R/'deployment/mage_vl4b/m231_prefill_parse_reuse_source'; M236=R/'deployment/mage_vl4b/m236_fused_parse_overlap_source'; F=R/'deployment/mage_vl4b/M236_FUSED_PARSE_OVERLAP_BOARD_RESULT_01.json'; O=R/'deployment/mage_vl4b/m237_m236_fixed_text_board_candidate'; RES=R/'deployment/mage_vl4b/M237_M236_FIXED_TEXT_BOARD_DELTA_RESULT.json'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    if O.exists(): raise RuntimeError('M237 clean output required')
    formal=json.loads(F.read_text()); family=formal['family']
    if formal.get('status')!='PASS' or family.get('status')!='PASS': raise RuntimeError('M237 requires M236 PASS')
    family_bytes=(json.dumps(family,indent=2)+'\n').encode(); predecessor={'date':'2026-09-01','gate':'M237-M236-exact-board-predecessor','status':'PASS','m236_formal_result_sha256':sha(F),'board_family_measurement_sha256':hashlib.sha256(family_bytes).hexdigest(),'build_id':'0x4D395832','tokens':849,'output_sha256_fp32':'ec6d680770fbac413cf51076656f206defc78edf4e92cfb41fc1a60c58d1f81e'}
    P=O.with_name(O.name+'.partial'); P.mkdir(parents=True)
    files=((M230/'m230_prefill_runtime.py','m230_prefill_runtime.py'),(M231/'m231_prefill_runtime.py','m231_prefill_runtime.py'),(M236/'m236_prefill_runtime.py','m236_prefill_runtime.py'),(S/'m236_fixed_text_gate.py','m236_fixed_text_gate.py'),(S/'m237_verify_predecessor.py','m237_verify_predecessor.py'),(S/'m237_accept_fixed_text.py','m237_accept_fixed_text.py'),(M230/'m230_verify_package.py','m230_verify_package.py'),(S/'run_m237_fixed_text_gate.sh','run_m237_fixed_text_gate.sh'))
    for src,name in files: shutil.copy2(src,P/name)
    (P/'M236_PREDECESSOR_SUMMARY.json').write_text(json.dumps(predecessor,indent=2)+'\n')
    rec=[{'path':p.name,'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(P.iterdir())]; manifest={'date':'2026-09-01','gate':'M237-M236-fixed-text-runtime-board-delta','status':'PASS','classification':'Clean runtime-only M236 fixed-text delta; no bitstream, weights, quantization, boot, DTB, CMA, partition, or persistent service mutation.','base_build_id':'0x4D395832','base_package_manifest_sha256':'406dcca340e4604baeb761445795391c43ec26bd99fa06ffae893d597b17414f','files':rec,'file_count':len(rec),'total_file_bytes':sum(x['bytes'] for x in rec),'forbidden_cache_file_count':0,'board_state_changed':False}; (P/'PACKAGE_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n'); P.replace(O)
    result={'date':'2026-09-01','gate':'M237-M236-fixed-text-board-delta-build','status':'PASS','directory':O.relative_to(R).as_posix(),'package_manifest_sha256':sha(O/'PACKAGE_MANIFEST.json'),'file_count':len(rec),'total_file_bytes':manifest['total_file_bytes'],'board_state_changed':False,'next_gate':'COM3 exact M236 predecessor plus frozen fixed-text complete 4B E2E.'}; RES.write_text(json.dumps(result,indent=2)+'\n'); print(json.dumps(result,indent=2)); print('M237_M236_FIXED_TEXT_DELTA_BUILD_PASS'); return 0
if __name__=='__main__': raise SystemExit(main())
