"""Audit saved M441 Random failure only; never invoke simulation or board tools."""
import csv
import io
import json
import re
from pathlib import Path
from m351_workflow import ROOT, BASE, atomic, encoded, sha, sync


def main():
    out = BASE / 'runs/M441-random-budget-audit-01'
    assert not out.exists(), 'Use the saved audit; do not overwrite'
    frozen = {
        'M441-long-A-gate_up-random-02': '50a4a7aaa36ad008c86a7b231191ca7b1f6dc94896579827696cece2d608df81',
        'M441-offline-continuation-01': '20bd4f1cdd9fc7987f3a3d49fc0cd2d6d80ee9eaebe0e39d87909fa43967a4f5',
        'M441-protocol-continuation-01': '3c7a796a207fd635e047eca4dfb77581b243a243dfcfd67825c62f0a6dccf211',
    }
    board = json.loads((ROOT / 'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    docs = [(ROOT / n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md', 'docsMILESTONES.md')]
    sources = []
    for name, digest in frozen.items():
        p = BASE / 'runs' / name / 'RESULT.json'
        assert sha(p) == digest
        assert all(digest in text for text in docs)
        assert any(digest in json.dumps(v) for v in board.values())
        sources.append(p)
        for e in json.loads(p.read_bytes()).get('evidence', []):
            q = ROOT / e['path']
            assert sha(q) == e['sha256']
            sources.append(q)
    sim = ROOT / 'tmp/m441_long_A_gate_up_02/verilog'
    # Vendor log contains non-UTF8 bytes. Keep its original SHA and visibly
    # escape those bytes; all selected monitor markers are ASCII.
    log = (sim / 'random.log').read_bytes().decode('utf-8', errors='backslashreplace')
    heartbeat = [tuple(map(int, m)) for m in re.findall(r'^M441_HEARTBEAT cycle=(\d+) output=(\d+)', log, re.M)]
    assert heartbeat[-1] == (30000000, 212484)
    assert all(b[0] > a[0] and b[1] >= a[1] for a, b in zip(heartbeat, heartbeat[1:]))
    assert 'Fatal: M441 bounded RTL cycle budget exceeded' in log
    assert not re.search(r'^M441_DONE ', log, re.M)
    windows = []
    for span in (1000000, 5000000, 10000000):
        rows = [h for h in heartbeat if h[0] >= heartbeat[-1][0] - span]
        dc, dw = rows[-1][0] - rows[0][0], rows[-1][1] - rows[0][1]
        assert dw > 0
        windows.append(dict(span_cycles=dc, first=rows[0], last=rows[-1], output_growth=dw,
                            zero_growth_intervals=sum(b[1] == a[1] for a, b in zip(rows, rows[1:])),
                            extrapolated_total_cycles=rows[-1][0] + (311296 - rows[-1][1]) * dc / dw))
    # Incomplete TV has no closing transaction marker: salvage is explicitly
    # prefix-only audit evidence, never passed through the full-run collector.
    tv = sim / 'random_result/rtl.m89x_runtime_kernel.autotvout_rx_V_data_V.dat'
    vals = [int(x, 16) for x in re.findall(r'^0x([0-9a-fA-F]+)\s*$', tv.read_text(encoding='utf-8-sig'), re.M)]
    payload = b''.join(v.to_bytes(8, 'little') for v in vals)
    golden = sim.parent / 'golden.bin'
    assert len(vals) == heartbeat[-1][1]
    assert payload == golden.read_bytes()[:len(payload)]
    support = sim / 'm89x_runtime_kernel_subsystem/m89x_runtime_kernel_env.sv'
    text = support.read_text(encoding='utf-8-sig')
    peer = ROOT / 'tmp/m441_long_B_gate_up_02/verilog/m89x_runtime_kernel_subsystem/m89x_runtime_kernel_env.sv'
    assert support.read_bytes() == peer.read_bytes()
    distribution = 'delay dist {0:=8, 0:=1, 256:=1, [0:256]:/2};'
    assert text.count(distribution) == 27
    names = ['axivip/axi_slave_seq_lib.sv', 'axivip/axi_slave_ardrv.sv', 'axivip/axi_slave_rdrv.sv',
             'axivip/axi_state.sv', 'axivip/axi_cfg.sv', 'svr/svr_slave_sequence.sv',
             'svr/svr_slave_driver.sv', 'svr/svr_master_sequence.sv', 'm441_monitor.sv']
    sources.extend([support, peer, golden, tv] + [sim / n for n in names])
    model = {n: (sim / n).read_text(encoding='utf-8-sig') for n in names}
    assert 'axi_artr.addr_delay = cfg.clatency.get_rctrl_lat();' in model[names[0]]
    assert 'axi_rtr.data_delay[0] = cfg.clatency.get_rdata_lat();' in model[names[0]]
    assert 'get_onedata_from_rqmodel' in model[names[0]]
    assert 'repeat(req.addr_delay)' in model[names[1]] and 'wait(vif.ARVALID)' in model[names[1]]
    assert 'repeat(delay)' in model[names[2]] and 'wait(vif.RREADY)' in model[names[2]]
    assert 'read_latency_mode= CHANNEL_FIRST' in model[names[4]]
    assert 'cyc%50000' in model[names[-1]] and 'output=%0d' in model[names[-1]]
    assert not list(sim.parent.rglob('*.wdb')) and not list(sim.parent.rglob('*.vcd'))
    a0 = json.loads((BASE / 'runs/M441-long-A-gate_up-zero-02/RESULT.json').read_bytes())
    b0 = json.loads((BASE / 'runs/M441-long-B-gate_up-zero-02/RESULT.json').read_bytes())
    n_ar_a = a0['metrics'][0]['AR']
    n_ar_b = b0['metrics'][0]['AR']
    # Nominal mean derived from the declared distribution, not measured samples.
    mean = (256 + 2 * 128) / (8 + 1 + 1 + 2)
    loose_mean_sum = a0['done']['cycles'] + mean * (2 * 413440 + 311296 + 6410)
    stream = io.StringIO(newline='')
    writer = csv.writer(stream)
    writer.writerow(['cycle', 'output_words'])
    writer.writerows(heartbeat)
    atomic(out / 'HEARTBEATS.csv', stream.getvalue().encode('utf-8'), immutable=True)
    result = dict(
        status='AUDITED_M441_RANDOM_TIMEOUT_CONTINUING_OUTPUT_NOT_COMPLETE_RTL',
        baseline_build_id='0x4D333537', candidate_build_id='0x4D343431',
        prior_verdicts_unchanged=True, saved_failure_sha256=frozen,
        last_cycle=30000000, last_output_words=212484, expected_output_words=311296,
        output_progress_windows=windows, partial_prefix_words=len(vals), partial_prefix_equal=True,
        full_numerical_pass=False, DDR_return_history_recorded=False,
        failed_terminal_DDR_FIFO_counters_recorded=False, saved_waveform_available=False,
        limitation='Progress of final output is proven; individual DDR ports and transient wait causes are not observable from saved failure counters.',
        delay_model=dict(range_cycles=[0, 256], declaration=distribution,
                         nominal_mean_cycles=mean, empirical_samples_recorded=False,
                         AR='One draw for each address handshake; waits after ARVALID before ARREADY.',
                         R='One draw for each returned beat, including every beat inside a burst; waits after RREADY before RVALID.',
                         AXIS='Independent delay draw for every TX and RX transfer; control AXI also randomized.',
                         ports='Four separate agents with the same distribution; global seed356, no explicit shared DDR arbiter/contention model.',
                         matched_model_source_sha256=sha(support),
                         same_seed_not_same_delay_sequence='A/B have different request counts and callback ordering; equal seed does not establish paired identical delays.'),
        full_gate_up=dict(weight_beats_per_port=413440, baseline_AR_per_port=n_ar_a,
                          candidate_AR_per_port=n_ar_b, output_beats=311296, input_beats=6410,
                          four_port_counts_not_serially_summed=True),
        estimate=dict(progress_projection_range=[min(w['extrapolated_total_cycles'] for w in windows), max(w['extrapolated_total_cycles'] for w in windows)],
                      nonoverlapped_nominal_mean_sum_cycles=loose_mean_sum,
                      proposed_fixed_cycle_budget=80000000,
                      budget_is_estimate_not_proof=True,
                      hardware_DDR_latency_calibrated=False),
        proposed_protocol='REVISED_PROTOCOL.md', revised_protocol_executed=False,
        simulation_started=False, board=False, performance=False, promoted=False,
        evidence=[dict(path=p.relative_to(ROOT).as_posix(), sha256=sha(p)) for p in sorted(set(sources))],
        audit_script_sha256=sha(Path(__file__)),
    )
    report = f'''# M441 随机延迟超时审计（2026-10-08）

只读已有失败证据。原 M441 FAIL/STOP 保留，未重跑、未上板。

## 1. 是否继续推进

最后 100 万周期：205,316 → 212,484，增加 7,168 个输出字，20 个观察间隔全部增加。
最后 500 万周期增加 35,844；最后 1,000 万周期增加 71,684，仅一个 50,000 周期间隔无增长，其后恢复。
212,484 个已保存输出字全部与原参考前缀逐位相同，但文件未闭合、无 Build 返回、无最终 TLAST/ap_done，不能判完整数值 PASS。

没有保存 WDB/VCD。DDR、MAC、背压及 FIFO 计数只在 ap_done 分支打印，预算 fatal 在该分支之前退出。
因此每个端口末段 R 计数、FIFO 末态和具体阻塞占比均为“未记录”。持续输出证明路径仍在推进，不能据此补造四端口响应曲线或排除全部暂时等待。

## 2. 随机延迟实际位置

- `m89x_runtime_kernel_env.sv:94/104`：0..256 周期分布；四端口独立 agent 使用同一规则。
- `axivip/axi_slave_seq_lib.sv:200` 与 `axi_slave_ardrv.sv:32`：每个 AR 请求在 ARVALID 后等待，再给 ARREADY。
- `axi_slave_seq_lib.sv:214/221` 与 `axi_slave_rdrv.sv:32`：每个返回 beat 在 RREADY 后等待，再给 RVALID；不是每个 burst 只延迟一次。
- `svr/svr_slave_sequence.sv:50` / `svr_slave_driver.sv:94`：输出每拍也随机等待；输入 TX 与 AXI 控制同样有随机延迟。
- `axi_cfg.sv:45`：CHANNEL_FIRST。四端口不是被脚本串行相加；也没有显式共同 DDR 控制器争用模型。

A/B 模型源码同 SHA。seed356 相同不保证两版逐事件得到相同随机延迟，因请求数量与回调顺序不同。
这是接口压力模型，尚未按板端 DDR 延迟校准；不能断言其真实程度，或把等待都归因于 DDR。

## 3. 预算估算

原版每端口 413,440 个单拍请求/返回；候选每端口 {n_ar_b:,} 个请求、同样 413,440 个返回字。
原声明分布的名义均值约 42.67 周期（不是实测抽样均值）。原版单拍结构在地址与数据阶段反复承受延迟；候选 burst 减少 AR 次数，但逐 R beat 的延迟仍保留。

末段 1/5/10M 窗口独立外推的完成总周期为约 43.784M；不是完成结果或严格上界。
将一个端口的全部 AR、R、输出 RX、输入 TX 名义等待与原 Zero 总周期简单相加，约 {loose_mean_sum / 1e6:.3f}M；此式不计重叠，不是精确模型，也不能乘四端口后称关键路径。
原 30M 固定预算明显小于两个估算量级，支持“预算不足”为当前主要解释；完整 DDR/FIFO 末态仍缺证。

建议独立修订协议固定 80M 周期，并补周期性及失败末态计数、停滞判据。该预算仅一次预先选择，不能失败后连续加大直至通过。
详细协议见 REVISED_PROTOCOL.md；尚未实现/执行。RTL 数值与协议仍在本失败级闭合后才能进入时序/上板。
'''
    protocol = '''# M441 Random 修订协议草案（独立新目录，未执行）

旧 RESULT、原 30M 预算、FAIL/STOP、Zero 结果全部保持；不恢复旧控制器。

1. 只修测试预算/观察器与控制返回码，不改 A/B DUT、权重、输入、参考、seed356、0..256延迟分布。修订源与模型逐文件 SHA；新增目录 revision03，不能覆盖02。
2. 所有剩余完整链固定80,000,000周期；每次原工具 wall预算24h，到期记录并保留进程，禁止kill。预算不能随观察结果变更。模型均值/外推不是严格保证。
3. 每50,000周期保存每端口AR/R、pending、MAC calls/accepted iterations、return gap、AR/R stall、队列写读/占用/峰值，以及TX/RX握手、输出背压和descriptor标识。global-budget fatal之前必须先导出同一套末态快照，完整原输出仍保存。
4. 固定停滞规则：TX/RX、四端口AR/R、accepted MAC与合法控制/descriptor进度全部连续1,000,000周期无变化才判全局停滞。某一个端口或输出不变不能独自触发。规则用独立小组件正/负例验证，不能因测试停滞修改DUT。
5. 任何Fatal/ERROR、未完成、缺最终TLAST/Build、字数不符、地址覆盖缺重、FIFO越界/未排空、数值不一致均FAIL，哪怕xsim返回0。先收集并三记录同步，后级才解锁；收集失败只修收集。
6. 一次固定比较，不追加样本：gate_up Random A/B各一次；若通过，mlp_down Zero A/B各一次→Random A/B各一次；再Q Zero A/B各一次→Random A/B各一次，共10个剩余RTL运行。原gate_up Zero完整A/B证据同SHA复用，不重跑。先后次序固定，未过即停本级。
7. Zero B不得比A周期增大；Random B必须严格少于A。三种形状均完整输出一致和协议通过才结束长链比较。固定seed分布对照不宣称相同随机事件轨迹，也不宣称多seed统计置信度。
8. 后续核OOC、最大FIFO/背压/timeout控制器保持关闭，必须重新绑定修订结果及精确SHA，不能假造原协议PASS以解锁。不得自动整壳/上板。

当前状态：审计与协议草案已保存；revision03生成器、观察器故障检查、控制器与实际运行均未准备/启动。下一步是实现并离线验证预算/停滞/失败快照及Fatal返回码，之后按固定协议运行。
'''
    atomic(out / 'REPORT.md', report.encode('utf-8'), immutable=True)
    atomic(out / 'REVISED_PROTOCOL.md', protocol.encode('utf-8'), immutable=True)
    result['artifacts'] = [dict(path=p.relative_to(ROOT).as_posix(), sha256=sha(p)) for p in (out / 'HEARTBEATS.csv', out / 'REPORT.md', out / 'REVISED_PROTOCOL.md')]
    ev = out / 'RESULT.json'
    atomic(ev, encoded(result), immutable=True)
    note = f'## M441 随机延迟预算只读审计（2026-10-08）\n\nSHA {sha(ev)}；末1/5/10M输出持续增长，212484字参考前缀一致但不完整PASS；无保存波形/失败末态DDR或FIFO曲线。AR按请求/R按beat及AXIS逐拍0..256延迟，四agent独立，非硬件校准。末段外推43.784M、名义无重叠估算{loose_mean_sum / 1e6:.3f}M支持30M预算不足解释，不能认定候选失败。80M独立修订协议仅草案，0新仿真/板端；原FAIL/STOP/Zero收益保持。下一步离线实现验证观察/停滞/Fatal失败返回码，再固定10个剩余运行，失败不加预算或补样本。'
    sync('latest_m441_random_budget_audit01', dict(status=result['status'], result=ev.relative_to(ROOT).as_posix(), sha256=sha(ev), board=False), note)
    print(result['status'], sha(ev), windows, 'nominal_sum', loose_mean_sum)


if __name__ == '__main__':
    main()
