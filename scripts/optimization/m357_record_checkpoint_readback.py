"""Preserve startup file errors and independently validate affected checkpoints."""
import json
import re
from pathlib import Path
import m351_workflow as w
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'tmp/m357_checkpoint_readback_01'
BASE=ROOT/'deployment/mage_vl4b/optimization_v1'
rows=json.loads((OUT/'INPUTS.json').read_text(encoding='utf-8'))
assert json.loads((OUT/'EXIT.json').read_text(encoding='utf-8'))['vivado_rc']==0
log=(OUT/'vivado.log').read_text(encoding='utf-8')
assert 'M357_AUXILIARY_CHECKPOINT_READBACK_PASS' in log
assert not re.search(r'^ERROR:|^CRITICAL WARNING:',log,re.M)
for row in rows:
    name=row['ip']
    run=ROOT/'tmp/m357_shell_01/mage_m120_m89x2_highddr.runs'/f'{name}_synth_1'
    original=(run/'runme.log').read_text(encoding='utf-8')
    errors=re.findall(r'^ERROR:.*$',original,re.M)
    assert errors==["ERROR: [Common 17-354] Could not open 'C' for writing."]
    # Match the actual execution line, not earlier printed CLI -source args.
    executed=re.search(r'^source '+re.escape(name)+r'\.tcl -notrace$',original,re.M)
    assert executed and original.index(errors[0])<executed.start()
    assert 'Synthesis finished with 0 errors, 0 critical warnings' in original
    assert w.sha(run/'runme.log')==row['original_log_sha256']
    assert w.sha(run/(name+'.dcp'))==row['checkpoint_sha256']
    readback=(OUT/(name+'_readback.txt')).read_text(encoding='utf-8')
    assert 'PART=xck26-sfvc784-2LV-c\nBLACKBOXES=0\n' in readback
    assert int(re.search(r'PRIMITIVES=(\d+)',readback)[1])>0
    row['retained_startup_errors']=errors
    row['readback_sha256']=w.sha(OUT/(name+'_readback.txt'))
result=dict(status='PASS_AUXILIARY_CHECKPOINT_READBACK_ONLY',build_id='0x4D333537',
    checkpoints=rows,files=[dict(path=p.relative_to(ROOT).as_posix(),sha256=w.sha(p))
        for p in sorted(OUT.iterdir()) if p.is_file()],
    interpretation='Each original file-writing ERROR precedes source of the design Tcl. Both later synthesis summaries report zero design errors/critical warnings. Separate process read-only opens exact SHA checkpoints, confirms expected part and zero blackboxes. Original ERRORs retained; specific writing target/root cause not established.',
    rejected_collection='Initial collector matched printed command-line -source arguments instead of anchored Tcl execution line and rejected before writing evidence. Anchor corrected; no synthesis/readback rerun.',
    root_cause_proven=False,whole_shell_timing_pass=False,board=False,promoted=False)
ev=BASE/'runs/M357-auxiliary-checkpoint-readback-01/RESULT.json'
w.atomic(ev,w.encoded(result),immutable=True);sha=w.sha(ev)
w.sync('M357_auxiliary_checkpoint_readback',dict(status=result['status'],sha256=sha,evidence_path=ev.relative_to(ROOT).as_posix(),build_id=result['build_id']),
    'M357 两个辅助IP保留设计Tcl加载前Common17-354文件写入ERROR；实际综合0设计错误/0critical，独立新Vivado进程只读同SHA checkpoint确认K26部件、0黑盒且可读。仅产物读回，不证明该启动ERROR根因，也非整机时序/上板PASS。证据 '+sha)
print(json.dumps(dict(status=result['status'],sha256=sha)))
