"""Version only the host fixture serialization to the actual producer format."""
from m351_workflow import ROOT,BASE,HERE,encoded,sha,sync
from m441_host_io08 import atomic
p=HERE/'m442_performance_support01.py'
r=dict(status='FAIL_M442_PERFORMANCE_HOST_FIXTURE_SERIALIZATION01',source_sha256=sha(p),explanation='Host fixture使用缩进JSON超过原4MiB字节预算；实际board producer原为紧凑JSON。严格decoder预算保持，新支持02只采用实际producer序列化，不修改冻结包/控制/门禁，不执行板端。',board=False)
out=BASE/'runs/M442-complete-request-parser-support-error-01/RESULT.json';atomic(out,encoded(r),immutable=True)
sync('latest_m442_parser_support_error01',dict(status=r['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out),board=False),'## M442性能支持fixture序列化拒绝（2026-10-10）\n\nSHA '+sha(out)+'；'+r['explanation'])
s=p.read_text(encoding='utf-8');anchor='def emit(v):\n    raw=encoded(v);'
assert s.count(anchor)==1
s=s.replace(anchor,"def raw_bytes(v):return (json.dumps(v,ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\\n').encode('utf-8')\ndef emit(v):\n    raw=raw_bytes(v);")
s=s.replace('atomic(saved,encoded(r),immutable=True)','atomic(saved,raw_bytes(r),immutable=True)')
s=s.replace("negative_decoder_checks=len(bads),actual_selector", "support_source_sha256=sha(__import__('pathlib').Path(__file__)),negative_decoder_checks=len(bads),actual_selector")
atomic(HERE/'m442_performance_support02.py',s.encode('utf-8'),immutable=True)
print('HOST_SUPPORT02_FROZEN',sha(HERE/'m442_performance_support02.py'))
