"""Read existing M441 logs; save a postmortem, never launch a tool or board job."""
import hashlib
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.dont_write_bytecode = True
sys.stdout.reconfigure(encoding='utf-8')
from m351_workflow import atomic, encoded, sync

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'deployment/mage_vl4b/optimization_v1/runs/M441-day-review-01'
TZ = timezone(timedelta(hours=8))

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def native_time(s):
    return datetime.strptime(s, '%a %b %d %H:%M:%S %Y').replace(tzinfo=TZ)

def fields(line):
    return {k: int(v) for k, v in re.findall(r'(\w+)=(\d+)', line)}

def main():
    if (OUT / 'RESULT.json').exists():
        raise RuntimeError('Immutable review already exists; read it instead')
    recovery = {}
    for name in ('CURRENT_STATE.md', 'DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md', 'docsMILESTONES.md', 'deployment/mage_vl4b/BOARD_GATE_RESULT.json'):
        p = ROOT / name
        full = p.read_text(encoding='utf-8-sig')
        recovery[name] = dict(sha256=sha(p), bytes=p.stat().st_size, lines=len(full.splitlines()))
    board = json.loads((ROOT / 'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_text(encoding='utf-8-sig'))
    evidence = {}
    results = {}
    for suffix, expected in (
        ('A-gate_up-zero-02', '3116961c34d729e37f32a79b4e914c1e16d4a978c988e41ddc51814298fd16f4'),
        ('B-gate_up-zero-02', '74bafec070d975c0ef967205f7b3232e49efd75a5436f6db2223a2142220647c'),
        ('A-gate_up-random-02', '50a4a7aaa36ad008c86a7b231191ca7b1f6dc94896579827696cece2d608df81')):
        rel = 'deployment/mage_vl4b/optimization_v1/runs/M441-long-' + suffix + '/RESULT.json'
        p = ROOT / rel
        assert sha(p) == expected
        assert any(isinstance(v, dict) and v.get('sha256') == expected for v in board.values())
        assert all(expected in (ROOT / n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md', 'docsMILESTONES.md'))
        evidence[rel] = expected
        results[suffix] = json.loads(p.read_text(encoding='utf-8-sig'))
    records = []
    all_text = {}
    for variant, rev, mode in (('B', '02', 'zero'), ('A', '02', 'zero'), ('A', '02', 'random'), ('A', '03', 'random')):
        rel = f'tmp/m441_long_{variant}_gate_up_{rev}/verilog/{mode}.log'
        p = ROOT / rel
        raw = p.read_bytes()
        # Native xsim logs contain non-UTF8 bytes. Preserve/hash exact bytes;
        # escape undecodable bytes only in the read-only ASCII metric view.
        text = raw.decode('utf-8-sig', errors='backslashreplace')
        all_text[(variant, rev, mode)] = text
        evidence[rel] = hashlib.sha256(raw).hexdigest()
        start = native_time(re.search(r'Start of session at: (.+)', text).group(1).strip())
        end_match = re.search(r'Exiting xsim at (.+?)\.\.\.', text)
        last_write = datetime.fromtimestamp(p.stat().st_mtime, TZ)
        end = native_time(end_match.group(1)) if end_match else None
        cpu_match = re.search(r'Simulation Memory Usage: (\d+) KB \(Peak: (\d+) KB\), Simulation CPU Usage: (\d+) ms', text)
        run_match = re.search(r'run: Time \(s\): cpu = [\d:]+ ; elapsed = (\d+):(\d+):(\d+)', text)
        elapsed = sum(int(v)*m for v,m in zip(run_match.groups(), (3600,60,1))) if run_match else (last_write-start).total_seconds()
        heartbeat = [fields(line) for line in text.splitlines() if line.startswith('M441_HEARTBEAT ')]
        done = re.search(r'M441_DONE.*?cycles=(\d+)', text)
        cycles = results[f'{variant}-gate_up-{mode}-{rev}']['done']['cycles'] if rev == '02' and mode == 'zero' else heartbeat[-1]['cycle']
        records.append(dict(variant=variant, revision=rev, mode=mode, start=start.isoformat(), end=end.isoformat() if end else None,
            last_log_write=last_write.isoformat(), elapsed_s=elapsed, elapsed_kind='native_run_elapsed' if run_match else 'start_to_last_log_write',
            cycles=cycles, cycles_per_host_second=cycles/elapsed, kernel_cpu_s=int(cpu_match[3])/1000 if cpu_match else None,
            kernel_cpu_wall_ratio=int(cpu_match[3])/1000/elapsed if cpu_match else None,
            kernel_peak_gib=int(cpu_match[2])/1048576 if cpu_match else None,
            last_output_words=heartbeat[-1]['output'], expected_words=311296,
            completed_output_words=results[f'{variant}-gate_up-{mode}-{rev}']['done']['output_words'] if rev=='02' and mode=='zero' else None,
            log_metric_decoding='UTF8-sig with non-UTF8 bytes escaped; exact raw SHA preserved',
            fatal='Fatal:' in text, normal_exit=end is not None, log=rel, log_sha256=evidence[rel]))
    text = all_text[('A', '03', 'random')]
    progress = [fields(line) for line in text.splitlines() if line.startswith('M441_PROGRESS ')]
    ports = [fields(line) for line in text.splitlines() if line.startswith('M441_PORT_PROGRESS ')]
    last = progress[-1]
    prior = next(p for p in progress if p['cycle'] == last['cycle']-1000000)
    end_ports = [p for p in ports if p['cycle'] == last['cycle']]
    prior_ports = [p for p in ports if p['cycle'] == prior['cycle']]
    delta_r = [p['R']-next(q['R'] for q in prior_ports if q['shard']==p['shard']) for p in end_ports]
    assert last['cycle']==38500000 and last['output']==273408 and last['terminal']==0
    assert last['output']>prior['output'] and all(n>0 for n in delta_r)
    delay = {}
    for channel, count, total in re.findall(r'M441_DELAY channel=(\S+) count=(\d+) sum=(\d+)', text):
        delay[channel] = dict(count=int(count), sum=int(total), mean_generated_cycles=int(total)/int(count))
    system = json.loads((OUT/'SYSTEM_EVENTS.json').read_text(encoding='utf-8-sig'))
    assert not system['errors']
    restart = next(e for e in system['events'] if e['id']==1074)
    restart_time = datetime.fromisoformat(restart['time_utc']).astimezone(TZ)
    last_write = datetime.fromisoformat(records[-1]['last_log_write'])
    assert 0 < (restart_time-last_write).total_seconds() < 60
    root = ROOT / 'deployment/mage_vl4b/optimization_v1/runs/M441-revision03-continuation-01'
    assert not (root/'RESULT.json').exists()
    assert not (ROOT/'deployment/mage_vl4b/optimization_v1/runs/M441-long-A-gate_up-random-03/RESULT.json').exists()
    for p in [OUT/'SYSTEM_EVENTS.json', root/'PROGRESS.json', root/'START.json', root/'RUNNING.json',
              ROOT/'scripts/optimization/m441_continue03.py', ROOT/'scripts/optimization/m441_day_review_system01.ps1', Path(__file__)]:
        evidence[str(p.relative_to(ROOT)).replace('\\','/')] = sha(p)
    r = dict(status='INCOMPLETE_M441_REVISION03_HOST_REBOOT_READ_ONLY_REVIEW', created_utc=datetime.now(timezone.utc).isoformat(),
        build_baseline='0x4D333537', build_candidate='0x4D343431', stable_rollback='0x4D395832',
        planned_comparison_groups=6, completed_comparison_groups=1, full_chain_execution_attempts=4,
        board_access=False, simulation_started=False, simulation_restarted=False, simulation_terminated_by_assistant=False,
        original_random02_verdict_preserved=True, new_complete_random_pass=False, board_performance_proven=False,
        zero_cycle_reduction_pct=(1-6741204/9319114)*100, recovery_reads=recovery, evidence=evidence, runs=records,
        partial03=dict(last=last, last_ports=end_ports, snapshots=len(progress), last_1M_output_increase=last['output']-prior['output'],
            last_1M_return_increase_per_port=delta_r, maximum_sampled_stagnant=max(p['stagnant'] for p in progress),
            generated_delay_latest_batches=delay, counters_overlap_not_additive=True, full_numerical_verdict='NOT_AVAILABLE'),
        interruption=dict(restart_event_id=1074, restart_event_time_local=restart_time.isoformat(),
            last_log_to_restart_request_s=(restart_time-last_write).total_seconds(), last_boot_utc=system['os']['last_boot_utc'],
            normal_exit_or_final_result_saved=False, supervisor_progress_is_stale=True,
            query_has_oom_or_unclean_boot_event=any(e['id'] in (2004,41,6008) for e in system['events']),
            no_simulation_checkpoint_evidence=True),
        limitations=['No historical host paging/commit/working-set series; memory bottleneck not established.',
            'No kernel CPU or peak-memory trailer for interrupted03.', 'No measured split of native DUT, VIP, observer host CPU cost.',
            'Generated latency samples are not measured board DDR latency.', 'No complete03 output/TLAST/ap_done/return-code evidence.'],
        next_step='Review a bounded protocol and supervision/restart reconciliation before any separately versioned rerun; no automatic tool or board action.')
    rows=[]
    for p in progress:
        if p['cycle'] % 1000000 == 0 or p is last:
            rows.append(f"{p['cycle']},{p['output']},{p['rx_stall']},{p['stagnant']}")
    atomic(OUT/'PROGRESS_BY_CYCLE.csv',('cycle,output_words,rx_stall,sampled_stagnant\n'+'\n'.join(rows)+'\n').encode('utf-8'),immutable=True)
    report = '''# M441 一日仿真复盘（2026-10-08，时间均为北京时间）

当前结论：revision03 原 A/gate_up Random 已被 Windows 重启中断，当前没有运行中的长链仿真。它未达到80M预算，末段仍有输出和权重返回增长；不能归为 RTL 死锁，也没有完整 Random PASS。原 gate_up Zero 的 A/B 完整数值、协议检查及27.6626% RTL周期下降保持；不是板端或完整请求提速。

## 一天具体跑了什么

从10月7日17:19到10月8日22:28，实际跨越约29小时9分钟。计划为 gate_up、mlp_down、W2 Q × Zero/Random，共6组、12次A/B执行。目前只完成 gate_up Zero 一组，但已经发生四次完整长链执行尝试，不能理解为一个进程连续算了一整天。

| 运行/阶段 | 起止时间 | 实际时间 | 进度与裁决 |
| --- | --- | --- | --- |
| B gate_up Zero02 | 7日17:19:12—22:35:20 | run 5小时16分03秒 | 6,741,204周期；311,296字全部输出，PASS |
| A gate_up Zero02 | 7日17:20:22—22:58:23 | run 5小时37分56秒 | 9,319,114周期；311,296字全部输出，PASS；与B并行，耗时不能直接相加 |
| A gate_up Random02 | 7日22:58:36—8日06:10:16 | run 7小时11分35秒 | 30M周期预算触发Fatal，212,484/311,296字，原FAIL保留 |
| 离线审计、观察器/协议修订、准备与编译窗口 | 8日06:10—13:09 | 约6小时59分日历时间 | 非长链计算时间；不能把整个窗口当作CPU工作时间。包含守卫组件启动参数拒绝及独立修复 |
| A gate_up Random03 | 8日13:09:35—末日志22:28:11 | 约9小时18分37秒 | 38.5M周期，273,408/311,296字，约87.83%；重启中断，没有DONE或完整裁决 |
| 主机重启 | 8日22:28:22发起，22:29:01开机 | 日志最后写入约10秒后发起 | Windows事件1074/6006/6005及开机时间相互印证；原监督器、子进程不再存活 |

其余B Random、mlp_down及Q尚未启动。控制器要求先通过原A Random诊断再继续；前级没有完整证据，后级停住符合门禁顺序，但测试计划的时间成本估计不充分。

## 慢在哪里、阻塞在哪里

1. **主机仿真推进很慢，是确定的实际成本。** A Zero的kernel累计CPU约20,058秒，对应run耗时20,276秒；A Random02累计CPU25,627秒，对应25,895秒，均接近平均一个CPU核的工作量。不能据此认定线程数，但可以确认没有取得多核线性加速。Random02约1159周期/秒，03约1149周期/秒；数千万周期自然需要多小时。包装TCL只记录数秒CPU和约257MB内存，不是仿真内核成本，不能误读。

2. **随机压力协议显著拉长模拟的硬件时间。** AR每次请求、R每个返回beat，以及AXIS输入/输出都可能被注入等待，四端口agent独立运行；不是每个burst只加一次延迟。生成值范围0..256，名义均值约42.67周期，03权重通道最新已导出批次均值约42.57—42.75。原版每个端口有413,440次单拍请求，需要反复承受地址与返回等待；候选burst减少地址请求，但不会取消逐beat等待。这个模型未按板端DDR校准，不能作为实板耗时预测。

3. **旧30M预算不足，导致七小时后只得到不完整结果。** 原02末1M/5M/10M仍持续增长，末段速度外推完整输出约43.784M，说明它不是在30M附近死锁。原观察器还只在成功结束时打印关键DDR/FIFO指标，失败时缺少末态。我的前期安排应先估算事务量和延迟成本，并把失败末态观察准备好，而不是依赖跑完才能诊断。原FAIL不改，03是独立协议，不是把旧结果改成PASS。

4. **03末段的阻塞是DDR返回间隙和输出背压，未显示全局停滞。** 38.5M时四端口累计gap约15.49—15.55M，RX stall约11.63M；它们可以相互重叠，四端口也并行，不能相加当作关键路径。最后1M周期输出增加7168字，四端口R分别增加9516、9464、9460、9631；最后pending仅0/0/1/2。末段仍推进，所以加预算无法解决的“卡死”目前没有证据。基线A没有候选记录FIFO，q计数为0是结构正常情况，不能拿它判断候选FIFO行为。

5. **内存成本高，但未证明它导致中断或慢速。** 原Random02内核峰值约19.83GiB，Zero A/B分别约8.07/5.52GiB。03没有正常退出，峰值和累计CPU没有保存，也没有连续分页、commit或工作集记录。本次系统事件查询没有对应OOM/异常关机记录；不能断言内存泄漏或交换盘拖慢。03原生日志约0.78MiB，未保存波形转储证据，也不足以认定海量日志/波形是主因。VIP、DUT和观察器各自CPU占比尚未测量。

6. **当前的直接停止原因是主机重启，监督流程没有重启恢复能力。** 事件1074显示开始菜单进程发起重启，22:28:37日志服务停止，22:29:01系统重新开机。只能说明这些事实，不能推断触发人的意图或归因于RTL。监督器与子进程一起消失，无法执行最后的收集和三记录同步，PROGRESS仍留下RUNNING；原记录是历史快照，并非当前存活证明。没有保存可恢复的仿真状态，不能从38.5M周期接着跑；日志与部分输出不是checkpoint。

## 反思与下一步边界

问题不是“板子算得慢”，本轮未访问COM3、未上板。主要是完整长链逐周期仿真的成本、先前不足的随机预算、诊断补齐的准备窗口，以及此次主机重启。编译约一分钟/版，不是主要耗时。

我应在继续批量安排前，先明确单链预计墙钟时间、压力模型目标和监督状态刷新，并区分完整数值验证与有界压力诊断的职责；任何改变压力模型或测试范围都应另立冻结协议，不能事后弱化原判据。还应让监控读取进程身份和主机启动时间，遇到重启明确记录中断，而不是继续显示RUNNING。修订协议前不原样重新跑十几个小时，不自动启动OOC、整壳或上板。

本报告只读取已有日志、源文件和Windows事件，新建审计证据并同步当前状态；没有启动、重跑、终止或修改任何仿真程序。原02 FAIL、原Zero结果和冻结03运行记录保留。
'''
    atomic(OUT/'REPORT.md',report.encode('utf-8'),immutable=True)
    r['report_sha256']=sha(OUT/'REPORT.md')
    r['progress_csv_sha256']=sha(OUT/'PROGRESS_BY_CYCLE.csv')
    atomic(OUT/'RESULT.json',encoded(r),immutable=True)
    digest=sha(OUT/'RESULT.json')
    rel=str((OUT/'RESULT.json').relative_to(ROOT)).replace('\\','/')
    note='## M441 一日仿真只读复盘与主机重启中断（2026-10-08）\n\nSHA '+digest+'；INCOMPLETE_M441_REVISION03_HOST_REBOOT_READ_ONLY_REVIEW。约29h09跨日：并行Zero A/B闭合，Random02 30M预算FAIL保留，03原A在38.5M/273408字后被Windows22:28:22重启中断，22:29:01开机；末1M输出+7168且四端口R增长，无末段死锁证据。当前原监督器/子进程不存活，旧RUNNING仅历史快照，无03完整结果/可恢复checkpoint。kernel CPU接近一核工作量，Random02峰值19.83GiB但分页/OOM未证实；压力按AR/R beat/AXIS，非板端校准。Zero27.6626%仅RTL周期，0板端/新收益/晋级；未重跑/kill。证据 '+rel+'，完整REPORT同目录。下一步先复核有界协议及监督重启对账，不自动恢复仿真/OOC/整壳/上板。'
    sync('latest_m441_day_review01',dict(status=r['status'],result=rel,sha256=digest,board_access=False),note)
    assert sha(OUT/'RESULT.json')==digest
    print(json.dumps(dict(status=r['status'],sha256=digest,report=str(OUT/'REPORT.md'),synced=True),ensure_ascii=False))

if __name__=='__main__':
    main()
