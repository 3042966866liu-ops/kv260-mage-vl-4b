#!/usr/bin/env python3
import argparse, hashlib, json
from pathlib import Path

def sha256(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(4<<20),b""): h.update(b)
    return h.hexdigest()

def main():
    p=argparse.ArgumentParser(); p.add_argument("--root",type=Path,required=True); p.add_argument("--expected-manifest-sha256",required=True); a=p.parse_args()
    manifest_path=a.root/"PACKAGE_MANIFEST.json"
    if sha256(manifest_path)!=a.expected_manifest_sha256: raise RuntimeError("M193 manifest hash mismatch")
    m=json.loads(manifest_path.read_text())
    if m.get("gate")!="M193-Pillow-runtime-repair-bootstrap" or m.get("status")!="PASS": raise RuntimeError("M193 manifest identity mismatch")
    expected={x["path"] for x in m["files"]}|{"PACKAGE_MANIFEST.json"}; actual={x.name for x in a.root.iterdir() if x.is_file()}
    if actual!=expected: raise RuntimeError("M193 bootstrap closure mismatch")
    for x in m["files"]:
        f=a.root/x["path"]
        if f.stat().st_size!=x["bytes"] or sha256(f)!=x["sha256"]: raise RuntimeError(f"M193 member mismatch: {x['path']}")
    print("M193_BOOTSTRAP_VERIFY_PASS"); return 0
if __name__=="__main__": raise SystemExit(main())
