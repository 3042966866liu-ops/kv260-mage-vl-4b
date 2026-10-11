"""Freeze, transfer and collect the CPU component, separate from FPGA gates."""
import ast
import base64
import hashlib
import json
from pathlib import Path
import re
import sys
from m441_host_io08 import atomic
from m351_workflow import ROOT, BASE, HERE, encoded, sha, sync

PKG = BASE/'candidates/M442-complete-request-parser-01'
BOOT = BASE/'candidates/M442-complete-request-parser-transfer-01'
RUN = BASE/'runs/M442-complete-request-parser-preparation-01'
OLD = BASE/'candidates/M442-direct-output-parser-02'


def manifest(directory, schema):
    rows = [dict(path=p.name, bytes=p.stat().st_size, sha256=sha(p)) for p in sorted(directory.iterdir())]
    atomic(directory/'SHA256SUMS', ''.join(r['sha256']+'  '+r['path']+'\n' for r in rows).encode(), immutable=True)
    rows.append(dict(path='SHA256SUMS', bytes=(directory/'SHA256SUMS').stat().st_size, sha256=sha(directory/'SHA256SUMS')))
    value = dict(schema=schema, files=rows, file_count=len(rows), total_bytes=sum(r['bytes'] for r in rows))
    atomic(directory/'PACKAGE_MANIFEST.json', encoded(value), immutable=True)
    return value


def transfer_collect(log):
    text=Path(log).read_text(encoding='utf-8-sig')
    hashes=re.findall(r'(?m)^M441_TRANSFER_SHA256=([0-9a-f]{64})\s*$',text)
    rows=re.findall(r'(?m)^M441_TRANSFER_CHUNK=(\d+)/(\d+):([A-Za-z0-9+/=]+)\s*$',text)
    if len(hashes)!=1 or not rows or int(rows[0][1])!=len(rows):
        raise RuntimeError('Original transfer evidence incomplete')
    parts=[]
    for i,(n,total,b64) in enumerate(rows):
        part=base64.b64decode(b64,validate=True)
        if int(n)!=i or int(total)!=len(rows) or not 0<len(part)<=900:
            raise RuntimeError('Transfer chunk order/bound differs')
        parts.append(part)
    raw=b''.join(parts)
    if hashlib.sha256(raw).hexdigest()!=hashes[0] or len(raw)>1<<20:
        raise RuntimeError('Original transfer SHA differs')
    result=json.loads(raw)
    if result['bootstrap_manifest_sha256']!=sha(BOOT/'PACKAGE_MANIFEST.json') or result['package_manifest_sha256']!=sha(PKG/'PACKAGE_MANIFEST.json'):
        raise RuntimeError('Transfer manifests differ')
    if result['overlay_loaded'] or result['fpga_transactions'] or result['board_gate_executed']:
        raise RuntimeError('Transfer executed model/PL')
    if result['status']=='PASS_M441_ARTIFACT_TRANSFER_ONLY':
        expected=json.loads((BOOT/'TRANSPORT_MANIFEST.json').read_bytes())['files']
        if result['files']!=expected or result['errors'] or not result['temporary_address_restored']:
            raise RuntimeError('Exact transfer/address restoration differs')
    elif result['status']!='FAIL_M441_ARTIFACT_TRANSFER' or not result['errors']:
        raise RuntimeError('Original transfer failure differs')
    out=BASE/'runs/M442-complete-request-parser-artifact-transfer-01/BOARD_RESULT.json'
    atomic(out,raw,immutable=True)
    sync('latest_m442_complete_request_parser_transfer',dict(status=result['status'],result=out.relative_to(ROOT).as_posix(),sha256=hashes[0],manifest_sha256=result['package_manifest_sha256'],board_gate=False),
         f'## M442 A53包指定对端传输回收（2026-10-10）\n\nSHA {hashes[0]}；{result["status"]}。manifest-first/逐文件原SHA，0Overlay/FPGA；临时地址恢复={result["temporary_address_restored"]}，原字节保存，不是数值/性能PASS。')
    print(result['status'],hashes[0])
    return 0 if result['status']=='PASS_M441_ARTIFACT_TRANSFER_ONLY' else 1


def send():
    import m441_transfer as transfer
    return transfer.send(PKG,sha(PKG/'PACKAGE_MANIFEST.json'),BOOT/'TRANSPORT_MANIFEST.json',
                         BASE/'runs/M442-complete-request-parser-artifact-transfer-01/SENDER_RESULT.json')

from m442_performance_decoder01 import decode
def collect(log):
    digest,raw,r,count=decode(Path(log).read_text(encoding='utf-8-sig'))
    out=BASE/'runs/M442-complete-request-parser-board-01/BOARD_RESULT.json'
    atomic(out,raw,immutable=True)
    atomic(out.with_name('COLLECTION.json'),encoded(dict(raw_sha256=digest,log_sha256=sha(Path(log)),hardware_rerun=False,chunks=count)),immutable=True)
    sync('latest_m442_complete_request_parser_board',dict(status=r['status'],result=out.relative_to(ROOT).as_posix(),sha256=digest,numerical_pass=r['numerical_pass'],performance_pass=False),f'## M442新解析完整请求测量回收（2026-10-10）\n\nSHA {digest}；{r["status"]}，原rc{r["gate_return_code"]}。同M441硬件及M437后11层视觉，单parser/七DMA驻留/159提示/原末帧两视图；完整视觉边界/语言/KV/logits/重试原参考及安全释放/回滚独立核对。固定4＋8全部原样本；测量回收尚非提速裁决，不删样本/不加测。')
    print(r['status'],digest,r['errors'],flush=True)
    from m442_close_performance01 import main as close
    close()
    return r['gate_return_code']
if __name__=='__main__':
    if sys.argv[1:]==['send']:raise SystemExit(send())
    if len(sys.argv)==3 and sys.argv[1]=='collect':raise SystemExit(collect(sys.argv[2]))
    if len(sys.argv)==3 and sys.argv[1]=='transfer-collect':raise SystemExit(transfer_collect(sys.argv[2]))
    raise RuntimeError('Saved collection or explicit send only')
