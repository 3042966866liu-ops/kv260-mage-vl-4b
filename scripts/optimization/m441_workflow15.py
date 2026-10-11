import json,sys
from pathlib import Path
import m351_workflow as w
from m441_host_io08 import atomic
from m441_performance_collect15 import PKG
def receipt():
 logs=w.ROOT/'tmp/m441_performance15';a=(logs/'assembly.log').read_text(encoding='utf-8-sig');s=(logs/'upload_syntax.log').read_text(encoding='utf-8-sig')
 assert 'M44115_ALL_PAYLOAD_SHA_VERIFIED_NO_GATE' in a and '__M441P_ASSEMBLY_RC_0__' in a and '__M441P_SYNTAX_RC_0__' in s
 out=w.BASE/'runs/M441-complete-request-performance-transfer-15/RESULT.json'
 value=dict(status='PASS_M441_PERFORMANCE_TRANSFER_ONLY15',manifest_sha256=w.sha(PKG/'PACKAGE_MANIFEST.json'),board_executed=False,logs=[dict(path=p.relative_to(w.ROOT).as_posix(),sha256=w.sha(p)) for p in sorted(logs.glob('*.log'))])
 atomic(out,w.encoded(value),immutable=True)
 w.sync('latest_m441_complete_request_transfer',dict(status=value['status'],result=out.relative_to(w.ROOT).as_posix(),sha256=w.sha(out),manifest_sha256=value['manifest_sha256']),f'## M441 精确CMA新性能15传输闭合（2026-10-09）\n\nSHA {w.sha(out)}；原09白名单同SHA复用，新15manifest-first900B/全文件SHA/root组装/bash-n通过。0执行；下一步独立固定4＋8，未知申请仍拒绝，原09FAIL保持。')
 print(value['status'],w.sha(out))
if __name__=='__main__':
 assert sys.argv[1:]==['receipt'];receipt()
