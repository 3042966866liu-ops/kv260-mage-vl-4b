#!/usr/bin/env python3
import hashlib,json,os,shutil,sys
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'tmp/m192_ps_vision/m192_gate_v2';RESULT=ROOT/'deployment/mage_vl4b/M192_PS_VISION_BOOTSTRAP_V2_RESULT.json'
M184=ROOT/'deployment/mage_vl4b/M184_M181_VIDEO_BOARD_IMPORT_RESULT_01.json';M193=ROOT/'deployment/mage_vl4b/M193_PILLOW_RUNTIME_REPAIR_RESULT_01.json'
M184_SHA='790bae8a261156e95b23d7aa349d9410dc3d511388a94ad9be80106ce8a2cf84';M193_SHA='80cee9d8a23f84424c3d69c6ceb354d7e5e8ba07e9078970227ca5609eee3906'
def sha256(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(4<<20),b''):h.update(b)
 return h.hexdigest()
def main():
 if sha256(M184)!=M184_SHA or sha256(M193)!=M193_SHA or json.loads(M193.read_text()).get('status')!='PASS':raise RuntimeError('M192 predecessor mismatch')
 if OUT.exists() or OUT.with_name(OUT.name+'.partial').exists():raise RuntimeError('M192 clean output required')
 s=OUT.with_name(OUT.name+'.partial');s.mkdir(parents=True)
 sources={'m192_video_ps_vision_board_gate.py':ROOT/'scripts/m192_video_ps_vision_board_gate.py','m192_run_video_ps_vision_board_gate.sh':ROOT/'scripts/m192_run_video_ps_vision_board_gate.sh','m192_verify_bootstrap.py':ROOT/'scripts/m192_verify_bootstrap.py','M184_M181_VIDEO_BOARD_IMPORT_RESULT_01.json':M184,'M193_PILLOW_RUNTIME_REPAIR_RESULT_01.json':M193};entries=[]
 for n,src in sources.items():
  dst=s/n;shutil.copyfile(src,dst);entries.append({'path':n,'bytes':dst.stat().st_size,'sha256':sha256(dst)})
 m={'date':'2026-09-01','gate':'M192-isolated-runtime-PS-vision-bootstrap','status':'PASS','m184_sha256':M184_SHA,'m193_sha256':M193_SHA,'files':entries,'file_count':len(entries)}
 (s/'PACKAGE_MANIFEST.json').write_text(json.dumps(m,indent=2)+'\n');os.replace(s,OUT)
 r={'date':'2026-09-01','gate':'M192-isolated-runtime-PS-vision-bootstrap-v2-build','status':'PASS','directory':OUT.relative_to(ROOT).as_posix(),'package_manifest_sha256':sha256(OUT/'PACKAGE_MANIFEST.json'),'m193_sha256':M193_SHA,'file_count':len(entries),'board_state_changed':False};tmp=RESULT.with_name(RESULT.name+'.partial');tmp.write_text(json.dumps(r,indent=2)+'\n');os.replace(tmp,RESULT);print(json.dumps(r,indent=2));print('M192_BOOTSTRAP_V2_BUILD_PASS');return 0
if __name__=='__main__':raise SystemExit(main())
