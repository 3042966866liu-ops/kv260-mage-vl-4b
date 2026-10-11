#!/usr/bin/env python3
import hashlib,json,os
from pathlib import Path
R=Path(__file__).resolve().parents[1]
def H(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def W(p,v):
 t=p.with_name(p.name+'.partial');t.write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8');os.replace(t,p)
def M(p,a,b,body):
 s=p.read_text(encoding='utf-8');block=a+'\n'+body.rstrip()+'\n'+b+'\n\n'
 if a in s:
  x,y=s.split(a,1);_,z=y.split(b,1);s=x+block+z.lstrip('\r\n')
 else:
  lines=s.splitlines(keepends=True);i=1 if lines and lines[0].startswith('# ') else 0;s=''.join(lines[:i])+('\n' if i else '')+block+''.join(lines[i:])
 t=p.with_name(p.name+'.partial');t.write_text(s,encoding='utf-8');os.replace(t,p)
q=R/'deployment/mage_vl4b/M169_M120_VIDEO_BUILDER_CORRECTION_READINESS_RESULT.json';v=json.loads(q.read_text(encoding='utf-8'))
if v.get('status')!='PASS_CORRECTED_BUILDER_READY_TEXT_E2E_LOCKED':raise RuntimeError('M169 not pass')
p=R/'deployment/mage_vl4b/BOARD_GATE_RESULT.json';d=json.loads(p.read_text(encoding='utf-8'))
d['latest_m120_video_builder_correction']={**v,'formal_result':q.relative_to(R).as_posix(),'formal_result_sha256':H(q)}
d['full_model_deployed']=False;d['web_deployed']=False;d['stable_rollback_preserved']=True
W(p,d)
body=f'''## M169: video 4B builder excludes fixed-text-only auxiliary state (2026-09-01)

The video language runtime still uses Build `0x4D395832`, the M120 split-Q/KV schedule, full M120 W3 embedding, PS BF16/W4 vision, four-frame preprocessing and SSE. The corrected builder now copies only eight hash-locked text runtime/overlay/contract files from the M165 package. It explicitly excludes `text_runtime/auxiliary`, Layer-0 reference fixtures and the old fixed-prompt embedding payload. The negative fixed-text lock still passes, so no video package was generated and no board state changed.

Evidence: `{q.relative_to(R).as_posix()}` (SHA-256 `{H(q)}`).'''
M(R/'CURRENT_STATE.md','<!-- M169_VIDEO_CORRECTION_START -->','<!-- M169_VIDEO_CORRECTION_END -->',body)
M(R/'docsMILESTONES.md','<!-- M169_VIDEO_CORRECTION_START -->','<!-- M169_VIDEO_CORRECTION_END -->',body)
print(json.dumps({'status':'PASS','result_sha256':H(q),'board_gate_result_sha256':H(p)},indent=2));print('M169_VIDEO_CORRECTION_SYNC_PASS')
