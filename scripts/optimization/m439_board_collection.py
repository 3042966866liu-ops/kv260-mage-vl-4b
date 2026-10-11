"""Strict saved-byte collection of isolated M439 gates; no execution."""
import argparse,base64,hashlib,json,re
from pathlib import Path
from m351_workflow import ROOT,BASE,atomic,encoded,sha,sync
from board_safety import safe_to_release
from m439_comparison import derive_comparison
MODES=('BuildID','Descriptor','Chain','Compare')
BUILDS=dict(A=0x4d333537,B=0x4d343339,R=0x4d395832)
FIXTURE=ROOT/'tmp/m439_board_support_01/BOARD_CASES.json'

def decode(log,mode,manifest_sha,prior_sha=None):
    if mode not in MODES:raise ValueError('Unknown gate')
    hashes=re.findall(r'(?m)^M439_RESULT_SHA256=([0-9a-f]{64})\s*$',log)
    codes=re.findall(r'(?m)^M439_SAVED_GATE_RC=([01])\s*$',log)
    chunks=re.findall(r'(?m)^M439_RESULT_CHUNK=(\d+)/(\d+):([A-Za-z0-9+/=]+)\s*$',log)
    if len(hashes)!=1 or len(codes)!=1 or not chunks or len(chunks)!=int(chunks[0][1]):raise ValueError('Missing/duplicate export')
    pieces=[]
    for i,(index,total,part) in enumerate(chunks):
        raw=base64.b64decode(part,validate=True)
        if int(index)!=i or int(total)!=len(chunks) or not 0<len(raw)<=1800:raise ValueError('Order/count/chunk bound')
        pieces.append(raw)
    raw=b''.join(pieces);digest=hashlib.sha256(raw).hexdigest()
    if digest!=hashes[0]:raise ValueError('Complete SHA mismatch')
    r=json.loads(raw);rc=int(codes[0])
    if r['gate_level']!=mode or r['build_id']!='0x4D343339' or r['manifest_sha256']!=manifest_sha or type(r['gate_return_code']) is not int or r['gate_return_code']!=rc:raise ValueError('Original identity/rc')
    if mode!='BuildID' and r.get('prior_raw_sha256')!=prior_sha:raise ValueError('Prior raw SHA')
    if any(r[k] is not False for k in ('full_model','video','promoted')):raise ValueError('Scope expanded')
    done=re.findall(r'(?m)^M439_DONE gate_rc=(\d+) export_rc=(\d+)\s*$',log)
    if done and (len(done)!=1 or done[0]!=(str(rc),'0')):raise ValueError('Runner/export rc')
    if r['status']=='PASS_M439_'+mode.upper():
        if rc or r['errors'] or r['package_verified'] is not True or r['unsafe_dma_buffers_retained'] or not r['safe_buffers_released'] or not r.get('stable_restored') or not r['boot_unchanged'] or not r['cmdline_unchanged']:raise ValueError('Incomplete safe PASS')
        spec=json.loads(FIXTURE.read_bytes());rows=r['transactions']
        count=dict(BuildID=2,Descriptor=2,Chain=3,Compare=217)[mode]
        allocation_groups=dict(BuildID=2,Descriptor=2,Chain=3,Compare=25)[mode]
        if len(rows)!=count or r['physical_transactions_started']!=count or len(r['allocations'])!=6*allocation_groups or len(r['overlay_loads'])!=(9 if mode=='Compare' else 2):raise ValueError('Physical lifecycle count')
        expected=[]
        for start in range(0,len(r['allocations']),6):expected.extend(reversed(r['allocations'][start:start+6]))
        if expected!=r['releases']:raise ValueError('Original-owner reverse release')
        memory=r['memory']
        if len(memory)!=allocation_groups+count or any(m.get('fixed_cma_reserve_enforced') is not False or any(type(m[k]) is not int or m[k]<0 for k in ('CmaFree','MemAvailable','Cached')) for m in memory):raise ValueError('Memory observations invalid')
        fixtures={x['path']:x for x in spec['files']}
        for row in rows:
            if row['variant'] not in BUILDS or not row['full_output_exact'] or row['output_sha256']!=row['expected_sha256'] or not safe_to_release(row['completed_snapshot']) or row['completed_snapshot']['ap_return']!=BUILDS[row['variant']] or type(row['wait_ns']) is not int or row['wait_ns']<=0:raise ValueError('Numerical/completion/Build')
            name=row.get('case')
            case=spec['cases'].get(name) if name else None
            packet=fixtures[case['packet'] if case else 'build_packet.bin'];gold=fixtures[case['golden'] if case else 'build_golden.bin']
            config=case['config_u32'] if case else spec['build_config']
            if (row['packet_sha256'],row['input_bytes'],row['expected_sha256'],row['output_bytes'],int(row['config'],16))!=(packet['sha256'],packet['bytes'],gold['sha256'],gold['bytes'],int(config,16)):raise ValueError('Frozen fixture/config')
        if rows[-1]['variant']!='R' or rows[-1]['label']!='stable-restored-build-id':raise ValueError('Stable restore missing')
        expected_cases=dict(BuildID=[None],Descriptor=['w2'],Chain=['q_full','w4_chain'])
        if mode!='Compare' and [row.get('case') for row in rows[:-1]]!=expected_cases[mode]:raise ValueError('Gate shape order')
        if mode!='BuildID' and r['numerical_pass'] is not True:raise ValueError('Numerical gate')
        if mode=='Compare':
            expected_order=[]
            for block,variant in enumerate('ABBABAAB'):
                for name in spec['comparison_cases']:
                    expected_order.extend((block,variant,name,repeat) for repeat in range(-1,8))
            if [(row.get('block'),row['variant'],row.get('case'),row.get('repeat')) for row in rows[:-1]]!=expected_order:raise ValueError('Balanced fixed order/repeats')
            if any(row.get('measured')!=(row['repeat']>=0) for row in rows[:-1]):raise ValueError('Primer or sample omitted')
            computed=derive_comparison(rows,r['overlay_loads'],spec['comparison_cases'])
            if computed!=r['comparison'] or not computed['all_cases_pass'] or r['chain_performance_pass'] is not True or r['balanced_orders']!=['A-B-B-A','B-A-A-B']:raise ValueError('Performance derivation')
    elif r['status'].startswith('FAIL_'):
        if rc!=1 or not r['errors']:raise ValueError('Invalid failure')
    else:raise ValueError('Unknown status')
    return digest,raw,r

def collect(mode,logpath,manifest_sha,prior_sha):
    digest,raw,r=decode(logpath.read_text(encoding='utf-8-sig'),mode,manifest_sha,prior_sha)
    p=BASE/('runs/M439-'+mode.lower()+'-board-01/BOARD_RESULT.json')
    atomic(p,raw,immutable=True)
    atomic(p.parent/'COLLECTION.json',encoded(dict(raw_sha256=digest,log_path=logpath.relative_to(ROOT).as_posix(),log_sha256=sha(logpath),collector_sha256=sha(Path(__file__)),gate_rc=r['gate_return_code'],reexecuted=False)),immutable=True)
    sync('latest_m439_board_'+mode.lower(),dict(status=r['status'],result=p.relative_to(ROOT).as_posix(),sha256=digest,build_id='0x4D343339',board=True),'## M439 '+mode+' 板端闭合（2026-10-07）\n\nSHA '+digest+'；'+r['status']+'，原退出码'+str(r['gate_return_code'])+'。完整原字节/输出/Build/所有者释放与实际内存核对；A为M357，R仅稳定恢复。非完整模型/视频或晋级，失败只停本级，无追加样本。')
    print(r['status'],digest)
    return r['gate_return_code']

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=MODES);p.add_argument('log',type=Path);p.add_argument('manifest_sha');p.add_argument('--prior-sha');a=p.parse_args();raise SystemExit(collect(a.mode,a.log.resolve(),a.manifest_sha,a.prior_sha))
