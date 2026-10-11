#!/usr/bin/env python3
"""Collect one M287 result and require stable M254 restoration."""
from __future__ import annotations
import argparse, json, os, re
from pathlib import Path

def main() -> int:
    parser=argparse.ArgumentParser(); parser.add_argument("--log",type=Path,required=True); parser.add_argument("--result",type=Path,required=True); parser.add_argument("--package-manifest-sha256",required=True); args=parser.parse_args()
    text=args.log.read_text(encoding="utf-8",errors="replace")
    matches=re.findall(r"__M287_BOARD_RESULT_BEGIN__\s*(.*?)\s*__M287_BOARD_RESULT_END__",text,flags=re.DOTALL)
    if len(matches)!=1: raise RuntimeError(f"M287 result envelope count {len(matches)}")
    result=json.loads(matches[0])
    if result.get("gate")!="M287-BACT-natural-151-real-KV260-single-fixture": raise RuntimeError("M287 gate identity mismatch")
    if result.get("package_manifest_sha256")!=args.package_manifest_sha256: raise RuntimeError("M287 package hash mismatch")
    restore=[int(value) for value in re.findall(r"__M287_RESTORE_RC_(\d+)__",text)]
    if not restore or restore[-1]!=0: raise RuntimeError(f"M287 restoration not proved {restore}")
    args.result.parent.mkdir(parents=True,exist_ok=True); partial=args.result.with_name(args.result.name+f".partial-{os.getpid()}"); partial.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"); os.replace(partial,args.result)
    passed=str(result.get("status","")).startswith("PASS")
    measurement=result.get("measurement") or {}
    print(f"M287_FORMAL_RESULT_{'PASS' if passed else 'FAIL'} tokens={measurement.get('prompt_tokens')} calls={measurement.get('observed_logical_fpga_calls')} restore_rc=0")
    return 0 if passed else 1
if __name__=="__main__": raise SystemExit(main())
