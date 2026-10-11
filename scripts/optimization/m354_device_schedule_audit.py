"""Bind existing stable reports/RTL to hypotheses, without board or HLS runs."""
import hashlib
import json
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
sys.dont_write_bytecode=True
import m351_workflow as w

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'deployment/mage_vl4b/optimization_v1'
RUN=BASE/'runs/M354-device-schedule-audit-01'


def main():
    if RUN.exists(): raise RuntimeError('Immutable audit already exists; inspect only')
    texts={n:(ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json')}
    board=json.loads(texts['deployment/mage_vl4b/BOARD_GATE_RESULT.json'])
    prior=board['latest_m353_allocation_feasibility']
    assert w.sha(ROOT/prior['result'])==prior['sha256']
    assert all(prior['sha256'] in texts[n] for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    closure_path=BASE/'candidates/M352-load-ps-slot-01/HARDWARE_CLOSURE.json'
    evidence=json.loads(closure_path.read_text(encoding='utf-8'))
    expected={r['path']:r['sha256'] for r in evidence['checked']}
    checked=[]
    def bound(rel,sha=None):
        p=ROOT/rel
        observed=w.sha(p)
        if sha is not None: assert observed==sha,(rel,observed,sha)
        checked.append(dict(path=rel,sha256=observed,bytes=p.stat().st_size))
        return p
    implementation=bound('deployment/mage_vl4b/M134_M120_M89X2_IMPLEMENTATION_GATE_RESULT.json',evidence['evidence_documents']['M134_M120_M89X2_IMPLEMENTATION_GATE_RESULT.json']['sha256'])
    impl=json.loads(implementation.read_text(encoding='utf-8'))
    assert impl['status']=='PASS' and impl['build_id']=='0x4D395832'
    timing_rel='deployment/mage_vl4b/m120_m89x2_board_candidate/full_shell_reports/impl_timing_summary.rpt'
    timing=bound(timing_rel,expected[timing_rel]).read_text(encoding='utf-8')
    clock=re.search(r'^clk_pl_0\s+\{[^}]+\}\s+([0-9.]+)\s+([0-9.]+)',timing,re.M)
    assert clock and tuple(map(float,clock.groups()))==(5.0,200.0)
    for name in ('bit','hwh'):
        rel='deployment/mage_vl4b/m175_m120_fixed_text_candidate/overlay/m120_m89x2_t32.'+name
        bound(rel,expected[rel])
    ip_rel='m132_m120_fifo_backpressure_hls/hls/impl/ip/tellme_local_hls_m89x_runtime_kernel_1_0.zip'
    ip=bound(ip_rel,impl['ip_zip_sha256'])
    prefix='m132_m120_fifo_backpressure_hls/hls'
    rtl_name='m89x_runtime_kernel_m89x_four_Block_entry_x_0_rd_proc.v'
    with zipfile.ZipFile(ip) as z:
        rtl=z.read('hdl/verilog/'+rtl_name)
        syn_path=bound(prefix+'/syn/verilog/'+rtl_name)
        assert syn_path.read_bytes()==rtl
        export_path=bound(prefix+'/impl/ip/hdl/verilog/'+rtl_name)
        assert export_path.read_bytes()==rtl
    code=rtl.decode('utf-8')
    # Exact generated FSM: next shard start state occurs only after previous done.
    proofs=[]
    for state,instance,next_state in ((2,'grp_m89x_shard_fu_156',3),(4,'grp_m89x_shard_1_fu_184',5),(6,'grp_m89x_shard_2_fu_208',7)):
        pattern=rf'ap_ST_fsm_state{state}\s*:\s*begin\s*if\s*\(\(\({instance}_ap_done == 1\x27b1\).*?ap_NS_fsm = ap_ST_fsm_state{next_state};'
        match=re.search(pattern,code,re.S)
        assert match,(state,instance)
        proofs.append(dict(previous_done=instance+'_ap_done',wait_state=state,next_start_state=next_state,
                           exported_rtl_line=code[:match.start()].count('\n')+1))
    for state,instance in ((3,'grp_m89x_shard_1_fu_184'),(5,'grp_m89x_shard_2_fu_208'),(7,'grp_m89x_shard_3_fu_232')):
        assert re.search(rf'if \(\(1\x27b1 == ap_CS_fsm_state{state}\)\) begin\s*{instance}_ap_start_reg <= 1\x27b1;',code)
    report_models=('m89x_runtime_kernel','m89x_four','m89x_four_Block_entry_x_0_rd_proc','m89x_shard')
    estimates=[]
    for model in report_models:
        p=bound(prefix+'/syn/report/'+model+'_csynth.xml')
        tree=ET.parse(p).getroot()
        assert tree.findtext('UserAssignments/TopModelName')==model
        estimates.append(dict(model=model,worst_case_cycles=int(tree.findtext('PerformanceEstimates/SummaryOfOverallLatency/Worst-caseLatency')),
            hls_target_clock_ns=float(tree.findtext('UserAssignments/TargetClockPeriod')),
            caveat='HLS bounds for variable dimensions and interface assumptions; not measured chain time or current board frequency'))
    assert [r['worst_case_cycles'] for r in estimates]==[463850042,46380919,46380919,11595228]
    stable_source=bound('deployment/mage_vl4b/m175_m120_fixed_text_candidate/runtime/board_runtime.py','5d53ea406e57de88f8c14d9bc4e1cb0c0049ff0b8f4bcf620e05745fcd82b201').read_text(encoding='utf-8')
    assert 'time.sleep(0.0001)' in stable_source and 'kernel_finished = True' in stable_source
    summary_path=bound('deployment/mage_vl4b/optimization_v1/runs/M339-profile-04-results/PROFILE_SUMMARY.json')
    summary=json.loads(summary_path.read_text(encoding='utf-8'))
    assert summary['build_id']=='0x4D395832' and summary['prompt_tokens']==159
    assert summary['main_thread_exclusive_seconds']['device_completion_wait']==104.690723141
    stable=ROOT/'deployment/mage_vl4b/m175_m120_fixed_text_candidate'
    manifest=json.loads((stable/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))
    rel='contracts/M126_LANGUAGE_RUNTIME_CONTRACT_RESULT.json'
    cp=bound(str((stable/rel).relative_to(ROOT)).replace('\\','/'),next(r['sha256'] for r in manifest['files'] if r['path']==rel))
    contract=json.loads(cp.read_text(encoding='utf-8'))
    selected=[]
    for layer,family in ((0,'q'),(0,'gate_up'),(0,'mlp_down'),(10,'qkv')):
        chain=next(c for c in contract['chains'] if c['layer']==layer and c['family']==family)
        selected.append(dict(layer=layer,family=family,chain_index=chain['chain_index'],groups=chain['groups'],bits=chain['bits'],
            descriptors=len(chain['descriptors']),input_bytes=chain['input_bytes'],output_bytes=chain['output_bytes'],
            chain_sha256=hashlib.sha256(json.dumps(chain,sort_keys=True,separators=(',',':')).encode()).hexdigest()))
    plan='''# M354 有界设备等待诊断规格（尚未实现、未上板）

目的：在原稳定 Overlay 上记录代表性合法 chain 的输入 DMA 完成、内核完成、输出 DMA 完成的时间关系。容量失败的 PS 预读配置仍暂停，不启动其候选线程，不运行完整模型或重复 M339 画像。

1. 先离线实现独立观察器：使用原 wait_transaction 的同一轮 transaction_snapshot，不新增 AP_CTRL 读取；AP_DONE 清读后必须锁存。以主机 monotonic_ns 记录提交时刻、首次 MM2S/S2MM 完成观察和 AP_DONE，保留相邻轮询时间区间、轮询数、最大间隔。DMA 初始 idle 不能算本次完成；不能观测有效事务转换时标为 UNRESOLVED。保留原 Build 返回、错误、超时与安全释放条件。
2. 离线负例覆盖 AP_DONE 清读、短事务首次观察已完成、输入/输出不同先后、通道初始 idle、未知状态、读错误、返回错误、活动超时。观察器不能自动 reset/free/kill，也不能以 AP_IDLE 替代 AP_DONE。
3. 先核对既有 M343 的确定性输入/全输出参考能否复用到所选原 chain。没有可复算的同 SHA 输入与完整 FTZ 参考则不打包。小事务只用其原窗口尺寸；不得改变 descriptor、权重、数学、T32、TLAST。代表性最大窗口容量不足直接停止，不用小链结果推断大链。
4. 板端包默认关闭，逐文件白名单 SHA，COM3 同终端 sudo 与固定环境门禁；最多四个已选 chain 各一次，仅诊断，不重复作为数值晋级门禁或性能成绩。每事务原10秒上限；活动故障留进程和所有原缓冲，无 timeout kill。运行前在真实分配后检查余量，不采用空闲快照。
5. 输出时间是主机轮询观察区间，不能等同线级 DMA 或 PL 纯计算时间。输入结束至 AP_DONE 仍包括 DDR 访问、计算、合并和背压；精确权重 AXI stall/内部 shard 开始结束需要后续独立 RTL 波形分析或新计数器候选，不能从主机 MMIO 直接分离。
6. 本规格不授权跳过前级或启动候选电路。原始证据原子 SHA 与 BOARD/CURRENT/docs 同步后裁决；只有出现新具体证据才考虑电路改动。报告显示调度串行不能推导四倍整请求加速。
'''
    RUN.mkdir(parents=True)
    w.atomic(RUN/'PROBE_SPECIFICATION.md',plan.encode('utf-8'),immutable=True)
    r=dict(status='PASS_OFFLINE_STABLE_REPORT_AND_EXPORTED_RTL_BINDING',build_id='0x4D395832',evidence_level='L0_READ_ONLY_EXISTING_REPORT_AUDIT',
        prior_allocation_audit_sha256=prior['sha256'],verified_files=checked,ip_zip_sha256=impl['ip_zip_sha256'],
        exported_rtl_equals_synthesis_rtl=True,generated_fsm_shard_calls_serialized=True,serial_fsm_proofs=proofs,
        constrained_clock_period_ns=5.0,constrained_clock_mhz=200.0,current_board_clock_measured=False,
        implemented_timing=impl['timing'],hls_estimates=estimates,report_inside_ip_archive=False,
        report_binding_scope='Same m132 solution, matching generated modules and exact syn/export/archive RTL. Report XML itself is frozen now, not a member of the original IP archive.',
        existing_main_thread_device_wait_s=104.690723141,pure_pl_compute_s=None,
        observations=['Four shard start states in the exported FSM wait for the preceding shard done; serialization is an RTL scheduling fact',
            'HLS generated-process worst-case estimate is approximately four times a shard estimate, not a video speedup prediction',
            '200MHz is implementation timing constraint, not a new measurement of board frequency',
            'Main-thread polling observes composite DMA/kernel completion and includes polling overhead; no attribution of the whole 104.69s to computation or serialization'],
        representative_original_chains=selected,probe_specification_sha256=w.sha(RUN/'PROBE_SPECIFICATION.md'),
        probe_implemented=False,board_access=False,hardware_changed=False,fpga_transactions=0,new_speedup_verified=False,
        ps_preread_capacity_still_failed=True,video_numerical_or_performance_unlocked=False,
        next_step='Implement and offline-test a bounded completion-observer with exact original polling/AP_DONE semantics; freeze same-chain input/full reference before any diagnostic package or board run')
    w.atomic(RUN/'RESULT.json',w.encoded(r),immutable=True)
    sha=w.sha(RUN/'RESULT.json')
    note=('## M354 稳定Build报告与导出RTL调度对应（2026-10-01）\n\n'
        '稳定Build0x4D395832；IP zip同M134 SHA，生成调度RTL与综合/导出/归档字节一致，原稳定bit/hwh及实现时序报告同SHA。'
        '导出FSM确认后一shard在前一done后才start，四shard串行是调度事实；仍不能归因整个104.690723s设备等待或推导四倍请求加速。'
        '实现约束5ns/200MHz、WNS0.147ns/WHS0.010ns，不是板端时钟新测量。HLS报告最大估计为变量维度界限，非本视频链实测。'
        '仅只读审计及有界观察器规格，0板端/新综合/电路/模型/FPGA事务；PS预读容量失败仍未解锁。'
        f'证据 `{(RUN/"RESULT.json").relative_to(ROOT).as_posix()}` SHA `{sha}`。'
        '下一步离线实现观察器，覆盖AP_DONE清读/初始idle/先后关系/错误及活动超时保留；冻结原chain输入和完整参考后才准备独立诊断包。\n\n')
    w.atomic(RUN/'REPORT.md',('# M354 设备调度证据与可观测范围\n\n'+note+'\n'+ '\n'.join('- '+o for o in r['observations'])+'\n').encode('utf-8'))
    w.sync('latest_m354_device_schedule_audit',dict(status=r['status'],result=(RUN/'RESULT.json').relative_to(ROOT).as_posix(),sha256=sha,
        board_access=False,new_speedup_verified=False,probe_implemented=False,next_step=r['next_step']),note)
    summary_file=ROOT/'KV260_本轮优化完整工作记录_2026-10-01.md'
    title,rest=summary_file.read_text(encoding='utf-8-sig').split('\n',1)
    w.atomic(summary_file,(title+'\n\n'+note+rest.lstrip('\n')).encode('utf-8'))
    print(json.dumps(dict(status=r['status'],sha256=sha,serialized=True,verified_files=len(checked),board_access=False)))


if __name__=='__main__':main()
