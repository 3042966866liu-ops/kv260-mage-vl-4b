"""Read-only audit of this attempt's auxiliary checkpoints, with original errors retained."""
import argparse,json,re,subprocess,time
from m441_supervisor04 import boot,process as identity,classify,log_snapshot
import m351_workflow as workflow
from m441_host_io08 import atomic
workflow.atomic=atomic
from m351_workflow import ROOT,BASE,HERE,encoded,sha,sync
ap=argparse.ArgumentParser();ap.add_argument('mode',choices=('prepare','run','collect'));ap.add_argument('--run',action='store_true');a=ap.parse_args()
out=ROOT/'tmp/m443_aux_readback_04';runs=ROOT/'tmp/m443_shell_01/mage_m120_m89x2_highddr.runs'
if a.mode=='prepare':
    assert not out.exists(),'Existing readback: collect only'
    from m443_aux_classifier04 import classify, EXPECTED
    failure=BASE/'runs/M443-full-shell-03/RESULT.json'
    assert sha(failure)=='17783ff1dd8ed80c434555f79102110de945cd8396596057a7cb08d24815e4e1'
    assert json.loads((ROOT/'tmp/m443_shell_exit.json').read_bytes())['vivado_rc']==0
    assert json.loads((ROOT/'tmp/m443_shell_mapping.json').read_bytes())['removed'] is True
    rows=[]
    for log in sorted(runs.glob('*_synth_1/runme.log')):
        text=log.read_text(encoding='utf-8-sig');errors=re.findall(r'^ERROR:.*$',text,re.M)
        if not errors:continue
        ip=log.parent.name.removesuffix('_synth_1');dcp=log.parent/(ip+'.dcp')
        classify(ip,text,sha(log),sha(dcp),(log.parent/'.vivado.end.rst').exists())
        rows.append(dict(ip=ip,log=log.relative_to(ROOT).as_posix(),original_log_sha256=sha(log),checkpoint=dcp.relative_to(ROOT).as_posix(),checkpoint_sha256=sha(dcp),retained_startup_errors=errors))
    assert {x['ip'] for x in rows}==set(EXPECTED), 'Affected saved-attempt set differs'
    out.mkdir();atomic(out/'INPUTS.json',encoded(rows),immutable=True)
    t=''
    for x in rows:
        t+='open_checkpoint {'+(ROOT/x['checkpoint']).as_posix()+'}\n'
        t+='if {[get_property PART [current_design]] ne "xck26-sfvc784-2LV-c"} {error "Readback part differs"}\nset boxes [get_cells -hier -quiet -filter {IS_BLACKBOX == 1}]\nif {[llength $boxes] != 0} {error "Readback blackboxes"}\n'
        t+='set fd [open {'+(out/(x['ip']+'_readback.txt')).as_posix()+'} w]\n'
        t+='puts $fd "PART=[get_property PART [current_design]]"\nputs $fd "BLACKBOXES=[llength $boxes]"\nputs $fd "PRIMITIVES=[llength [get_cells -hier -filter {IS_PRIMITIVE == 1}]]"\nclose $fd\nclose_design\n'
    t+='puts "M443_AUXILIARY_CHECKPOINT_READBACK_PASS"\nexit\n'
    atomic(out/'readback.tcl',t.encode('utf-8'),immutable=True)
    r=dict(status='PREPARED_M443_AUXILIARY_READBACK_ONLY',build_id='0x4D343433',checkpoints=rows,Tcl_sha256=sha(out/'readback.tcl'),inputs_sha256=sha(out/'INPUTS.json'),budget_s=600,board=False,executed=False,prior_failure_sha256=sha(failure),scripts=[dict(path=(HERE/n).relative_to(ROOT).as_posix(),sha256=sha(HERE/n)) for n in ('m443_aux_readback04.py','m443_aux_classifier04.py','m441_supervisor04.py','m351_workflow.py','m441_host_io08.py')])
    ev=BASE/'runs/M443-auxiliary-readback-preparation-04/RESULT.json';atomic(ev,encoded(r),immutable=True)
    sync('latest_m443_auxiliary_readback_preparation',dict(status=r['status'],result=ev.relative_to(ROOT).as_posix(),sha256=sha(ev),build_id=r['build_id'],board=False),
         '## M443 辅助checkpoint只读准备（2026-10-11）\n\nSHA '+sha(ev)+'；仅允许本次实际出现的已冻结kernel/reset启动Common17-354；记录数量来自日志，本次精确两个错误IP，集合不同拒绝，实际设计脚本之前，设计综合0error/0critical且已完成。冻结本次DCP/log SHA，独立读回而不重跑综合或删除原错误；0执行/板端，根因未证明。')
    print(r['status'],sha(ev))
elif a.mode=='run':
    assert a.run,'Default disabled';prep=BASE/'runs/M443-auxiliary-readback-preparation-04/RESULT.json';p=json.loads(prep.read_bytes())
    assert all(sha(ROOT/x['path'])==x['sha256'] for x in p['scripts'])
    assert not (out/'console.log').exists(),'Existing readback: collect only'
    assert sha(out/'INPUTS.json')==p['inputs_sha256'] and sha(out/'readback.tcl')==p['Tcl_sha256']
    for x in p['checkpoints']:
        assert sha(ROOT/x['checkpoint'])==x['checkpoint_sha256'] and sha(ROOT/x['log'])==x['original_log_sha256']
    assert all(sha(prep) in (ROOT/n).read_text(encoding='utf-8') for n in ('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'))
    start=time.monotonic();wall=False
    with (out/'console.log').open('wb') as f:
        proc=subprocess.Popen(['D:/AMDDesignTools/2026.1/Vivado/bin/vivado.bat','-mode','batch','-source',str(out/'readback.tcl'),'-log','readback.log','-journal','readback.jou'],cwd=out,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
        print('M443_READONLY_AUX_STARTED pid='+str(proc.pid),flush=True)
        born=identity(proc.pid).get('creation_FILETIME');initial=boot()
        while proc.poll() is None:
            atomic(out/'LIVE.json',encoded(dict(status=classify(initial,boot(),identity(proc.pid,born)),process=identity(proc.pid,born),elapsed_s=time.monotonic()-start,log=log_snapshot(out/'console.log'))))
            if time.monotonic()-start>p['budget_s']:
                atomic(out/'EXIT.json',encoded(dict(vivado_rc=None,wall_budget_exceeded=True,process_retained=True,pid=proc.pid,creation_FILETIME=born)),immutable=True)
                raise RuntimeError('Readback budget exceeded: native process retained, no downstream gate')
            time.sleep(2)
        rc=proc.returncode
    atomic(out/'EXIT.json',encoded(dict(vivado_rc=rc,wall_budget_exceeded=wall,elapsed_s=time.monotonic()-start)),immutable=True)
    print('M443_AUX_ORIGINAL_RC',rc);raise SystemExit(1 if wall else rc)
else:
    rows=json.loads((out/'INPUTS.json').read_bytes());saved=json.loads((out/'EXIT.json').read_bytes());text=(out/'console.log').read_text(encoding='utf-8-sig')
    checks=dict(original_rc=saved['vivado_rc']==0,wall_budget=not saved['wall_budget_exceeded'],actual_marker=bool(re.search(r'^M443_AUXILIARY_CHECKPOINT_READBACK_PASS$',text,re.M)),no_readback_error=not re.search(r'^ERROR:|^CRITICAL WARNING:',text,re.M))
    for x in rows:
        dcp=ROOT/x['checkpoint'];log=ROOT/x['log'];data=(out/(x['ip']+'_readback.txt')).read_text(encoding='utf-8-sig')
        checks[x['ip']+'_unchanged']=sha(dcp)==x['checkpoint_sha256'] and sha(log)==x['original_log_sha256']
        checks[x['ip']+'_valid']=data.startswith('PART=xck26-sfvc784-2LV-c\nBLACKBOXES=0\n') and int(re.search(r'PRIMITIVES=(\d+)',data)[1])>0
        x['readback_sha256']=sha(out/(x['ip']+'_readback.txt'))
    ok=all(checks.values());r=dict(status='PASS_M443_AUXILIARY_CHECKPOINT_READBACK_ONLY' if ok else 'FAIL_M443_AUXILIARY_READBACK',build_id='0x4D343433',checks=checks,checkpoints=rows,original_rc=saved['vivado_rc'],root_cause_proven=False,whole_shell_timing_pass=False,board=False,promotion=False,
       evidence=[dict(path=x.relative_to(ROOT).as_posix(),sha256=sha(x)) for x in sorted(out.iterdir()) if x.is_file()])
    ev=BASE/'runs/M443-auxiliary-checkpoint-readback-04/RESULT.json';atomic(ev,encoded(r),immutable=True)
    sync('latest_m443_auxiliary_checkpoint_readback',dict(status=r['status'],result=ev.relative_to(ROOT).as_posix(),sha256=sha(ev),build_id=r['build_id'],board=False),
         '## M443 辅助checkpoint只读闭合（2026-10-11）\n\nSHA '+sha(ev)+'；'+r['status']+'，原rc'+str(saved['vivado_rc'])+'。本次实际受影响的同SHA产物独立打开（零个时仅无启动错误检查）K26/0黑盒/有primitive，原启动写入ERROR保留，根因未证明；无综合重跑，非整机/板端PASS。')
    print(r['status'],sha(ev));print(json.dumps(checks));raise SystemExit(0 if ok else 1)
