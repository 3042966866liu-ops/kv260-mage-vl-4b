#!/usr/bin/env python3
import argparse,json,os
from pathlib import Path
def main():
 p=argparse.ArgumentParser();p.add_argument('--log',type=Path,required=True);p.add_argument('--result',type=Path,required=True);a=p.parse_args();t=a.log.read_text(encoding='utf-8',errors='replace');b=t.rfind('__M198_PS_VISION_RESULT_BEGIN__');e=t.rfind('__M198_PS_VISION_RESULT_END__')
 if b<0 or e<=b:raise RuntimeError('M198 UART envelope missing')
 r=json.loads(t[b:].splitlines()[1]);tmp=a.result.with_name(a.result.name+'.partial');tmp.parent.mkdir(parents=True,exist_ok=True);tmp.write_text(json.dumps(r,indent=2)+'\n');os.replace(tmp,a.result);print('M198_PS_VISION_UART_COLLECT_PASS' if r.get('status')=='PASS' else 'M198_PS_VISION_UART_COLLECT_FAIL');return 0 if r.get('status')=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
