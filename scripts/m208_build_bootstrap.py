#!/usr/bin/env python3
"""Build clean, hash-closed M208 UART bootstrap."""
import hashlib,json,shutil
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'tmp/m208_ps_vision/m208_gate'
RESULT=ROOT/'deployment/mage_vl4b/M208_PS_VISION_BOOTSTRAP_RESULT.json'

def sha(path):
 d=hashlib.sha256();d.update(path.read_bytes());return d.hexdigest()

def main():
 if OUT.exists():shutil.rmtree(OUT)
 OUT.mkdir(parents=True)
 files={
  'ps_vision_runtime.py':ROOT/'deployment/mage_vl4b/m200_video_e2e_overlay_source/ps_vision_runtime.py',
  'm206_ps_vision_runtime.py':ROOT/'scripts/m206_ps_vision_runtime.py',
  'm207_ps_vision_runtime.py':ROOT/'scripts/m207_ps_vision_runtime.py',
  'm207_test_ps_vision_runtime.py':ROOT/'scripts/m207_test_ps_vision_runtime.py',
  'm208_ps_vision_board_gate.py':ROOT/'scripts/m208_ps_vision_board_gate.py',
  'm208_run_ps_vision.sh':ROOT/'scripts/m208_run_ps_vision.sh',
  'm208_verify_bootstrap.py':ROOT/'scripts/m208_verify_bootstrap.py',
  'M198_M197_PS_VISION_BOARD_RESULT_01.json':ROOT/'deployment/mage_vl4b/M198_M197_PS_VISION_BOARD_RESULT_01.json',
  'M207_OFFLINE_FP32_GEMM_M198_POLICY_RESULT_ATTEMPT02.json':ROOT/'deployment/mage_vl4b/M207_OFFLINE_FP32_GEMM_M198_POLICY_RESULT_ATTEMPT02.json',
 }
 for name,source in files.items():
  if not source.is_file():raise RuntimeError(f'M208 source missing: {source}')
  shutil.copy2(source,OUT/name)
 entries=[{'path':name,'bytes':(OUT/name).stat().st_size,'sha256':sha(OUT/name)} for name in sorted(files)]
 manifest={'gate':'M208-M207-FP32-W4-GEMM-bootstrap','status':'PASS','files':entries,'file_count':len(entries),'total_bytes':sum(x['bytes'] for x in entries)}
 mp=OUT/'PACKAGE_MANIFEST.json';mp.write_text(json.dumps(manifest,indent=2)+'\n')
 result={'gate':'M208-M207-FP32-W4-GEMM-bootstrap-build','status':'PASS','directory':str(OUT.relative_to(ROOT)).replace('\\','/'),'package_manifest_sha256':sha(mp),'file_count':len(entries),'total_bytes':manifest['total_bytes'],'board_state_changed':False}
 RESULT.write_text(json.dumps(result,indent=2)+'\n')
 print('M208_BOOTSTRAP_BUILD_PASS')
 return 0
if __name__=='__main__':raise SystemExit(main())

