"""Actual SV guard component test (explicit fake signals, no M441 DUT)."""
import json
import re
import subprocess
import sys
from pathlib import Path
from m351_workflow import ROOT, BASE, atomic, encoded, sha, sync
from m441_observer03 import GUARD, selftest as guard_checks
from m441_progress03 import selftest as collector_checks


def main():
    work = ROOT / 'tmp/m441_guard03_component_01'
    evidence = BASE / 'runs/M441-guard03-component-01/RESULT.json'
    assert not work.exists() and not evidence.exists()
    monitor = (ROOT / 'tmp/m441_long_A_gate_up_03/verilog/m441_monitor.sv').read_text(encoding='utf-8-sig')
    budget = next(line for line in monitor.splitlines() if 'cyc=cyc+1;if(cyc>80000000)' in line)
    tb = r'''
`timescale 1ns/1ps
`define D guard_tb
module guard_tb;
reg clk=0;always #1 clk=~clk;
reg tx_TVALID=0,tx_TREADY=1,rx_TVALID=0,rx_TREADY=1,ap_done=0;
reg [3:0] arok=0,rok=0,iter=0,start=0,old_start=0;
reg ctrl_activity=0;
longint tx_seen=0,rx_backpressure=0,tx_backpressure=0,ctrl_seen=0;
integer cyc=0,stagnant=0;string test_case;
task automatic progress_snapshot(input integer terminal_kind);
 $display("M441_GUARD_SNAPSHOT cycle=%0d stagnant=%0d terminal=%0d",cyc,stagnant,terminal_kind);
endtask
initial begin
 if(!$value$plusargs("CASE=%s",test_case))$fatal(1,"CASE required");
 if(test_case=="budget")cyc=79999998;
end
always @(posedge clk)begin
''' + budget + '\n' + GUARD + r'''
 old_start=start;
 if(test_case=="progress")begin
  tx_TVALID=(cyc%10==0);
  if(cyc==1000100)begin progress_snapshot(1);$display("M441_GUARD_DONE");$finish;end
 end
end
endmodule
'''
    atomic(work / 'guard.sv', tb.encode('utf-8'), immutable=True)
    atomic(work / 'guard.prj', b'sv xil_defaultlib "guard.sv"\n', immutable=True)
    atomic(work / 'run.tcl', b'run all\nquit\n', immutable=True)
    runs = []
    def run(name, args):
        with (work / (name + '_console.log')).open('wb') as stream:
            p = subprocess.run(args, cwd=work, stdout=stream, stderr=subprocess.STDOUT,
                               creationflags=subprocess.CREATE_NO_WINDOW)
        runs.append(dict(name=name, tool_rc=p.returncode))
        return p.returncode
    tools = Path('D:/AMDDesignTools/2026.1/Vivado/bin')
    rc = run('compile', [str(tools / 'xelab.bat'), 'xil_defaultlib.guard_tb', '-prj', 'guard.prj', '-s', 'm441_guard03', '-log', 'compile.log'])
    assert rc == 0
    for mode in ('progress', 'stall', 'budget'):
        rc = run(mode, [str(tools / 'xsim.bat'), 'm441_guard03', '-testplusarg', 'CASE=' + mode, '-tclbatch', 'run.tcl', '-log', mode + '.log'])
        log = (work / (mode + '.log')).read_bytes().decode('utf-8', errors='backslashreplace')
        fatal = re.findall(r'^Fatal: ([^\r\n]+)', log, re.M)
        if mode == 'progress':
            assert rc == 0 and not fatal and len(re.findall(r'^M441_GUARD_DONE\s*$', log, re.M)) == 1
        else:
            assert len(fatal) == 1 and re.search(r'^M441_GUARD_SNAPSHOT .*terminal=2', log, re.M)
            assert ('progress stalled' if mode == 'stall' else 'cycle budget exceeded') in fatal[0]
        runs[-1].update(gate_rc=1 if fatal else rc, fatal=fatal)
    result = dict(status='PASS_M441_ACTUAL_SV_GUARD_COMPONENT_ONLY', runs=runs,
                  fake_signals=True, M441_DUT=False, board=False, performance=False,
                  guard_logic_sha256=sha(ROOT / 'scripts/optimization/m441_observer03.py'),
                  Python_guard_fault_checks=guard_checks(), Python_saved_snapshot_fault_checks=collector_checks(),
                  evidence=[dict(path=p.relative_to(ROOT).as_posix(), sha256=sha(p)) for p in sorted(work.glob('*')) if p.is_file()],
                  script_sha256=sha(Path(__file__)))
    atomic(evidence, encoded(result), immutable=True)
    sync('latest_m441_guard03_component01', dict(status=result['status'], result=evidence.relative_to(ROOT).as_posix(), sha256=sha(evidence), board=False),
         f'## M441 实际SV诊断守卫组件（2026-10-08）\n\nSHA {sha(evidence)}；实际相同guard与80M预算表达式，明确fake接口信号，活跃进度/1M停滞/80M预算三例；Fatal末态快照及gate失败检查通过，工具rc单独保留。Python15守卫/11回收负例。非M441 DUT/数值/性能，下一步编译独立03实际层级并进行固定协议。')
    print(result['status'], sha(evidence), runs, flush=True)


if __name__ == '__main__':
    main()
