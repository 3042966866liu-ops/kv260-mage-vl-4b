#!/usr/bin/env python3
import hashlib,json,os,shutil,sys
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/"tmp/m193_pillow/m193_bootstrap"; RESULT=ROOT/"deployment/mage_vl4b/M193_PILLOW_BOOTSTRAP_RESULT.json"
def sha256(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(4<<20),b""): h.update(b)
    return h.hexdigest()
def main():
    if OUT.exists() or OUT.with_name(OUT.name+".partial").exists(): raise RuntimeError("M193 clean bootstrap required")
    s=OUT.with_name(OUT.name+".partial"); s.mkdir(parents=True)
    sources={n:ROOT/f"scripts/{n}" for n in ["m193_pillow_board_repair.py","m193_run_pillow_repair.sh","m193_verify_bootstrap.py"]}; entries=[]
    for n,src in sources.items():
        dst=s/n; shutil.copyfile(src,dst); entries.append({"path":n,"bytes":dst.stat().st_size,"sha256":sha256(dst)})
    manifest={"date":"2026-09-01","gate":"M193-Pillow-runtime-repair-bootstrap","status":"PASS","pillow_sha256":"a40905599d8079e09f25027423aed94f2823adaf2868940de991e53a449e14a8","files":entries,"file_count":3}
    (s/"PACKAGE_MANIFEST.json").write_text(json.dumps(manifest,indent=2)+"\n"); os.replace(s,OUT)
    result={"date":"2026-09-01","gate":"M193-Pillow-runtime-repair-bootstrap-build","status":"PASS","directory":OUT.relative_to(ROOT).as_posix(),"package_manifest_sha256":sha256(OUT/"PACKAGE_MANIFEST.json"),"file_count":3,"board_state_changed":False}
    tmp=RESULT.with_name(RESULT.name+".partial"); tmp.write_text(json.dumps(result,indent=2)+"\n"); os.replace(tmp,RESULT); print(json.dumps(result,indent=2)); print("M193_BOOTSTRAP_BUILD_PASS"); return 0
if __name__=="__main__": raise SystemExit(main())
