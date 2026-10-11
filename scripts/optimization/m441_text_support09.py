"""Check only the new M441 layer entry, identities, controller and byte recovery."""
import base64
import copy
import json
import subprocess
import sys
from pathlib import Path
import m351_workflow as w
from m441_host_io08 import atomic
import m441_text_collect09 as c

def emit(r):
    raw=w.encoded(r);parts=[raw[i:i+900] for i in range(0,len(raw),900)]
    return 'M441T_RESULT_SHA256='+__import__('hashlib').sha256(raw).hexdigest()+'\nM441T_SAVED_GATE_RC='+str(r['gate_return_code'])+'\n'+''.join(f'M441T_RESULT_CHUNK={i}/{len(parts)}:'+base64.b64encode(b).decode()+'\n' for i,b in enumerate(parts))+f'M441T_DONE case=B1 gate_rc={r["gate_return_code"]} export_rc=0\n'

def support():
    pkg=c.PKG
    r=json.loads((w.BASE/'runs/M366-staged-text-board-02/BOARD_RESULT.json').read_bytes())
    assert r['status']=='PASS_M366_FIXED_TEXT_DIAGNOSTIC'
    # Explicit collector fixture derived from an existing PASS; no new board evidence.
    r.update(status='PASS_M441T_FIXED_TEXT_DIAGNOSTIC',build_id='0x4D343431',manifest_sha256=w.sha(pkg/'PACKAGE_MANIFEST.json'),prior_board_sha256='0b416a17669ae1a5690a62650237ce6ced33f922017625f685401ca806e2273d',source_compatibility_checked_before_overlay=True)
    r['prior_single_layer_raw_sha256']='16b7aeb84dad97dbfbbdff06311becff9cf7866261316cc18dc296a97f0132e4'
    r['head_AST_checked_before_overlay']=True
    r['final_snapshot']['ap_return']=0x4d343431
    assert c.decode(emit(r))[2]==r
    failed=dict(r,status='FAIL',gate_return_code=1,errors=['explicit fixture failure'])
    assert c.decode(emit(failed))[2]==failed
    bads=[emit(r)+emit(r),emit(r).replace('CHUNK=0/','CHUNK=1/'),emit(r).replace('export_rc=0','export_rc=1'),emit(r).replace('SAVED_GATE_RC=0','SAVED_GATE_RC=1')]
    mutations=[('manifest_sha256','0'*64),('prior_board_sha256','0'*64),('source_compatibility_checked_before_overlay',False),('prior_single_layer_raw_sha256','0'*64),('head_AST_checked_before_overlay',False),('head_observer_proof',{'removed_observation_calls_ast_equals_original':False}),('additional_cma_requests_allowed',True),('numerical_pass',False),('performance_pass',True),('unsafe_buffers_retained',True),('safe_buffers_released',False),('model_forward_calls',2),('exact_comparison',{'hidden':False}),('released_buffers',[]),('fpga_transactions',0),('stable_overlay_reloaded',False),('errors',['fixture'])]
    for k,v in mutations:bads.append(emit(dict(r,**{k:v})))
    for bad in bads:
        try:c.decode(bad)
        except (ValueError,KeyError):pass
        else:raise AssertionError('Broken saved evidence accepted')
    control=w.HERE/'m441_text_control09.ps1'
    pwsh='C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe'
    tested=subprocess.run([pwsh,'-NoProfile','-File',str(control),'-Mode','SelfTest'],capture_output=True,text=True,encoding='utf-8')
    assert tested.returncode==0 and 'M441T_CONTROL_SELFTEST_PASS' in tested.stdout,tested.stdout+tested.stderr
    prep=w.BASE/'runs/M441-fixed-text-preparation-09/RESULT.json'
    p=json.loads(prep.read_bytes())
    paths=[pkg/'m441_text_gate.py',pkg/'m441_text_export.py',pkg/'m441_text_assemble.py',pkg/'run_m441_text.sh',w.HERE/'m441_text_collect09.py',control,Path(__file__)]
    out=w.BASE/'runs/M441-fixed-text-support-09'
    result=dict(status='PASS_M441_FIXED_TEXT_SUPPORT09',manifest_sha256=p['manifest_sha256'],preparation_sha256=w.sha(prep),original_m366_reference_sha256=w.sha(w.BASE/'runs/M366-staged-text-board-02/BOARD_RESULT.json'),collector_fixture_explicitly_not_board=True,collector_pass_and_failure_verified=True,collector_negative_checks=len(bads),controller_failure_collection_verified=True,files=[dict(path=x.relative_to(w.ROOT).as_posix(),sha256=w.sha(x)) for x in paths],board_executed=False,performance_pass=False)
    atomic(out/'CONTROL_SELFTEST.txt',(tested.stdout+tested.stderr).encode('utf-8'),immutable=True)
    atomic(out/'RESULT.json',w.encoded(result),immutable=True);sha=w.sha(out/'RESULT.json')
    w.sync('latest_m441_single_layer_support',dict(status=result['status'],result=(out/'RESULT.json').relative_to(w.ROOT).as_posix(),sha256=sha,manifest_sha256=p['manifest_sha256']),f'## M441 固定文本支持检查09（2026-10-09）\n\n实际新入口闭包/提前源码检查与原owner政策核对；显式旧raw派生回收fixture PASS/FAIL及{len(bads)}项破坏负例、控制故意失败仍收集通过。不是板端数值。SHA {sha}；下一步同TTY sudo、manifest先发与逐文件SHA后一次固定文本。')
    print(result['status'],sha)

def receipt():
    pkg=c.PKG;logs=w.ROOT/'tmp/m441_text09'
    a=logs/'assembly.log';s=logs/'upload_syntax.log'
    assert 'M441T_ALL_PAYLOAD_SHA_VERIFIED_NO_GATE' in a.read_text(encoding='utf-8-sig')
    assert '__M441T_ASSEMBLY_RC_0__' in a.read_text(encoding='utf-8-sig')
    assert '__M441T_SYNTAX_RC_0__' in s.read_text(encoding='utf-8-sig')
    all_logs=sorted(logs.glob('*.log'))
    out=w.BASE/'runs/M441-fixed-text-transfer-09'
    r=dict(status='PASS_M441_FIXED_TEXT_TRANSFER_ONLY09',manifest_sha256=w.sha(pkg/'PACKAGE_MANIFEST.json'),logs=[dict(path=p.relative_to(w.ROOT).as_posix(),bytes=p.stat().st_size,sha256=w.sha(p)) for p in all_logs],assembly_full_whitelist_verified=True,bash_n_pass=True,board_executed=False,overlay_loaded=False,numerical_pass=False,performance_pass=False)
    atomic(out/'RESULT.json',w.encoded(r),immutable=True);sha=w.sha(out/'RESULT.json')
    w.sync('latest_m441_single_layer_transfer',dict(status=r['status'],result=(out/'RESULT.json').relative_to(w.ROOT).as_posix(),sha256=sha,manifest_sha256=r['manifest_sha256']),f'## M441 固定文本隔离包传输09（2026-10-09）\n\nmanifest先发900B分块、新文件逐SHA、旧M363同SHA辅助与板端保存Compare原字节复用，完整白名单/计数核对及root bash-n通过；0Overlay/模型。SHA {sha}；下一步一次固定文本，已有attempt只Collect。')
    print(r['status'],sha)

if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='receipt':receipt()
    else:support()
