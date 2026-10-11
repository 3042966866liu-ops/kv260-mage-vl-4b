#!/usr/bin/env python3
import argparse,json,os
from pathlib import Path

p=argparse.ArgumentParser();p.add_argument('--log',type=Path,required=True);p.add_argument('--result',type=Path,required=True);a=p.parse_args();text=a.log.read_text(encoding='utf-8',errors='replace');begin='__M208_PS_VISION_RESULT_BEGIN__';end='__M208_PS_VISION_RESULT_END__'
if text.count(begin)!=1 or text.count(end)!=1:raise RuntimeError('M208 UART envelope cardinality mismatch')
value=json.loads(text.split(begin,1)[1].split(end,1)[0].strip())
if value.get('gate')!='M208-M207-fixed-four-frame-PS-vision-FP32-W4-GEMM':raise RuntimeError('M208 result identity mismatch')
if value.get('status')=='PASS' and ('M208_PS_VISION_RUNNER_PASS' not in text or '__M208_PS_VISION_RUNNER_RC_0__' not in text):raise RuntimeError('M208 PASS runner proof mismatch')
a.result.parent.mkdir(parents=True,exist_ok=True);tmp=a.result.with_name(a.result.name+'.partial');tmp.write_text(json.dumps(value,indent=2)+'\n');os.replace(tmp,a.result)
print('M208_PS_VISION_UART_COLLECT_PASS' if value.get('status')=='PASS' else 'M208_PS_VISION_UART_COLLECT_FAIL')
raise SystemExit(0 if value.get('status')=='PASS' else 1)

