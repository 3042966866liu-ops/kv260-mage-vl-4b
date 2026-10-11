"""Default-disabled, one-case recovery after documented host reboot. No old run restart."""
import argparse,json,time,traceback,os
from m351_workflow import ROOT,BASE,encoded,sha,sync
from m441_host_io08 import atomic
from m441_supervisor04 import boot,process
import m441_sim_control21 as original
import m441_sim_evidence21 as evidence
RUN=BASE/'runs/M441-W2-W4-simulation-recovery-23'
PREP=RUN/'PREPARATION.json'
OLD=BASE/'runs/M441-W2-W4-simulation-coverage-21'
def local_sync(key,value,note):
    assert key=='latest_m441_simulation19_mlp_down'
    sync('latest_m441_simulation23_mlp_down',value,note.replace('仿真19/','仿真23恢复/'))
def guarded_collect(case,receipt,snapshot):
    folder=ROOT/case['path'];sim=folder/'verilog'
    text=(sim/'pressure.log').read_text(encoding='utf-8-sig',errors='replace')
    assert 'could not be opened' not in text,'Native output fopen warning: retain receipt, no numeric PASS'
    return evidence.collect(case,receipt,snapshot)
def output_preflight(case):
    sink=ROOT/case['path']/'tv/rtldatafile'
    assert sink.is_dir() and not list(sink.iterdir()),'Prepared empty sink required'
    probe=sink/'m441_launch_write_preflight23.writeprobe';raw=b'M441-output-sink23\n'
    with probe.open('xb') as stream:
        stream.write(raw);stream.flush();os.fsync(stream.fileno())
    assert probe.read_bytes()==raw;probe.unlink();assert not list(sink.iterdir())
    return dict(status='PASS_ACTUAL_OUTPUT_DIRECTORY_WRITE_PREFLIGHT23',directory=sink.relative_to(ROOT).as_posix(),write_fsync_read_delete=True,captured_epoch=time.time(),not_DUT_evidence=True)
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run',action='store_true');a=ap.parse_args();assert a.run,'Default disabled'
    p=json.loads(PREP.read_bytes());assert p['order']==['mlp_down'] and len(p['cases'])==1
    for row in p['bindings']:assert sha(ROOT/row['path'])==row['sha256'],row['path']
    for row in p['cases'][0]['files']:assert sha(ROOT/row['path'])==row['sha256'],row['path']
    for row in p['reused_PASS']:
        assert sha(ROOT/row['path'])==row['sha256']
        saved=json.loads((ROOT/row['path']).read_bytes());assert all(saved['checks'].values())
        for item in saved['evidence']:assert sha(ROOT/item['path'])==item['sha256']
    assert not (RUN/'START.json').exists(),'Already started: collect saved bytes only'
    assert process(28012,134360582687452936)['status']=='NOT_FOUND' and process(13100,134360610223133265)['status']=='NOT_FOUND','Original owner not proven absent'
    original.RUN=RUN;original.PREP=PREP;evidence.RUN=RUN;evidence.PREP=PREP;evidence.sync=local_sync;original.collect=guarded_collect
    atomic(RUN/'OUTPUT_LAUNCH_PREFLIGHT.json',encoded(output_preflight(p['cases'][0])),immutable=True)
    compiled=json.loads((OLD/'COMPILE.json').read_bytes())
    original.verify_snapshot(ROOT/'tmp/m441_sim_coverage_21/W2_max/verilog/xsim.dir',compiled['snapshot'])
    atomic(RUN/'COMPILE.json',(OLD/'COMPILE.json').read_bytes(),immutable=True)
    atomic(RUN/'START.json',encoded(dict(start_epoch=time.time(),boot=boot(),preparation_sha256=sha(PREP),case='mlp_down',reused_compilation_sha256=sha(OLD/'COMPILE.json'))),immutable=True)
    try:
        deadline=time.monotonic()+p['global_wall_budget_s']
        r=original.run_case(p,p['cases'][0],compiled,deadline)
        assert r['status']=='PASS_M441_SUPPLEMENTAL_W2_W4_RTL' and all(r['checks'].values())
        refs=p['reused_PASS']+[dict(case='mlp_down',path=(RUN/'mlp_down_RESULT.json').relative_to(ROOT).as_posix(),sha256=sha(RUN/'mlp_down_RESULT.json'),status=r['status'])]
        final=dict(status='PASS_M441_SUPPLEMENTAL_GAPS_WITH_SEPARATE_RECOVERY23',build_id=p['build_id'],preparation_sha256=sha(PREP),results=refs,original_interruption=p['interruption'],original_recovery22_failure=p['original_recovery22_failure'],board=False,performance=False,production_changed=False)
        atomic(RUN/'RESULT.json',encoded(final),immutable=True)
        sync('latest_m441_simulation23_closed',dict(status=final['status'],result=(RUN/'RESULT.json').relative_to(ROOT).as_posix(),sha256=sha(RUN/'RESULT.json'),board=False),'## M441末项独立恢复23完成（2026-10-10）\n\nSHA '+sha(RUN/'RESULT.json')+'；原21四项PASS复用，新23仅mlp_down完整原字节裁决通过；原21重启中断保持，不伪造原总PASS，不追加旧样本，0板端/生产。')
        import m441_sim_report23
        m441_sim_report23.main()
        original.progress('COMPLETE',result=final)
    except BaseException as exc:
        fail=dict(status='STOP_M441_CURRENT_LEVEL_RECOVERY23',error=repr(exc),traceback=traceback.format_exc(),preparation_sha256=sha(PREP),old_attempt_preserved=True,board=False)
        atomic(RUN/'STOP.json',encoded(fail),immutable=True)
        sync('latest_m441_simulation23_stop',dict(status=fail['status'],result=(RUN/'STOP.json').relative_to(ROOT).as_posix(),sha256=sha(RUN/'STOP.json'),board=False),'## M441末项恢复23本级停止（2026-10-10）\n\nSHA '+sha(RUN/'STOP.json')+'；仅当前级原失败/traceback保留，不重启旧控制器或已PASS项。')
        original.progress('STOP',result=fail);raise
if __name__=='__main__':main()
