#!/usr/bin/env python3
import argparse,json,os
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--log',type=Path,required=True);p.add_argument('--result',type=Path,required=True);a=p.parse_args();text=a.log.read_text(encoding='utf-8',errors='replace');begin='__M212_BOARD_RESULT_BEGIN__';end='__M212_BOARD_RESULT_END__'
if text.count(begin)!=1 or text.count(end)!=1:raise RuntimeError('M212 UART result envelope mismatch')
value=json.loads(text.split(begin,1)[1].split(end,1)[0].strip())
if value.get('gate')!='M212-real-KV260-live-service-control-plane':raise RuntimeError('M212 board result identity mismatch')
if value.get('status')=='PASS' and ('M212_LIVE_SERVICE_BOARD_START_PASS' not in text or '__M212_LIVE_RUNNER_RC_0__' not in text):raise RuntimeError('M212 runner PASS proof missing')
a.result.parent.mkdir(parents=True,exist_ok=True);tmp=a.result.with_name(a.result.name+'.partial');tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');os.replace(tmp,a.result)
print('M212_BOARD_UART_COLLECT_PASS' if value.get('status')=='PASS' else 'M212_BOARD_UART_COLLECT_FAIL');raise SystemExit(0 if value.get('status')=='PASS' else 1)
