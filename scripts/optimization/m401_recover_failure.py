"""Package/collect saved early failure; never execute the original gate."""
import ast
import base64
import hashlib
import json
import re
import sys
from m351_workflow import ROOT,HERE,BASE,sha,atomic,encoded,sync
PKG=BASE/'candidates/M401-saved-recovery-01'
EXPECTED='9530a03974a7b330be21f39e07eaea1ef4c1eb53eacc86f89a155054994d9ca9'
def prepare():
    if PKG.exists():raise RuntimeError('Immutable recovery package exists')
    source=HERE/'m401_saved_export.py';ast.parse(source.read_bytes(),feature_version=(3,10))
    assert not any(x in source.read_text(encoding='utf-8') for x in ('import pynq','import numpy','import m401_tail_text_gate'))
    PKG.mkdir(parents=True);atomic(PKG/source.name,source.read_bytes())
    row=dict(path=source.name,bytes=source.stat().st_size,sha256=sha(source))
    atomic(PKG/'PACKAGE_MANIFEST.json',encoded(dict(files=[row],file_count=1,total_bytes=row['bytes'])))
    print('M401_SAVED_RECOVERY_PREPARED',sha(PKG/'PACKAGE_MANIFEST.json'))
def collect():
    log=ROOT/'tmp/m401/saved_recovery_uart.log';text=log.read_text(encoding='utf-8-sig')
    hashes=re.findall(r'(?m)^M401_RECOVER_SHA256=([0-9a-f]{64})\s*$',text)
    chunks=re.findall(r'(?m)^M401_RECOVER_CHUNK=(\d+)/(\d+):([A-Za-z0-9+/=]+)\s*$',text)
    assert hashes==[EXPECTED] and chunks and len(chunks)==int(chunks[0][1])
    parts=[]
    for i,(index,total,b64) in enumerate(chunks):
        p=base64.b64decode(b64,validate=True);assert int(index)==i and int(total)==len(chunks) and 0<len(p)<=900;parts.append(p)
    raw=b''.join(parts);assert hashlib.sha256(raw).hexdigest()==EXPECTED
    assert 'M401_RECOVER_DONE original_gate_rc=1' in text and '__M401_SAVED_RECOVER_RC_0__' in text
    r=json.loads(raw);assert type(r['gate_return_code']) is int and r['gate_return_code']==1 and r['status']=='FAIL'
    assert r['manifest_sha256']=='8f6e63c18bda343ce365bebab2cb48466d0268472062578527c7580c9d8d687e'
    assert not any(r[k] for k in ('overlay_loaded','model_forward_calls','fpga_transactions','allocated_buffers','released_buffers','unsafe_buffers_retained','numerical_pass','performance_pass'))
    out=BASE/'runs/M401-tail-text-board-01/BOARD_RESULT.json';atomic(out,raw,immutable=True)
    atomic(out.parent/'RECOVERY_UART.log',log.read_bytes(),immutable=True)
    value=dict(status='CLOSED_PRE_RESOURCE_PACKAGE_FAILURE',raw_sha256=EXPECTED,gate_rc=1,original_export_rc=1,recovery_export_rc=0,chunks=len(chunks),errors=r['errors'],traceback=r.get('traceback'),
               source_precheck_passed=True,overlay_loaded=False,allocated_buffers=0,model_forward_calls=0,FPGA_transactions=0,resources_retained=False,
               numerical_pass=False,performance_pass=False,original_package_unchanged=True,next_step='Repair fixed-text package labels only in immutable version02. Original saved result preserved; no video/higher gate.')
    close=BASE/'runs/M401-tail-text-failure-closure-01/RESULT.json';atomic(close,encoded(value),immutable=True);h=sha(close)
    report='# M401 固定文本资源申请前失败闭合\n\n原gate rc1/export rc1，原raw SHA `'+EXPECTED+'`。只读回收rc0，'+str(len(chunks))+'块≤900B顺序及完整SHA通过。\n\n'+str(r['errors'])+'\n\n'+r.get('traceback','')+'\n\n源码前置检查通过，但未进入模型/Overlay/DMA；实际分配0、FPGA事务0、保留资源0。原失败和45载荷包不改；只修新文本版本的文件名/范围配套，不能扩大到视频。\n'
    atomic(close.parent/'REPORT.md',report.encode('utf-8'),immutable=True)
    sync('latest_m401_tail_text_board',dict(status=r['status'],result=out.relative_to(ROOT).as_posix(),sha256=EXPECTED,fixed_text_numerical_pass=False,performance_pass=False),
         f'## M401 固定文本资源前失败结果（2026-10-04）\n\n原rc1/export1，raw `{EXPECTED}`；原字节只读回收rc0/{len(chunks)}块，源码前置PASS，错误 `{r["errors"]}`。Overlay0/DMA0/模型0/FPGA0、保留资源0；不是CMA/数值失败。原失败包保持，只修固定文本同级配套标签，不解锁视频或性能。')
    sync('latest_m401_tail_text_failure_closure',dict(status=value['status'],result=close.relative_to(ROOT).as_posix(),sha256=h,raw_sha256=EXPECTED),
         f'## M401 前资源打包失败闭合（2026-10-04）\n\n闭合 `{h}`，raw `{EXPECTED}`，实际原错误和导出范围拒绝已保存；0Overlay/分配/FPGA/模型、无保留进程。只读补取原字节，没有重跑硬件；下一步新不可变文本02修正文件名和导出器范围，必须实际包范围一致检查。')
    print(json.dumps(value|{'closure_sha256':h}))
if __name__=='__main__':
    if sys.argv[1:]==['prepare']:prepare()
    elif sys.argv[1:]==['collect']:collect()
    else:raise SystemExit('prepare | collect')
