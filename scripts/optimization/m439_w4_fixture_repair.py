"""Freeze the time-zero test-entry failure; prepare versioned W4 support only."""
import json
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
failed=BASE/'runs/M439-baseline_w4-zero-01/RESULT.json';r=json.loads(failed.read_bytes())
assert r['status']=='FAIL_M439_NARROW_RTL' and r['done'] is None and not r['metrics'] and not r['addresses']
log=ROOT/'tmp/m439_baseline_w4_01/verilog/zero.log';s=log.read_text(encoding='utf-8-sig',errors='replace')
assert 'autotvin_s0.dat could not be opened' in s and 'UVM_FATAL' in s and '@ 0:' in s
runner=HERE/'m439_run_rtl.ps1';text=runner.read_text(encoding='utf-8');old="'tmp/m439_'+$Tag+'_01/verilog'";new="'tmp/m439_'+$Tag+'_02/verilog'";assert text.count(old)==1
new_runner=HERE/'m439_run_rtl02.ps1';atomic(new_runner,text.replace(old,new).encode('utf-8'),immutable=True)
ev=BASE/'runs/M439-W4-fixture-failure-closure-01/RESULT.json'
v=dict(status='CLOSED_M439_W4_TIME_ZERO_MISSING_POINTER_FIXTURE',raw_sha256=sha(failed),log_sha256=sha(log),simulation_engine_rc=0,
  numerical_executed=False,RTL_transactions=0,board=False,original_failure_preserved=True,
  missing_files=['c.m89x_runtime_kernel.autotvin_s'+str(i)+'.dat' for i in range(4)],
  interpretation='New W4 fixture rebuilt memory and AXIS fields but omitted four pointer argument TV files consumed by frozen VIP. The engine returned0 on UVM_FATAL; strict collector rejected. Empty-metric all() fields in old FAIL are vacuous, not MAC or protocol evidence.',
  repair='Fresh02 adds only exact zero-pointer TV from frozen M438 and audits every macro filename before compilation. DUT/weight/activation/reference unchanged.',
  runner01_sha256=sha(runner),runner02_sha256=sha(new_runner),next_step='Retry same W4 fixture initialization level only; no board/full-model expansion')
atomic(ev,encoded(v),immutable=True)
sync('latest_m439_W4_fixture_failure_closure',dict(status=v['status'],result=ev.relative_to(ROOT).as_posix(),sha256=sha(ev),build_id='0x4D333537',board=False),
     f'## M439 W4时间0测试入口失败闭合（2026-10-07）\n\nSHA {sha(ev)}；缺四个s0..s3指针TV，UVM_FATAL时间0，rc0不作PASS，0核事务/板端；旧输出检查全部未通过。新02只补同SHA参数和真实宏文件闭包，原核/数据/失败保持，不扩大测试级。')
print('M439_W4_FAILURE_CLOSED',sha(ev))
