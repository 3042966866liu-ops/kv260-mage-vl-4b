"""Strict original-byte board collection; no board execution from this module."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import re
import m351_workflow as w
from board_safety import safe_to_release

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'deployment/mage_vl4b/optimization_v1'
MODES=('BuildID','Descriptor','Chain','Compare')

def decode(log,mode,manifest_sha,prior_sha=None):
    if mode not in MODES:raise ValueError('Unknown mode')
    hashes=re.findall(r'(?m)^M357_RESULT_SHA256=([0-9a-f]{64})\s*$',log)
    codes=re.findall(r'(?m)^M357_SAVED_GATE_RC=([01])\s*$',log)
    chunks=re.findall(r'(?m)^M357_RESULT_CHUNK=(\d+)/(\d+):([A-Za-z0-9+/=]+)\s*$',log)
    if len(hashes)!=len(codes) or len(hashes)!=1 or not chunks or len(chunks)!=int(chunks[0][1]):raise ValueError('Missing/duplicate header/chunk')
    parts=[]
    for i,(index,total,data) in enumerate(chunks):
        if int(index)!=i or int(total)!=len(chunks):raise ValueError('Chunk order/count differs')
        raw=base64.b64decode(data,validate=True)
        if not 0<len(raw)<=1800:raise ValueError('Chunk bound differs')
        parts.append(raw)
    raw=b''.join(parts);digest=hashlib.sha256(raw).hexdigest()
    if digest!=hashes[0]:raise ValueError('Complete raw SHA differs')
    result=json.loads(raw);rc=int(codes[0])
    if result['gate_level']!=mode or result['build_id']!='0x4D333537' or result.get('manifest_sha256')!=manifest_sha:raise ValueError('Gate/package identity differs')
    if type(result['gate_return_code']) is not int or result['gate_return_code']!=rc:raise ValueError('Original gate rc differs')
    if mode!='BuildID' and result.get('prior_raw_sha256')!=prior_sha:raise ValueError('Prior lower gate identity differs')
    if any(result[k] is not False for k in ('full_model','video','promoted')):raise ValueError('Lower gate scope differs')
    done=re.findall(r'M357_DONE gate_rc=(\d+) export_rc=(\d+)',log)
    if done and (len(done)!=1 or done[0]!=(str(rc),'0')):raise ValueError('Runner/export rc differs')
    if result['status']=='PASS_M357_'+mode.upper():
        if rc or result['errors'] or result['package_verified'] is not True or result['unsafe_dma_buffers_retained'] or not result['safe_buffers_released'] or not result.get('stable_restored') or not result['boot_unchanged'] or not result['cmdline_unchanged']:raise ValueError('Incomplete PASS/rollback')
        rows=result['transactions'];count=9 if mode=='Compare' else 2
        if len(rows)!=count or result['physical_transactions_started']!=count:raise ValueError('Physical transaction count differs')
        if any(not r['full_output_exact'] or r['output_sha256']!=r['expected_sha256'] or not safe_to_release(r['completed_snapshot']) or r['completed_snapshot']['ap_return']!=(0x4d395832 if r['variant']=='A' else 0x4d333537) or type(r['wait_ns']) is not int or r['wait_ns']<=0 for r in rows):raise ValueError('Full output/completion/build differs')
        if rows[-1]['variant']!='A' or rows[-1]['label']!='stable-restored-build-id':raise ValueError('Stable restore transaction absent')
        if len(result['allocations'])!=6*count:raise ValueError('Owned allocation count differs')
        expected=[]
        for i in range(0,len(result['allocations']),6):expected.extend(reversed(result['allocations'][i:i+6]))
        if expected!=result['releases']:raise ValueError('Owned allocation/release lifecycle differs')
        if len(result['memory'])!=2*count or any(r['CmaFree']<r['required_cma_free_bytes'] or r['required_cma_free_bytes']!=64<<20 for r in result['memory']):raise ValueError('Actual transaction reserve rejected')
        case=json.loads((ROOT/'tmp/m357_board_fixture_02/BOARD_CASES.json').read_text(encoding='utf-8'))
        fixtures={r['path']:r for r in case['files']}
        for row in rows:
            prefix='build' if 'build-id' in row['label'] else ('descriptor' if mode=='Descriptor' else 'q')
            packet=fixtures[prefix+'_packet.bin'];golden=fixtures[prefix+'_golden.bin']
            config=case['build_config'] if prefix=='build' else (case['single_descriptor_chain'] if prefix=='descriptor' else case['original_q_case']['chain'])['config_u32']
            if row['packet_sha256']!=packet['sha256'] or row['expected_sha256']!=golden['sha256'] or row['input_bytes']!=packet['bytes'] or row['output_bytes']!=golden['bytes'] or int(row['config'],16)!=int(config,16):raise ValueError('Frozen original fixture/config differs')
        if mode!='BuildID' and result['numerical_pass'] is not True:raise ValueError('Numerical gate not passed')
        if mode=='Compare':
            if ''.join(r['variant'] for r in rows[:8])!='ABBABAAB' or result['balanced_orders']!=['A-B-B-A','B-A-A-B'] or result['chain_performance_pass'] is not True:raise ValueError('Balanced performance gate rejected')
            c=result['comparison']
            import statistics
            a=[r['wait_ns'] for r in rows[:8] if r['variant']=='A'];b=[r['wait_ns'] for r in rows[:8] if r['variant']=='B']
            if c['original_ns']!=a or c['candidate_ns']!=b or c['original_median_ns']!=statistics.median(a) or c['candidate_median_ns']!=statistics.median(b) or max(b)>=min(a) or c['same_observed_ps_clocks'] is not True or c['pure_compute'] is not False:raise ValueError('Comparison derivation differs')
            loads=result['overlay_loads']
            if len(loads)!=count or any(r['clocks_mhz']!=loads[0]['clocks_mhz'] for r in loads):raise ValueError('Actual observed clocks differ')
    elif result['status'].startswith('FAIL_'):
        if rc!=1 or not result['errors']:raise ValueError('Invalid failure record')
    else:raise ValueError('Unknown status')
    return digest,raw,result

def collect(mode,logpath,manifest_sha,prior_sha):
    text=logpath.read_text(encoding='utf-8-sig')
    digest,raw,result=decode(text,mode,manifest_sha,prior_sha)
    directory=BASE/('runs/M357-'+mode.lower()+'-board-01')
    w.atomic(directory/'BOARD_RESULT.json',raw,immutable=True)
    w.atomic(directory/'COLLECTION.json',w.encoded(dict(raw_sha256=digest,log_path=logpath.relative_to(ROOT).as_posix(),log_sha256=w.sha(logpath),mode=mode,gate_rc=result['gate_return_code'],board_result_not_reexecuted=True)),immutable=True)
    w.sync('M357_board_'+mode.lower(),dict(status=result['status'],sha256=digest,evidence_path=(directory/'BOARD_RESULT.json').relative_to(ROOT).as_posix(),build_id='0x4D333537'),
        'M357 新电路 '+mode+' 上板裁决 '+result['status']+'；完整原字节/rc/输出及安全回收核对，仅当前级，无完整模型/视频或晋级。证据 '+digest)
    print(json.dumps(dict(status=result['status'],sha256=digest,gate_rc=result['gate_return_code'])))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('mode',choices=MODES);ap.add_argument('log',type=Path);ap.add_argument('manifest_sha');ap.add_argument('--prior-sha');a=ap.parse_args();collect(a.mode,a.log,a.manifest_sha,a.prior_sha)
