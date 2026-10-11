"""Strict recovery of actual loader identity check; saved bytes only."""
import base64
import hashlib
import json
from pathlib import Path
import re
import sys
import m351_workflow as w
PKG=w.BASE/'candidates/M368-staged-video-03'


def decode(log):
    hashes=re.findall(r'(?m)^M368_IDENTITY_SHA256=([0-9a-f]{64})\s*$',log)
    codes=re.findall(r'(?m)^M368_IDENTITY_RC=([01])\s*$',log)
    parts=re.findall(r'(?m)^M368_IDENTITY_CHUNK=(\d+)/(\d+):([A-Za-z0-9+/=]+)\s*$',log)
    if len(hashes)!=1 or len(codes)!=1 or not parts or len(parts)!=int(parts[0][1]):raise ValueError('Incomplete/duplicate identity result')
    blocks=[]
    for i,(index,total,data) in enumerate(parts):
        raw=base64.b64decode(data,validate=True)
        if int(index)!=i or int(total)!=len(parts) or not 0<len(raw)<=900:raise ValueError('Identity chunk order/size differs')
        blocks.append(raw)
    raw=b''.join(blocks);d=hashlib.sha256(raw).hexdigest();r=json.loads(raw)
    if hashes[0]!=d or r['gate_return_code']!=int(codes[0]) or r['manifest_sha256']!=w.sha(PKG/'PACKAGE_MANIFEST.json'):raise ValueError('Identity SHA/rc/package differs')
    if any(r[k] for k in ('overlay_loads','allocations','forward_calls','fpga_transactions')):raise ValueError('Identity scope differs')
    done=re.findall(r'M368_IDENTITY_DONE gate_rc=(\d+) export_rc=(\d+)',log)
    if done and done!=[(codes[0],'0')]:raise ValueError('Identity gate/export rc differs')
    if r['status']=='PASS_ACTUAL_LOADER_IDENTITY_SEQUENCE':
        if r['errors'] or r['gate_return_code'] or not r['no_PYNQ_import'] or r['original']!=r['restored'] or not all(r['original']['checks'].values()) or r['original']['status']!='PASS' or r['original']['build_id']!='0x4D395832' or r['early_candidate_patch_rejected']['status']!='FAIL':raise ValueError('Identity sequence incomplete')
        if {k for k,v in r['early_candidate_patch_rejected']['checks'].items() if not v}!={'m120_fixed_text_board_e2e','m198_optimized_ps_vision','m208_selected_real_board_vision','clean_m120_video_candidate','candidate_manifest_external_hash','m175_text_runtime_package'}:raise ValueError('Wrong identity failure reproduced')
    elif r['gate_return_code']!=1 or not r['errors']:raise ValueError('Invalid identity failure')
    return d,raw,r


def collect(path):
    d,raw,r=decode(Path(path).read_text(encoding='utf-8-sig'));out=w.BASE/'runs/M368-identity-board-01'
    w.atomic(out/'BOARD_RESULT.json',raw,immutable=True)
    w.sync('latest_m368_identity_preflight',dict(status=r['status'],sha256=d,result=(out/'BOARD_RESULT.json').relative_to(w.ROOT).as_posix()),f'## M368 实际加载身份顺序门禁\n\n{r["status"]}，原rc{r["gate_return_code"]}，0Overlay/缓冲/forward/FPGA。冻结原offline_preflight稳定身份PASS，提前候选复现同六项FAIL，恢复原身份PASS；并非跳过校验。原SHA `{d}`，错误{json.dumps(r["errors"],ensure_ascii=False)}。只有本级PASS并同步才允许03真实视频；性能仍未解锁。')
    print(json.dumps(dict(status=r['status'],sha256=d,errors=r['errors'])))


if __name__=='__main__':collect(sys.argv[1])
