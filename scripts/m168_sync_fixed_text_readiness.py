#!/usr/bin/env python3
import hashlib,json,os
from pathlib import Path
R=Path(__file__).resolve().parents[1];Q=R/'deployment/mage_vl4b/M168_M120_FIXED_TEXT_READINESS_RESULT.json';B=R/'deployment/mage_vl4b/BOARD_GATE_RESULT.json'
def H(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def W(p,s):t=p.with_name(p.name+'.partial');t.write_text(s,encoding='utf-8');os.replace(t,p)
v=json.loads(Q.read_text(encoding='utf-8'))
if v.get('status')!='PASS_OFFLINE_READINESS_M167_LOCKED':raise RuntimeError('M168 readiness not pass')
d=json.loads(B.read_text(encoding='utf-8'));d['latest_m120_corrected_fixed_text_readiness']={**v,'formal_result':Q.relative_to(R).as_posix(),'formal_result_sha256':H(Q)};d['full_model_deployed']=False;d['web_deployed']=False;W(B,json.dumps(d,indent=2)+'\n')
body=f'''## M168: corrected fixed-text board gate is ready and locked behind M167 (2026-09-01)

The COM3-only M168 controller requires the exact M167 real-board Layer-0 PASS and the SHA-256 of the original board `layer0_acceptance.json`. It then runs one frozen 30-token/one-token E2E with Build `0x4D395832`, `162` logical FPGA calls, `staged-low-cma`, and `cpu_linear_fallback=false`. Versioned receiver/checker/runner sources, fixed FTDI identity, missing-M167 negative lock and shell/Python/PowerShell checks pass. No board execution occurred.

Evidence: `{Q.relative_to(R).as_posix()}` (SHA-256 `{H(Q)}`).'''
for name in ('CURRENT_STATE.md','docsMILESTONES.md'):
 p=R/name;s=p.read_text(encoding='utf-8');a='<!-- M168_FIXED_TEXT_READINESS_START -->';z='<!-- M168_FIXED_TEXT_READINESS_END -->';block=a+'\n'+body+'\n'+z+'\n\n'
 if a in s:x,y=s.split(a,1);_,q=y.split(z,1);s=x+block+q.lstrip('\r\n')
 else:
  lines=s.splitlines(keepends=True);i=1 if lines and lines[0].startswith('# ') else 0;s=''.join(lines[:i])+('\n' if i else '')+block+''.join(lines[i:])
 W(p,s)
print(json.dumps({'status':'PASS','result_sha256':H(Q),'board_gate_result_sha256':H(B)},indent=2));print('M168_FIXED_TEXT_READINESS_SYNC_PASS')
