"""Read-only audit of this attempt's auxiliary checkpoints, with original errors retained."""
import argparse,json,re,subprocess,time
from m441_supervisor04 import boot,process as identity,classify,log_snapshot
from m351_workflow import ROOT,BASE,atomic,encoded,sha,sync
ap=argparse.ArgumentParser();ap.add_argument('mode',choices=('prepare','run','collect'));ap.add_argument('--run',action='store_true');a=ap.parse_args()
out=ROOT/'tmp/m441_aux_readback_01';runs=ROOT/'tmp/m441_shell_01/mage_m120_m89x2_highddr.runs'
if a.mode=='prepare':
    assert not out.exists(),'Existing readback: collect only'
    rows=[]
    for log in sorted(runs.glob('*_synth_1/runme.log')):
        text=log.read_text(encoding='utf-8-sig');errors=re.findall(r'^ERROR:.*$',text,re.M)
        if not errors:continue
        ip=log.parent.name.removesuffix('_synth_1')
        assert errors==["ERROR: [Common 17-354] Could not open 'C' for writing."]
        source=re.search(r'^source '+re.escape(ip)+r'\.tcl -notrace$',text,re.M)
        assert source and text.index(errors[0])<source.start()
        assert 'Synthesis finished with 0 errors, 0 critical warnings' in text
        assert (log.parent/'.vivado.end.rst').exists()
        dcp=log.parent/(ip+'.dcp');assert dcp.is_file()
        rows.append(dict(ip=ip,log=log.relative_to(ROOT).as_posix(),original_log_sha256=sha(log),checkpoint=dcp.relative_to(ROOT).as_posix(),checkpoint_sha256=sha(dcp),retained_startup_errors=errors))
    assert {x['ip'] for x in rows}.issubset({'qwen25_mixed_gs_zynq_ultra_ps_e_0_0','qwen25_mixed_gs_reset_sync_0'})
    out.mkdir();atomic(out/'INPUTS.json',encoded(rows),immutable=True)
    t=''
    for x in rows:
        t+='open_checkpoint {'+(ROOT/x['checkpoint']).as_posix()+'}\n'
        t+='if {[get_property PART [current_design]] ne "xck26-sfvc784-2LV-c"} {error "Readback part differs"}\nset boxes [get_cells -hier -quiet -filter {IS_BLACKBOX == 1}]\nif {[llength $boxes] != 0} {error "Readback blackboxes"}\n'
        t+='set fd [open {'+(out/(x['ip']+'_readback.txt')).as_posix()+'} w]\n'
        t+='puts $fd "PART=[get_property PART [current_design]]"\nputs $fd "BLACKBOXES=[llength $boxes]"\nputs $fd "PRIMITIVES=[llength [get_cells -hier -filter {IS_PRIMITIVE == 1}]]"\nclose $fd\nclose_design\n'
    t+='puts "M441_AUXILIARY_CHECKPOINT_READBACK_PASS"\nexit\n'
    atomic(out/'readback.tcl',t.encode('utf-8'),immutable=True)
    r=dict(status='PREPARED_M441_AUXILIARY_READBACK_ONLY',build_id='0x4D343431',checkpoints=rows,Tcl_sha256=sha(out/'readback.tcl'),inputs_sha256=sha(out/'INPUTS.json'),budget_s=600,board=False,executed=False)
    ev=BASE/'runs/M441-auxiliary-readback-preparation-01/RESULT.json';atomic(ev,encoded(r),immutable=True)
    sync('latest_m441_auxiliary_readback_preparation',dict(status=r['status'],result=ev.relative_to(ROOT).as_posix(),sha256=sha(ev),build_id=r['build_id'],board=False),
         '## M441 辅助checkpoint只读准备（2026-10-07）\n\nSHA '+sha(ev)+'；仅允许本次实际出现的已知PS/reset启动Common17-354；记录数量来自日志，允许没有此错误，实际设计脚本之前，设计综合0error/0critical且已完成。冻结本次DCP/log SHA，独立读回而不重跑综合或删除原错误；0执行/板端，根因未证明。')
    print(r['status'],sha(ev))
elif a.mode=='run':
    assert a.run,'Default disabled';prep=BASE/'runs/M441-auxiliary-readback-preparation-01/RESULT.json';p=json.loads(prep.read_bytes())
    assert not (out/'console.log').exists(),'Existing readback: collect only'
    assert sha(out/'INPUTS.json')==p['inputs_sha256'] and sha(out/'readback.tcl')==p['Tcl_sha256']
    for x in p['checkpoints']:
        assert sha(ROOT/x['checkpoint'])==x['checkpoint_sha256'] and sha(ROOT/x['log'])==x['original_log_sha256']
    assert all(sha(prep) in (ROOT/n).read_text(encoding='utf-8') for n in ('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'))
    start=time.monotonic();wall=False
    with (out/'console.log').open('wb') as f:
        proc=subprocess.Popen(['D:/AMDDesignTools/2026.1/Vivado/bin/vivado.bat','-mode','batch','-source',str(out/'readback.tcl'),'-log','readback.log','-journal','readback.jou'],cwd=out,stdout=f,stderr=subprocess.STDOUT)
        print('M441_READONLY_AUX_STARTED pid='+str(proc.pid),flush=True)
        born=identity(proc.pid).get('creation_FILETIME');initial=boot()
        while proc.poll() is None:
            atomic(out/'LIVE.json',encoded(dict(status=classify(initial,boot(),identity(proc.pid,born)),process=identity(proc.pid,born),elapsed_s=time.monotonic()-start,log=log_snapshot(out/'console.log'))))
            if time.monotonic()-start>p['budget_s']:
                atomic(out/'EXIT.json',encoded(dict(vivado_rc=None,wall_budget_exceeded=True,process_retained=True,pid=proc.pid,creation_FILETIME=born)),immutable=True)
                raise RuntimeError('Readback budget exceeded: native process retained, no downstream gate')
            time.sleep(2)
        rc=proc.returncode
    atomic(out/'EXIT.json',encoded(dict(vivado_rc=rc,wall_budget_exceeded=wall,elapsed_s=time.monotonic()-start)),immutable=True)
    print('M441_AUX_ORIGINAL_RC',rc);raise SystemExit(1 if wall else rc)
else:
    rows=json.loads((out/'INPUTS.json').read_bytes());saved=json.loads((out/'EXIT.json').read_bytes());text=(out/'console.log').read_text(encoding='utf-8-sig')
    checks=dict(original_rc=saved['vivado_rc']==0,wall_budget=not saved['wall_budget_exceeded'],actual_marker=bool(re.search(r'^M441_AUXILIARY_CHECKPOINT_READBACK_PASS$',text,re.M)),no_readback_error=not re.search(r'^ERROR:|^CRITICAL WARNING:',text,re.M))
    for x in rows:
        dcp=ROOT/x['checkpoint'];log=ROOT/x['log'];data=(out/(x['ip']+'_readback.txt')).read_text(encoding='utf-8-sig')
        checks[x['ip']+'_unchanged']=sha(dcp)==x['checkpoint_sha256'] and sha(log)==x['original_log_sha256']
        checks[x['ip']+'_valid']=data.startswith('PART=xck26-sfvc784-2LV-c\nBLACKBOXES=0\n') and int(re.search(r'PRIMITIVES=(\d+)',data)[1])>0
        x['readback_sha256']=sha(out/(x['ip']+'_readback.txt'))
    ok=all(checks.values());r=dict(status='PASS_M441_AUXILIARY_CHECKPOINT_READBACK_ONLY' if ok else 'FAIL_M441_AUXILIARY_READBACK',build_id='0x4D343431',checks=checks,checkpoints=rows,original_rc=saved['vivado_rc'],root_cause_proven=False,whole_shell_timing_pass=False,board=False,promotion=False,
       evidence=[dict(path=x.relative_to(ROOT).as_posix(),sha256=sha(x)) for x in sorted(out.iterdir()) if x.is_file()])
    ev=BASE/'runs/M441-auxiliary-checkpoint-readback-01/RESULT.json';atomic(ev,encoded(r),immutable=True)
    sync('latest_m441_auxiliary_checkpoint_readback',dict(status=r['status'],result=ev.relative_to(ROOT).as_posix(),sha256=sha(ev),build_id=r['build_id'],board=False),
         '## M441 辅助checkpoint只读闭合（2026-10-07）\n\nSHA '+sha(ev)+'；'+r['status']+'，原rc'+str(saved['vivado_rc'])+'。本次实际受影响的同SHA产物独立打开（零个时仅无启动错误检查）K26/0黑盒/有primitive，原启动写入ERROR保留，根因未证明；无综合重跑，非整机/板端PASS。')
    print(r['status'],sha(ev));print(json.dumps(checks));raise SystemExit(0 if ok else 1)
