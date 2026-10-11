"""Save only current verified compile recovery and live numerical gate."""
import json
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
from m441_supervisor04 import process,log_snapshot

def main():
    ev=BASE/'runs/M441-W4-compile-recovery-closure-05/RESULT.json'
    assert not ev.exists()
    oldpath=BASE/'runs/M441-long-A-mlp_down-RTL-preparation-04/RESULT.json'
    newpath=BASE/'runs/M441-long-A-mlp_down-RTL-preparation-05/RESULT.json'
    old=json.loads(oldpath.read_bytes());new=json.loads(newpath.read_bytes())
    a={f['path'].split('_04/',1)[1]:f['sha256'] for f in old['files']}
    b={f['path'].split('_05/',1)[1]:f['sha256'] for f in new['files']}
    assert a==b
    board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    compiled=[]
    for v in 'AB':
        p=BASE/f'runs/M441-long-{v}-mlp_down-compile-05/RESULT.json'
        r=json.loads(p.read_bytes());assert r['status']=='PASS_M441_COMPLETE_RTL_COMPILED' and r['original_rc']==0
        assert board[f'latest_m441_long_{v}_mlp_down_compile05']['sha256']==sha(p)
        assert all(sha(p) in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
        compiled.append(dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p),variant=v))
    work=BASE/'runs/M441-W4-zero-continuation-05'
    start=json.loads((work/'START.json').read_bytes());running=json.loads((work/'RUNNING.json').read_bytes())
    supervisor=process(start['supervisor']['pid'],start['supervisor']['creation_FILETIME'])
    assert supervisor['status']=='ALIVE'
    jobs=[]
    for job in running['jobs']:
        identity=process(job['pid'],job['creation_FILETIME']);assert identity['status']=='ALIVE'
        native=log_snapshot(ROOT/job['native_log']);assert native['last'].get('cycle',0)>0 and not native['failure_tail']
        jobs.append(dict(owner=job,identity=identity,native_snapshot=native))
    bounded=BASE/'runs/M441-bounded-boundary-preparation-04/RESULT.json'
    r=dict(status='PASS_M441_IDENTICAL_INPUT_COMPILE_RECOVERY_NUMERIC_RUNNING',
        identical_A_frozen_input_files=len(a),all_input_SHA_equal=True,compile_results=compiled,
        compiler_recovery_scope='Both native xelab compiles succeeded in isolated05 under normal tool permission, with verbosity2. Original04 failed C compilation; detailed original compiler stderr absent. No proven exact root cause.',
        original_compile04_FAIL_preserved=True,supervisor=supervisor,numerical_jobs=jobs,
        finite_numeric_contract=dict(cycles_per_run=12000000,wall_s_per_tool=28800,formal_output_words_per_run=40960,run_count=2,restarts=0),
        bounded_boundary_preparation_sha256=sha(bounded),boundary_component_and_control_ready=False,
        partial_boundary04_preparation=dict(reason='Pre-run Python string-count assertion was wrong; unchanged source model contains both range occurrences plus one endpoint. Partial04 directory preserved, corrected preparation isolated05; no tools ran.'),
        supervisor_limit='LIVE enumerates finished jobs as missing; completed jobs have authoritative *_exit.json receipts. Current live pair verified separately. Next control must classify known receipts as completed before missing-process checks.',
        future_candidates='Output parsing temporary copies audit after M441; no implementation started.',
        board=False,performance=False,full_numeric_result=False,promoted=False)
    atomic(ev,encoded(r),immutable=True)
    report='''# M441 W4编译恢复与当前有限验证

原04失败保留。05重新生成的154份A输入逐份同SHA，两版xelab均返回0并保存正式编译PASS；详细日志记录实际MinGW6.2命令。原04没有底层编译器stderr，因此原因只定位到生成C编译阶段，不能把隔离运行成功等同于已经证明沙箱或某个编译选项是根因。

两版完整mlp_down Zero已启动：各40,960输出字，12M周期/8小时上限，实际进度与进程身份每30秒保存。候选四个权重FIFO已观察到34字占用及背压。当前只有部分进度，完整输出及最后排空仍待正式收集。

后续有界压力输入保持10个descriptor、327,680输出字、原FIFO8192/34规模；只将测试模型延迟改为0..8并加入最后TLAST的128个有效周期停顿。组件、收集器和控制准入尚未完成，不能启动这一门禁。原Random02 FAIL和Random03重启中断保持，不称六组Random通过。

监督器LIVE中的已退出作业需结合对应exit收据读取：已完成不等于异常消失。后续控制会优先识别已保存返回码，避免误报。

M441数值、必要协议和时序闭合后，才进入真实板端W4长链比较。完成M441后优先审计当前实际解析器：确认FP16转FP32、transpose/reshape、ldexp/astype和最终写入的复制；对照M231/M332及双worker旧分支。MAC流水边界、尺度缓存、紧凑输出只保留待核实建议，不叠加新核改动。
'''
    atomic(ev.parent/'REPORT.md',report.encode('utf-8'),immutable=True)
    sync('latest_m441_W4_compile_recovery_closure05',dict(status=r['status'],sha256=sha(ev),result=ev.relative_to(ROOT).as_posix(),board=False),
        '## M441 W4编译恢复与实际Zero进度闭合（2026-10-09）\n\nSHA '+sha(ev)+'；A154输入逐份同SHA，两版xelab原rc0，完整mlp_down Zero各一次正推进，40,960字/12M/8h。原04生成C编译失败底层原因未保存，不猜测；原FAIL保持。候选FIFO34已有满/背压观察，最终数值/排空尚待收集。新有界压力仅输入准备，组件/控制尚缺；0板端/请求收益。先完成本级，后续输出解析建议排在M441之后。')
    print(r['status'],sha(ev),[(j['owner']['stage'],j['native_snapshot']['last']['cycle']) for j in jobs])

if __name__=='__main__':main()
