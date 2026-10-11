"""Saved-only strengthening: Tcl echo is not an executed verification marker."""
import json,re
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync

original=HERE/'m439_collect_protocol.py'
prep=BASE/'runs/M439-max-protocol-preparation-01/RESULT.json'
assert sha(original)==json.loads(prep.read_bytes())['collector_sha256']
ev=BASE/'runs/M439-protocol-collector-strict-markers-02/RESULT.json'
markers=['M439_SHARED_VIP_WEIGHT_AR_HOLD_VERIFIED cycles=10000',
         'M439_SHARED_VIP_OUTPUT_HOLD_VERIFIED cycles=100000']
for marker in markers:
    assert re.search('^'+re.escape(marker)+'$',marker+'\n',re.M)
    assert not re.search('^'+re.escape(marker)+'$','## puts "'+marker+'"\n',re.M)
r=dict(status='PREPARED_SAVED_ONLY_M439_STRICT_EXECUTED_MARKERS',original_collector_sha256=sha(original),
       actual_collector_sha256=sha(HERE/'m439_collect_protocol02.py'),reason='Xsim log includes Tcl puts command echoes; require anchored native output lines, not substring membership.',
       echo_only_rejected=True,native_output_accepted=True,original_collector_not_yet_used_for_max=True,
       no_simulation_rerun=True,board=False)
atomic(ev,encoded(r),immutable=True)
sync('latest_m439_protocol_collector_strict_markers',dict(status=r['status'],result=ev.relative_to(ROOT).as_posix(),sha256=sha(ev),build_id='0x4D343339',board=False),
     '## M439 协议回收标记收紧（2026-10-07）\n\nSHA '+sha(ev)+'；首次最大结果裁决前发现Xsim回显Tcl puts命令，02只认可整行实际验证输出，echo负例拒绝。原collector与所有仿真保持，只读已有原字节，不重跑。')
s=original.read_text(encoding='utf-8')
s=s.replace("assert sha(Path(__file__))==p['collector_sha256']", "assert sha(HERE/'m439_collect_protocol.py')==p['collector_sha256']")
for marker in markers:
    old=repr(marker)+' in log'
    assert s.count(old)==1
    s=s.replace(old,"bool(re.search(r'^"+re.escape(marker)+"$',log,re.M))")
anchor="r=dict(status=good if ok else bad,"
assert s.count(anchor)==1
s=s.replace(anchor,"r=dict(collector_template_sha256=sha(HERE/'m439_collect_protocol.py'),actual_collector_sha256=sha(HERE/'m439_collect_protocol02.py'),collection_strengthening_sha256=sha(ev),status=good if ok else bad,")
ns={'__name__':'m439_collect_protocol02','__file__':str(HERE/'m439_collect_protocol02.py'),'HERE':HERE,'ev':ev}
exec(compile(s,str(HERE/'m439_collect_protocol02.py')+':strict-native-markers','exec'),ns)
