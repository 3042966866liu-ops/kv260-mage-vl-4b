"""Recover original transfer bytes; only a restored network unlocks hardware."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import re
import m351_workflow as w
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'deployment/mage_vl4b/optimization_v1'
def decode(text,bootstrap_sha,transport_sha,package_sha,rows):
    hashes=re.findall(r'(?m)^M443_TRANSFER_SHA256=([0-9a-f]{64})\s*$',text)
    chunks=re.findall(r'(?m)^M443_TRANSFER_CHUNK=(\d+)/(\d+):([A-Za-z0-9+/=]+)\s*$',text)
    if len(hashes)!=1 or not chunks or len(chunks)!=int(chunks[0][1]):raise ValueError('Incomplete/duplicate transfer export')
    parts=[]
    for i,(index,total,data) in enumerate(chunks):
        raw=base64.b64decode(data,validate=True)
        if int(index)!=i or int(total)!=len(chunks) or not 0<len(raw)<=1800:raise ValueError('Order/count/chunk bound differs')
        parts.append(raw)
    raw=b''.join(parts);digest=hashlib.sha256(raw).hexdigest()
    if digest!=hashes[0]:raise ValueError('Complete raw SHA differs')
    r=json.loads(raw)
    if (r['bootstrap_manifest_sha256'],r['transport_manifest_sha256'],r['package_manifest_sha256'])!=(bootstrap_sha,transport_sha,package_sha):raise ValueError('Transfer identity differs')
    if r['board_gate_executed'] is not False or r['overlay_loaded'] is not False or type(r['fpga_transactions']) is not int or r['fpga_transactions']!=0:raise ValueError('Transfer scope differs')
    if r['status']=='PASS_M443_ARTIFACT_TRANSFER_ONLY':
        if r['errors'] or r['temporary_address_restored'] is not True or r['files']!=rows or not 0<=r['elapsed_s']<=630:raise ValueError('Incomplete transfer PASS')
        def identity(links):return sorted((a['family'],a['local'],a['prefixlen']) for link in links for a in link['addr_info'])
        if identity(r['addresses_before'])!=identity(r['addresses_after']) or r['default_routes_before']!=r['default_routes_after']:raise ValueError('Network identity changed')
    elif r['status']=='FAIL_M443_ARTIFACT_TRANSFER':
        if not r['errors']:raise ValueError('Empty failure')
    else:raise ValueError('Unknown transfer status')
    return digest,raw,r
def collect(log):
    p=BASE/'runs/M443-board-package-preparation-01/RESULT.json'
    prep=json.loads(p.read_text(encoding='utf-8'))
    bootstrap=ROOT/prep['bootstrap_path'];transport_path=bootstrap/'TRANSPORT_MANIFEST.json'
    if w.sha(bootstrap/'PACKAGE_MANIFEST.json')!=prep['bootstrap_manifest_sha256'] or w.sha(transport_path)!=prep['transport_manifest_sha256']:raise ValueError('Frozen bootstrap changed')
    rows=json.loads(transport_path.read_text(encoding='utf-8'))['files']
    digest,raw,r=decode(log.read_text(encoding='utf-8-sig'),prep['bootstrap_manifest_sha256'],prep['transport_manifest_sha256'],prep['manifest_sha256'],rows)
    out=BASE/'runs/M443-artifact-transfer-01'
    w.atomic(out/'BOARD_RESULT.json',raw,immutable=True)
    w.atomic(out/'COLLECTION.json',w.encoded(dict(raw_sha256=digest,log_path=log.relative_to(ROOT).as_posix(),log_sha256=w.sha(log),original_bytes=True,reexecuted=False)),immutable=True)
    w.sync('M443_artifact_transfer',dict(status=r['status'],sha256=digest,evidence_path=(out/'BOARD_RESULT.json').relative_to(ROOT).as_posix(),build_id='0x4D343433'),
        'M443 有界指定对端文件传输 '+r['status']+'；逐文件完整SHA/白名单与临时地址及默认路由回读核对。仅文件传输，0Overlay/FPGA，未上板数值或性能。证据 '+digest)
    print(json.dumps(dict(status=r['status'],sha256=digest)))
    return 0 if r['status'].startswith('PASS_') else 1
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('log',type=Path);a=ap.parse_args();raise SystemExit(collect(a.log.resolve()))
