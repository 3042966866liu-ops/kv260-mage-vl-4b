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

PKG = BASE/'candidates/M442-live-parser-text-01'
BOOT = BASE/'candidates/M442-live-parser-text-transfer-01'
RUN = BASE/'runs/M442-live-parser-text-preparation-01'
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
    out=BASE/'runs/M442-live-parser-text-artifact-transfer-01/BOARD_RESULT.json'
    atomic(out,raw,immutable=True)
    sync('latest_m442_live_parser_text_transfer',dict(status=result['status'],result=out.relative_to(ROOT).as_posix(),sha256=hashes[0],manifest_sha256=result['package_manifest_sha256'],board_gate=False),
         f'## M442 A53包指定对端传输回收（2026-10-10）\n\nSHA {hashes[0]}；{result["status"]}。manifest-first/逐文件原SHA，0Overlay/FPGA；临时地址恢复={result["temporary_address_restored"]}，原字节保存，不是数值/性能PASS。')
    print(result['status'],hashes[0])
    return 0 if result['status']=='PASS_M441_ARTIFACT_TRANSFER_ONLY' else 1


def send():
    import m441_transfer as transfer
    return transfer.send(PKG,sha(PKG/'PACKAGE_MANIFEST.json'),BOOT/'TRANSPORT_MANIFEST.json',
                         BASE/'runs/M442-live-parser-text-artifact-transfer-01/SENDER_RESULT.json')

_namespace_text={"__name__":"_m442_text_original_decoder"}
exec(compile('"""Strict original-byte collector derived from the proven M365 collector."""\nimport argparse\nimport json\nfrom pathlib import Path\nimport m351_workflow as w\nfrom m441_host_io08 import atomic\n\nPKG=w.BASE/\'candidates/M442-live-parser-text-01\'\n_source=(w.HERE/\'m36603_collect.py\').read_text(encoding=\'utf-8\')\n_source=_source[:_source.index(\'\\ndef collect(\')]\n_source=_source.replace(\'M366-staged-text-03\',\'M442-live-parser-text-01\').replace(\'M366\',\'M442T\').replace(\'0x4D333537\',\'0x4D343431\').replace(\'0x4d333537\',\'0x4d343431\')\n_namespace={\'__name__\':\'_m441_original_collector09\'}\nexec(compile(_source,\'<exact-derived-M365-byte-collector09>\',\'exec\'),_namespace)\n\ndef decode(log):\n    digest,raw,r=_namespace[\'decode\'](log)\n    if r[\'status\']==\'PASS_M442T_FIXED_TEXT_DIAGNOSTIC\':\n        if r.get(\'prior_board_sha256\')!=\'0b416a17669ae1a5690a62650237ce6ced33f922017625f685401ca806e2273d\':raise ValueError(\'Actual compare prerequisite differs\')\n        if r.get(\'source_compatibility_checked_before_overlay\') is not True:raise ValueError(\'Source not checked before resources\')\n        if r.get(\'additional_cma_requests_allowed\') is not False:raise ValueError(\'Allocation seal absent\')\n        if r.get(\'prior_single_layer_raw_sha256\')!=\'dde4b9e06a29c32aef24095c41817e840d72a24ad8a066bac536a4b523d976b7\' or r.get(\'head_AST_checked_before_overlay\') is not True:raise ValueError(\'Single layer/head admission differs\')\n    return digest,raw,r\n',"<strict original text decoder>","exec"),_namespace_text)

def collect(log):
    digest,raw,r=_namespace_text['decode'](Path(log).read_text(encoding='utf-8-sig'))
    if r['status']=='PASS_M442T_FIXED_TEXT_DIAGNOSTIC':
        if r['parser_candidate_sha256']!=sha(PKG/'m442_output_parser06.py') or r['parser_component_sha256']!=sha(PKG/'PARSER_COMPONENT.json') or r['parser_workers']!=1 or r['kernel_changed']:
            raise RuntimeError('New parser identity/worker/kernel differs')
        if r['additional_cma_requests_allowed'] is not False or not r['source_compatibility_checked_before_overlay']:
            raise RuntimeError('Source/allocator seal differs')
    out=BASE/'runs/M442-live-parser-text-board-01/BOARD_RESULT.json'
    atomic(out,raw,immutable=True)
    atomic(out.with_name('COLLECTION.json'),encoded(dict(raw_sha256=digest,log_sha256=sha(Path(log)),hardware_rerun=False)),immutable=True)
    sync('latest_m442_live_parser_text_board',dict(status=r['status'],result=out.relative_to(ROOT).as_posix(),sha256=digest,numerical_pass=r['numerical_pass'],performance_pass=False),f'## M442真实解析路径固定文本裁决（2026-10-10）\n\nSHA {digest}；{r["status"]}，原rc{r["gate_return_code"]}。同M441硬件/原30token/36层/154family/151936logits/72KV完整参考和七DMA封锁；只显式candidate解析器改变，原字节/安全恢复核对。非完整请求性能，失败仅本级。')
    print(r['status'],digest,r.get('errors'),flush=True)
    return r['gate_return_code']
if __name__=='__main__':
    if sys.argv[1:]==['send']:raise SystemExit(send())
    if len(sys.argv)==3 and sys.argv[1]=='collect':raise SystemExit(collect(sys.argv[2]))
    if len(sys.argv)==3 and sys.argv[1]=='transfer-collect':raise SystemExit(transfer_collect(sys.argv[2]))
    raise RuntimeError('Saved collection or explicit send only')
