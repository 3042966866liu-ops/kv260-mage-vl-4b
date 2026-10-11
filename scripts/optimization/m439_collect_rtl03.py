"""Saved-only coverage accepts original W4 interleaved address issue order."""
import json
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
ev=BASE/'runs/M439-W4-address-coverage-collector-03/RESULT.json'
if not ev.exists():
    p=ROOT/'tmp/m439_baseline_w4_02/verilog/zero.log'
    log=p.read_text(encoding='utf-8-sig',errors='replace')
    import re
    addresses=[int(a,16) for a in re.findall(r'M439_AR shard=0 address=([0-9a-fA-F]+)',log)]
    assert addresses and addresses!=sorted(addresses),'Original W4 may interleave word addresses'
    r=dict(status='PREPARED_SAVED_ONLY_W4_ADDRESS_COVERAGE_REPAIR',board=False,dut_changed=False,simulation_rerun=False,
      original_collector_sha256=sha(HERE/'m439_collect_rtl.py'),wrapper02_sha256=sha(HERE/'m439_collect_rtl02.py'),
      rationale='Original W4 HLS may issue pair words in an interleaved order. Exact nonoverlapping coverage must sort intervals, not require original requests chronologically ascending. Count/length/RLAST/full output remain strict. Candidate monotonic request order is reported separately.')
    atomic(ev,encoded(r),immutable=True)
    sync('latest_m439_W4_address_collector',dict(status=r['status'],result=ev.relative_to(ROOT).as_posix(),sha256=sha(ev),build_id='0x4D343339',board=False),
      f'## M439 W4地址覆盖只读收集修正（2026-10-07）\n\nSHA {sha(ev)}；原W4 pair字发出顺序可交错，不能强制地址按时间递增；collector尚未对02模拟结果执行。03仅按地址排序核对严格无重复/无空洞覆盖，保留原时间顺序和单独单调字段，完整输出/字数/RLAST检查不变，不重跑仿真。')
r=json.loads(ev.read_bytes());assert sha(HERE/'m439_collect_rtl.py')==r['original_collector_sha256'] and sha(HERE/'m439_collect_rtl02.py')==r['wrapper02_sha256']
s=(HERE/'m439_collect_rtl02.py').read_text(encoding='utf-8')
anchor="ns={'__name__'"
extra='''s=s.replace("base=rows[0]['address'] if rows else 0", "base=min(x['address'] for x in rows) if rows else 0")
s=s.replace("for x in rows:\\n                good=", "for x in sorted(rows,key=lambda item:item['address']):\\n                good=")
s=s.replace("burst_histogram=dict(hist),exact_nonoverlapping_coverage=good", "burst_histogram=dict(hist),request_order_monotonic=rows==sorted(rows,key=lambda item:item['address']),exact_nonoverlapping_coverage=good")
'''
assert s.count(anchor)==1;s=s.replace(anchor,extra+anchor)
ns={'__name__':'m439_collect_rtl03','__file__':str(HERE/'m439_collect_rtl03.py')};exec(compile(s,str(HERE/'m439_collect_rtl03.py')+':saved-only','exec'),ns)
