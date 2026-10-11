#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json,os
from pathlib import Path
def find(text):
 end=max(text.rfind('M120_FIXED_TEXT_E2E_PASS'),text.rfind('M120_FIXED_TEXT_E2E_FAIL'))
 if end<0:raise RuntimeError('M168 fixed-text marker missing')
 d=json.JSONDecoder();v=[]
 for i,c in enumerate(text[:end]):
  if c!='{':continue
  try:x,_=d.raw_decode(text[i:end])
  except json.JSONDecodeError:continue
  if isinstance(x,dict) and x.get('gate')=='M120-fixed-text-E2E':v.append(x)
 if len(v)!=1:raise RuntimeError(f'M168 expected one result, observed={len(v)}')
 return v[0]
def main():
 p=argparse.ArgumentParser();p.add_argument('--log',type=Path,required=True);p.add_argument('--result',type=Path,required=True);p.add_argument('--layer0',type=Path,required=True);a=p.parse_args()
 x=find(a.log.read_text(encoding='utf-8',errors='replace'));e=x.get('evidence',{})
 if x.get('status') not in {'PASS','FAIL'} or x.get('cpu_linear_fallback') is not False:raise RuntimeError('M168 result identity mismatch')
 if x.get('status')=='PASS':
  ok=x.get('reference_match') is True and x.get('fpga_execution_proved') is True and x.get('expected_calls')==162 and e.get('logical_calls')==162 and str(e.get('build_id','')).lower()=='0x4d395832'
  if not ok:raise RuntimeError('M168 PASS lacks fixed-text FPGA proof')
 x.update({'candidate_build_id':'0x4D395832','package_manifest_sha256':'34662ca90cb45b9a1d34903538b030f28b1f9f70ece3f35e7ccbbaf6eb3bbf97','m167_formal_result':a.layer0.as_posix(),'m167_formal_result_sha256':hashlib.sha256(a.layer0.read_bytes()).hexdigest(),'uart_log':a.log.as_posix(),'uart_log_sha256':hashlib.sha256(a.log.read_bytes()).hexdigest(),'evidence_level':'L5 fixed-reference M120 text E2E; not arbitrary prompt/Web'})
 t=a.result.with_name(a.result.name+'.partial');t.write_text(json.dumps(x,indent=2)+'\n',encoding='utf-8');os.replace(t,a.result)
 print(json.dumps(x,indent=2));print('M168_M120_FIXED_TEXT_COLLECT_PASS' if x['status']=='PASS' else 'M168_M120_FIXED_TEXT_COLLECT_FAIL');return 0 if x['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
