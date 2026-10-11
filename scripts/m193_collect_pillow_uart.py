#!/usr/bin/env python3
import argparse,json,os
from pathlib import Path

def main():
    p=argparse.ArgumentParser(); p.add_argument("--log",type=Path,required=True); p.add_argument("--result",type=Path,required=True); a=p.parse_args()
    text=a.log.read_text(encoding="utf-8",errors="replace"); begin=text.rfind("__M193_PILLOW_RESULT_BEGIN__"); end=text.rfind("__M193_PILLOW_RESULT_END__")
    if begin<0 or end<=begin: raise RuntimeError("M193 UART envelope missing")
    result=json.loads(text[begin:].splitlines()[1]); tmp=a.result.with_name(a.result.name+".partial"); tmp.parent.mkdir(parents=True,exist_ok=True); tmp.write_text(json.dumps(result,indent=2)+"\n"); os.replace(tmp,a.result)
    print("M193_PILLOW_UART_COLLECT_PASS" if result.get("status")=="PASS" else "M193_PILLOW_UART_COLLECT_FAIL"); return 0 if result.get("status")=="PASS" else 1
if __name__=="__main__": raise SystemExit(main())
