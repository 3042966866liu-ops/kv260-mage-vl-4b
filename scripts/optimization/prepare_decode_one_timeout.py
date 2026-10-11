"""Create an isolated negative RTL watchdog test only after normal CoSim passes."""
from pathlib import Path
import re
import shutil
from measurement import sha256,write_json
root=Path(__file__).resolve().parents[2]
source=root/'tmp/op01_decode_one_rtl/hls/sim'
report=source/'report/op01_decode_one_kernel_cosim.rpt'
if not report.is_file() or not re.search(r'Verilog\s*\|\s*Pass',report.read_text()):
    raise RuntimeError('Normal CoSim PASS required before isolated negative test')
dest=root/'tmp/op01_decode_one_timeout'
if dest.exists():raise RuntimeError('Immutable staging exists')
if not (source/'tv').is_dir():raise RuntimeError('Missing sibling tv')
for name in ['verilog','tv']:
    shutil.copytree(source/name,dest/name)
tb=dest/'verilog/op01_decode_one_kernel.autotb.v'
text=tb.read_text()
if text.count('endmodule')!=1:raise RuntimeError('Unexpected generated TB structure')
watchdog='''
// Isolated expected failure: a too-small execution budget must reject a started transaction.
initial begin
    wait (start_cnt > 0);
    $display("OP01_WATCHDOG_ARMED start_cnt=%0d", start_cnt);
    repeat (200) @ (posedge AESL_clock);
    if (finish_cnt == 0) begin
        $display("OP01_RTL_TIMEOUT_TRIGGERED finish_cnt=%0d total=%0d", finish_cnt, AUTOTB_TRANSACTION_NUM);
        $fatal(1, "OP01 bounded timeout expired before ap_done");
    end else begin
        $fatal(1, "OP01 negative test invalid: transaction already completed");
    end
end
'''
tb.write_text(text.replace('endmodule',watchdog+'\nendmodule'))
runner=dest/'verilog/run_xsim.bat'
calls=[line for line in runner.read_text().splitlines() if line.strip().lower().startswith('call ')]
if len(calls)!=2 or '/xelab ' not in calls[0] or '/xsim ' not in calls[1]:
    raise RuntimeError('Unexpected generated xsim runner')
# Preserve elaboration failure and simulator failure, never hide either with trailing commands.
(dest/'verilog/run_timeout.cmd').write_text('@echo off\nset PATH=\n'+calls[0]+'\nif errorlevel 1 exit /b %errorlevel%\n'+calls[1]+'\nexit /b %errorlevel%\n')
write_json(dest/'PREPARATION.json',dict(status='PREPARED_NOT_EXECUTED',normal_report_sha256=sha256(report),
    source_tb_sha256=sha256(source/'verilog/op01_decode_one_kernel.autotb.v'),
    modified_tb_sha256=sha256(tb),watchdog_cycles_after_start=200,
    scope='timeout rejection only, not missing-input recovery; normal artifacts untouched',
    sibling_tv_files=sum(p.is_file() for p in (dest/'tv').rglob('*'))))
print('OP01_TIMEOUT_PREPARED_NOT_EXECUTED')
