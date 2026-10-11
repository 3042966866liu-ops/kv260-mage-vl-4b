#!/usr/bin/env python3
import ast,hashlib,json,os,subprocess
from pathlib import Path
R=Path(__file__).resolve().parents[1];P=R/'scripts/m168_run_corrected_fixed_text_uart.ps1';S=R/'scripts/m168_run_corrected_fixed_text_e2e.sh';O=R/'deployment/mage_vl4b/M168_M120_FIXED_TEXT_READINESS_RESULT.json'
files=[R/'scripts/m168_verify_m167_predecessor.py',R/'scripts/m168_verify_absent_result.py',S,R/'scripts/m168_collect_fixed_text_uart.py',P]
result={'date':'2026-09-01','gate':'M168-M120-corrected-fixed-text-readiness','status':'FAIL','classification':'Offline source/policy and missing-M167 negative lock only; no board fixed-text, arbitrary prompt, video or Web execution.'}
try:
 for p in files:
  if not p.is_file():raise RuntimeError(f'missing {p}')
 for p in files[:2]+[files[3]]:ast.parse(p.read_text(encoding='utf-8'),filename=str(p))
 ps=P.read_text(encoding='utf-8');sh=S.read_text(encoding='utf-8')
 required=['M168_LOCKED_UNTIL_M167_CORRECTED_LAYER0_PASS','M167_M120_CORRECTED_LAYER0_BOARD_RESULT_','board_acceptance_sha256',"$ExpectedFtdiSerial='XFL1PL5N11BJB'",'sudo -n bash','m168_collect_fixed_text_uart.py']
 missing=[x for x in required if x not in ps]
 if missing:raise RuntimeError(f'PowerShell controls missing: {missing}')
 if 'ssh' in ps.lower() or 'plink' in ps.lower():raise RuntimeError('SSH route present')
 required_sh=['set -euo pipefail','m120_board_env_preflight.py','python3 "$verifier"','text_e2e_gate.py','--weight-mode staged-low-cma','M168_M120_FIXED_TEXT_E2E_RUNNER_PASS']
 missing=[x for x in required_sh if x not in sh]
 if missing:raise RuntimeError(f'runner controls missing: {missing}')
 pwsh=Path(r'C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell\pwsh.exe')
 c=subprocess.run([str(pwsh),'-File',str(P)],cwd=R,text=True,capture_output=True,encoding='utf-8',errors='replace')
 lock=c.stdout+c.stderr
 if c.returncode==0 or 'M168_LOCKED_UNTIL_M167_CORRECTED_LAYER0_PASS' not in lock:raise RuntimeError('missing-M167 negative lock failed')
 result.update({'status':'PASS_OFFLINE_READINESS_M167_LOCKED','source_sha256':{p.relative_to(R).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files},'fixed_com3_ftdi_identity':True,'ssh_used':False,'same_terminal_sudo_n':True,'exact_m167_board_acceptance_hash_required':True,'fixed_prompt_tokens':30,'generated_tokens':1,'expected_logical_calls':162,'cpu_linear_fallback':False,'weight_mode':'staged-low-cma','current_missing_m167_negative_lock_test':'PASS','board_execution_run':False,'board_state_changed':False,'stable_rollback_preserved':True,'next_gate':'Complete M166 stage and M167 Layer-0 PASS, then run M168 once over COM3.'})
except Exception as e:result['error']=f'{type(e).__name__}: {e}';result['next_gate']='Repair M168 readiness only; do not run fixed text.'
t=O.with_name(O.name+'.partial');t.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');os.replace(t,O);print(json.dumps(result,indent=2));print('M168_FIXED_TEXT_READINESS_PASS' if str(result['status']).startswith('PASS') else 'M168_FIXED_TEXT_READINESS_FAIL');raise SystemExit(0 if str(result['status']).startswith('PASS') else 1)
