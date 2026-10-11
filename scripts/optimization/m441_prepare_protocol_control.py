"""Freeze tested local protocol controls without starting any FPGA tool."""
import ast
import json
import subprocess
import sys
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
from m441_protocol_control import OUT,PREP,verified_prep,synchronized,RUNTIME_NAMES

def main():
    dest=BASE/'runs/M441-protocol-control-preparation-01'
    assert not dest.exists(),'Existing preparation: read only'
    verified_prep()
    checks=BASE/'runs/M441-protocol-evidence-support-checks-02/RESULT.json'
    r=synchronized(checks,'PASS_M441_PROTOCOL_COLLECTOR_FAULT_CHECKS_ONLY','latest_m441_protocol_collector_checks')
    assert len(r['rejected_cases'])==31 and r['source_sha256']==sha(HERE/'m441_protocol_evidence.py')
    assert not (BASE/'runs/M441-offline-continuation-01/RESULT.json').exists(),'This guard test requires the genuine missing prerequisite'
    sim=OUT/'verilog'
    before={p.relative_to(OUT).as_posix():sha(p) for p in OUT.rglob('*') if p.is_file()}
    dest.mkdir(parents=True)
    cases=[]
    for label,args,rc,marker in [
        ('read_only_check',['check'],0,'BLOCKED_BEFORE_ANY_TOOL_OR_BOARD'),
        ('default_disabled',['compile'],1,'Default disabled: explicit --run required'),
        ('missing_long_chain_gate',['compile','--run'],1,'Missing prerequisite: deployment/mage_vl4b/optimization_v1/runs/M441-offline-continuation-01/RESULT.json')]:
        proc=subprocess.run([sys.executable,'-B',str(HERE/'m441_protocol_control.py'),*args],capture_output=True)
        atomic(dest/(label+'.stdout.txt'),proc.stdout,immutable=True)
        atomic(dest/(label+'.stderr.txt'),proc.stderr,immutable=True)
        okay=proc.returncode==rc and marker in (proc.stdout+proc.stderr).decode('utf-8-sig')
        cases.append(dict(name=label,args=args,original_rc=proc.returncode,expected_rc=rc,pass_gate=okay))
    after={p.relative_to(OUT).as_posix():sha(p) for p in OUT.rglob('*') if p.is_file()}
    unchanged=before==after
    no_tool_outputs=not any((sim/n).exists() for n in ('compile.log','compile_console.log','compile_exit.json','xsim.dir'))
    names=('m441_protocol_control.py','m441_collect_max_protocol.py','m441_protocol_evidence.py',
           'm441_prepare_max_protocol.py','m441_prepare_protocol_control.py','m441_protocol_support_checks02.py',
           'm357_uvm_log_evidence.py','m351_workflow.py')
    rows=[]
    for name in names:
        path=HERE/name;ast.parse(path.read_text(encoding='utf-8-sig'),feature_version=(3,10))
        rows.append(dict(path=path.relative_to(ROOT).as_posix(),sha256=sha(path)))
    success=all(x['pass_gate'] for x in cases) and unchanged and no_tool_outputs
    result=dict(status='PREPARED_M441_PROTOCOL_CONTROL_COLLECTOR_GUARDS' if success else 'FAIL_M441_PROTOCOL_CONTROL_GUARDS',
        build_id='0x4D343431',cases=cases,prepared_inputs_unchanged=unchanged,no_tool_outputs=no_tool_outputs,
        files=rows,maximum_input_sha256=sha(PREP),collector_fault_checks_sha256=sha(checks),
        runtime_bookkeeping_names=sorted(RUNTIME_NAMES),
        snapshot_contract='All files verified on copy; executable/model and every file outside the explicit runtime bookkeeping set must retain SHA. Compile evidence binds the original snapshot; timeout evidence binds the synchronized maximum result. Runtime bookkeeping may change and is preserved as evidence.',
        next_step='Wait for saved complete long-chain RTL comparisons. If they pass, close same-constraint core routed timing before enabling local max FIFO/backpressure/timeout gates. No board or full shell is unlocked.',
        board=False,RTL_simulated=False,performance=False,promoted=False)
    ev=dest/'RESULT.json';atomic(ev,encoded(result),immutable=True)
    report='# M441 后续最大协议控制准备\n\n'+('准备通过' if success else '准备失败')+'。真实 CLI 的默认关闭与缺少长链前置证据两种拒绝已检查；未启动 xelab/xsim，189份输入保持原字节。\n\n31项收集故障检查复用已保存结果。编译模型严格同 SHA，运行日志等6项可变元数据明确区分；超时结果必须引用已通过的最大协议结果。\n\n长链仿真仍由已有有限控制器继续，成功后还须同约束核时序闭合；本记录不代表 RTL、板端或性能通过。\n'
    atomic(dest/'REPORT.md',report.encode('utf-8'),immutable=True)
    sync('latest_m441_protocol_control_preparation',dict(status=result['status'],result=ev.relative_to(ROOT).as_posix(),sha256=sha(ev),board=False),
         f'## M441 最大协议控制准入准备（2026-10-07）\n\nSHA {sha(ev)}；{result["status"]}。真实CLI默认关闭/缺失长链结果均提前拒绝，输入未变，0工具启动/板端。复用31项收集故障检查；编译模型同SHA与超时负例前置绑定。长链比较及同约束路由时序未通过不得执行最大协议，更未解锁整壳或上板。')
    print(result['status'],sha(ev),cases,unchanged,no_tool_outputs)
    if not success:raise SystemExit(1)

if __name__=='__main__':main()
