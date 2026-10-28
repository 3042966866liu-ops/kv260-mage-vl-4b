"""Saved-only physical gate audit. Never imports PYNQ or executes a gate.

PASS requires independently collected complete binary outputs, not producer
booleans. A failed/retained gate can be saved immediately from its UART JSON.
"""
import argparse,base64,hashlib,importlib.util,json,math,re
from pathlib import Path,PurePosixPath
import numpy as np
import sys
from m351_workflow import BASE,sha,atomic,encoded
from m455456_workflow02 import synchronized
from m511n_saved_wire01 import decode
ROOT=Path(__file__).resolve().parents[2];PKG=BASE/'candidates/M511N-width-local-01'
MANIFEST=sha(PKG/'PACKAGE_MANIFEST.json')
REMOTE='/dev/shm/m511n_width_board_01/'
STABLE='/home/ubuntu/tellme_release_install_20260926/deployment/mage_vl4b/m175_m120_fixed_text_candidate/'
LEVELS=('BuildID','Descriptor','Chain','Layer','Timing')
SIZES=[6963200]*4+[389152,2621440,2621440]
def need(ok,message):
    if not ok:raise ValueError(message)
def read(p):
    def pairs(items):
        d={}
        for k,v in items:
            need(k not in d,'Duplicate JSON key');d[k]=v
        return d
    return json.loads(p.read_bytes() if isinstance(p,Path) else p,object_pairs_hook=pairs,parse_constant=lambda x:(_ for _ in ()).throw(ValueError('Nonfinite JSON')))
def pure(name):
    sys.path.insert(0,str(PKG))
    try:
        spec=importlib.util.spec_from_file_location('_j1_check_'+name,PKG/(name+'.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
    finally:sys.path.pop(0)
def finite(v):return type(v) in (int,float) and math.isfinite(v) and v>=0
def snapshot(s,build):
    need(pure('board_safety').safe_to_release(s) and s['ap_return']==build,'Unsafe kernel/DMA or wrong Build')
    need(all(s.get(k)=='' for k in ('kernel_read_error','return_read_error','dma_read_error')),'MMIO read error')
    need(all(s.get(k) is True for k in ('mm2s_idle','s2mm_idle')) and all(s.get(k) is False for k in ('mm2s_error','s2mm_error')),'DMA not idle/error')
def observation(row,s):
    o=row['observation'];e=o['events']['ap_done']
    need(o['completion_proven'] is True and o['pure_compute_time_proven'] is False and o['last_snapshot']==s,'Completion observation missing')
    need(type(o['wait_ns']) is int and 0<o['wait_ns']<=10_000_000_000 and o['wait_ns']==o['completed_ns']-o['submitted_ns'],'Observer time bound')
    need(e['clear_on_read_latched'] is True and o['submitted_ns']<=e['lower_ns']<=e['upper_ns']==e['observed_ns']<=o['completed_ns'],'AP_DONE edge missing')
def validate(r,level,files=None):
    need(sha(PKG/'PACKAGE_MANIFEST.json')==MANIFEST,'Local frozen package changed')
    profile=read(PKG/'fixtures/RESULT.json');pure('language_channel_pair_identity01').validate_joint(profile)
    need(r['gate_level']==level and level in LEVELS and r['build_id']=='0x4D343632' and r['manifest_sha256']==MANIFEST,'Gate identity')
    need(type(r['gate_return_code']) is int and r['gate_return_code'] in (0,1),'Actual gate return code')
    need(r['promoted'] is False and r['full_model'] is False,'Scope/promotion')
    if r['status']!='PASS_M511N_'+level.upper():
        need(r['gate_return_code']==1 and bool(r['errors']) and r['status'].startswith('FAIL'),'Explicit actual failure')
        return r
    need(r['gate_return_code']==0 and not r['errors'] and r['numerical_pass'] is True,'Incomplete PASS')
    need(r['candidate_id']=='M511N' and r['layer_order']==[0,18,35] and r['candidate_widths']==profile['candidate_widths'] and r['candidate_weights']==profile['candidate_weights'],'Actual exact three-weight M511N identity')
    need(r['reference_preflight']==dict(status='PASS_M511N_NATIVE_PS_GRAPH_ONLY',mock_exchanges=12,physical_transactions=0,Overlay=0,DMA=0) and r['reference_preflight_module_sha256']==sha(PKG/'m511n_native_graph01.py'),'Actual native graph preflight before Overlay')
    for k in ('stable_restored','safe_buffers_released','original_clocks_restored','configuration_application_accepted','boot_unchanged','cmdline_unchanged'):need(r.get(k) is True,'Lifecycle '+k)
    for k in ('unsafe_dma_buffers_retained','unknown_configuration_ownership','unknown_stable_programming_ownership'):need(r.get(k) is False,'Unknown '+k)
    c=r['configuration_record'];need(type(r['pid']) is int and r['pid']>0 and c['pid']==r['pid'],'Same actual PID')
    need(c['application_sha256']==sha(PKG/'CONFIGURATION_APPLICATION.json') and c['manifest_sha256']==MANIFEST and c['shell_closure_sha256']=='21a825bc7e7b5f96152639dafe630a1954ca34e376a33efb928e00f6d7f18a37','Configuration provenance')
    need(c['bit_sha256']=='b895a251c8b5cb1b74d71837712372f7f502e43b9eb9cdd3eba28918ad7080bd' and c['overlay_returned'] is True and c['configuration_credits_granted']==0 and c['observation_kind']=='same-process-kernel-CMA-trace','Actual precise configuration')
    pure('m462_configuration_retry01').validate(c)
    for k in ('initial_service','final_service'):need(r[k]['port8001_listening'] is False and r[k]['accelerator_owners']==[],'Other owner/service')
    alloc=r['allocations'];need(len(alloc)==14,'Exactly seven owners twice')
    need(r['releases']==list(reversed(alloc[:7]))+list(reversed(alloc[7:])),'Reverse safe release')
    for group in (alloc[:7],alloc[7:]):
        need([a['bytes'] for a in group]==SIZES,'Owner capacity differs')
        for a in group:need(type(a['address']) is int and 0<a['address'] and a['address']+a['bytes']<=0x80000000,'Low DDR')
        spans=sorted((a['address'],a['address']+a['bytes']) for a in group);need(all(a[1]<=b[0] for a,b in zip(spans,spans[1:])),'Overlapping owner')
    initial=r['clock_initial'];restored=r['clock_restored']
    need(len(initial['raw'])==len(restored['raw'])==4 and initial['raw']==restored['raw'] and initial['pll_raw']==restored['pll_raw'],'Original clocks/PLL restore')
    loads=r['overlay_loads'];need(len(loads)==2 and [x['label'] for x in loads]==['candidate','stable-restored'],'Only candidate then stable')
    need([x['bit_sha256'] for x in loads]==[c['bit_sha256'],'1cbf7bbb86cfe64c2349418d5a15890d735bea3fa4c999060c8a9da9ac3206ac'],'Overlay bytes')
    for x in loads:
        pure('m455_board_clocks03').validate_operating(x['clocks']);need(x['clocks']['pll_raw']==initial['pll_raw'] and x['clocks']['raw'][2:]==initial['raw'][2:],'PLL/unused clocks')
    need(len(r['environment_preflights'])==2,'Per Overlay preflight')
    for i,e in enumerate(r['environment_preflights']):
        need(e['status']=='PASS' and e['euid']==0 and e['xilinx_xrt']=='/usr' and e['tmpdir']=='/dev/shm' and e['xclbinutil']=='/usr/local/share/pynq-venv/bin/xclbinutil','Environment')
        need(e['xrt_supported'] is True and e['xcl_probe_count']==e['pynq_device_count']==1 and e['package_manifest_sha256']==('406dcca340e4604baeb761445795391c43ec26bd99fa06ffae893d597b17414f' if i else MANIFEST),'Device/manifest')
    audit=r['actual_imports'];need(audit['status']=='PASS_ACTUAL_ISOLATED_IMPORTS_BEFORE_OVERLAY' and audit['Overlay_started'] is False and audit['xcl_probe_count']==audit['pynq_device_count']==1,'Actual imports')
    need(audit['pynq_path']=='/usr/local/share/pynq-venv/lib/python3.10/site-packages/pynq/__init__.py','Actual PYNQ venv path')
    need(audit['numpy_path']=='/usr/local/share/pynq-venv/lib/python3.10/site-packages/numpy/__init__.py','Actual NumPy venv path')
    need(r['numpy_version']=='1.26.4','Actual fixed NumPy version')
    expected={'board_safety','owned_buffer_release','measurement','m462_board_support01','m120_board_common','m455_completion_observer','m462_configuration01','m462_configuration_retry01','m455_cma_trace01','m455_board_clocks03','m462_chain_export01','m462_chain_imports01','board_runtime','contract_runtime'}
    need(len(audit['modules'])==14 and {m['module'] for m in audit['modules']}==expected,'Imported module set')
    spec=read(PKG/'BOARD_CASES.json')
    for m in audit['modules']:
        n=m['module'];stable=n in ('board_runtime','contract_runtime')
        need(m['path']==(STABLE+'runtime/' if stable else REMOTE)+n+'.py','Actual import path')
        need(m['sha256']==(spec['stable_sources']['runtime/'+n+'.py']['sha256'] if stable else sha(PKG/(n+'.py'))),'Actual imported bytes')
    need(len(r['new_actual_imports'])==6 and {x['module'] for x in r['new_actual_imports']}=={'language_compensated_resident01','language_compensated_board_path01','language_factor_board_path01','language_channel_pair_identity01','j1_joint_graph01','m511n_native_graph01'},'New module set')
    for m in r['new_actual_imports']:need(m['path']==REMOTE+m['module']+'.py' and m['sha256']==sha(PKG/(m['module']+'.py')),'New import identity')
    for mem in r['memory']:
        need(all(type(mem[k]) is int and mem[k]>=0 for k in ('MemAvailable','CmaFree','Cached')),'Memory observation')
        need(mem['MemAvailable']>=64<<20 and r['memory'][0]['MemAvailable']-mem['MemAvailable']<=1<<30,'PS memory budget')
    need(r['memory'][0]['label']=='baseline','Initial memory baseline');snapshot(r['final_snapshot'],0x4D395832)
    profile=read(PKG/'fixtures/RESULT.json');cases={x['ordinal']:x for x in profile['cases']}
    parts=profile['parts'];expected_files={};transactions=r['transactions'];samples=r['samples']
    def expected_file(n,b):
        need(n not in expected_files,'Duplicate expected output');expected_files[n]=b
    def raw_transaction(t,config,packet,golden,build,label):
        need(t['label']==label and int(t['config'],16)==int(config,16) and t['input_bytes']==len(packet) and t['output_bytes']==len(golden),'Raw transaction identity')
        need(t['full_output_exact'] is True and t['output_sha256']==hashlib.sha256(golden).hexdigest(),'Whole raw output')
        snapshot(t['snapshot'],build);observation(t,t['snapshot']);expected_file(label+'_output.bin',golden)
    need(transactions,'No transactions')
    raw_transaction(transactions[-1],spec['build_config'],(PKG/'build_packet.bin').read_bytes(),(PKG/'restore_build_golden.bin').read_bytes(),0x4D395832,'stable-build')
    if level in ('BuildID','Descriptor'):
        need(len(transactions)==2 and not samples,'Exact lower gate count')
        if level=='BuildID':args=(spec['build_config'],(PKG/'build_packet.bin').read_bytes(),(PKG/'build_golden.bin').read_bytes(),'candidate-build')
        else:
            d=read(PKG/'M511N_ADMISSION.json')['descriptor'];args=(d['config_u32'],(PKG/d['packet']).read_bytes(),(PKG/d['golden']).read_bytes(),'single-descriptor')
        raw_transaction(transactions[0],*args[:3],0x4D343632,args[3])
    else:
        weights={w['path']:w for c0 in cases.values() for w in c0['weights']}
        need(r['PS_resident_weight_bytes']==sum(w['bytes'] for w in weights.values()),'Resident weight bytes')
        reads=r['PS_weight_read_records']
        need(len(reads)==len(weights) and {w['path'] for w in reads}==set(weights),'Each unique weight read exactly once')
        for w in reads:
            need(w['bytes']==weights[w['path']]['bytes'] and finite(w['read_wall_s']) and w['referenced_case_ordinals']==[c0['ordinal'] for c0 in cases.values() if any(v['path']==w['path'] for v in c0['weights'])],'Weight read provenance')
        need(math.isclose(r['PS_weight_read_wall_s'],sum(w['read_wall_s'] for w in reads),rel_tol=1e-12),'Weight time counted once')
        def ids(part,variant):return part['mlps'][0 if variant=='A' else 1]['stages']
        if level=='Chain':order=[part['cases'][2]['ordinal'] for part in parts]
        elif level=='Layer':order=[i for part in parts for v in 'AB' for i in ids(part,v)]
        else:order=[i for v in 'ABBAABBABAAB' for part in parts for i in ids(part,v)]
        need([t['ordinal'] for t in transactions[:-1]]==order,'Actual frozen joint full-chain order')
        for t in transactions[:-1]:
            c0=cases[t['ordinal']];packet=(PKG/'fixtures'/c0['name']/'packet.bin').read_bytes();golden=(PKG/'fixtures'/c0['name']/'golden.bin').read_bytes()
            need(t['config']==c0['original_contract']['config_u32'] and t['weight_bytes']==sum(w['bytes'] for w in c0['weights']) and t['input_bytes']==len(packet) and t['output_bytes']==len(golden),'Chain geometry')
            need(t['packet_exact'] is True and t['full_output_exact'] is True and t['packet_sha256']==hashlib.sha256(packet).hexdigest() and t['output_sha256']==hashlib.sha256(golden).hexdigest(),'Complete actual wire identity')
            snapshot(t['completed_snapshot'],0x4D343632);observation(t,t['completed_snapshot'])
            for k in ('weight_copy_s','weight_sync_s','input_copy_s','input_sync_s','output_prepare_s','register_program_s','device_transaction_blocking_s','output_sync_s','output_copy_s','callback_wall_s'):need(finite(t[k]),'Finite phase time')
        need(r['raw_observation_counts']=={str(i):order.count(i) for i in sorted(set(order))},'All repeated wires observed')
        for i in sorted(set(order)):
            c0=cases[i]
            for suffix,local in [('packet','packet.bin'),('output','golden.bin')]:expected_file(f'wire/case{i}_{suffix}.bin',(PKG/'fixtures'/c0['name']/local).read_bytes())
        need(len(samples)==(0 if level=='Chain' else 6 if level=='Layer' else 12),'Exact complete MLP sample count')
        def local_sample(s,part,variant,transport):
            width=part['candidate_width'];actual=part['reference_width'] if variant=='A' else width;stages=ids(part,variant)
            need(s['variant']==variant and s['comparison_width']==width and s['executed_width']==actual and s['layer']==part['layer'] and s['shape_only'] is False,'Exact per-layer numerical scope')
            need([x['ordinal'] for x in s['stages']]==stages and [x['ordinal'] for x in transport]==stages,'Per-layer chain partition')
            need(finite(s['full_MLP_wall_s']) and s['full_MLP_wall_s']>0 and finite(s['silu_up_s']) and s['asynchronous_work'] is False,'Per-layer complete wall')
            for x in s['stages']:need(all(finite(x[k]) for k in ('pack_s','exchange_blocking_wall_s','parse_s')),'Nested phase time')
            return np.load(PKG/'fixtures'/part['mlps'][0 if variant=='A' else 1]['output_path'],allow_pickle=False).tobytes()
        if level=='Layer':
            need([(s['layer'],s['variant']) for s in samples]==[(p['layer'],v) for p in parts for v in 'AB'],'Local verification order')
            cursor=0
            for part in parts:
                for j,v in enumerate('AB'):
                    s=samples[cursor//2];transport=transactions[cursor:cursor+2]
                    need(s['transport']==transport and s['sample_index']==j and s['warmup'] is False and s['full_output_exact'] is True,'Local sample linkage')
                    expected_file(f'L{part["layer"]}_{j:02}_{v}.bin',local_sample(s,part,v,transport));cursor+=2
        elif level=='Timing':
            need(''.join(s['variant'] for s in samples)=='ABBAABBABAAB','Frozen 4+8 joint sequence')
            for j,s in enumerate(samples):
                v=s['variant'];transport=transactions[j*6:j*6+6]
                need(s['comparison_id']=='M511N' and s['layer_order']==[0,18,35] and len(s['layers'])==3 and s['shape_only'] is False and s['asynchronous_work'] is False,'Actual serial joint scope')
                need(s['sample_index']==j and s['warmup']==(j<4) and s['full_output_exact'] is True and s['transport']==transport,'Joint sample and actual transport linkage')
                need(finite(s['joint_MLP_wall_s']) and s['joint_MLP_wall_s']>0 and s['full_MLP_wall_s']==s['joint_MLP_wall_s'],'Single measured joint wall alias')
                need(s['joint_MLP_wall_s']>=sum(x['full_MLP_wall_s'] for x in s['layers']),'Outer timer must include all three local MLPs')
                for k,part in enumerate(parts):expected_file(f'M511N_{j:02}_{v}_L{part["layer"]}.bin',local_sample(s['layers'][k],part,v,transport[k*2:k*2+2]))
            p=pure('language_compensated_resident01').paired_summary(samples)
            formal=samples[4:];groups={}
            for name,group in [('ABBA',formal[:4]),('BAAB',formal[4:])]:
                need(''.join(x['variant'] for x in group)==name,'Frozen order group')
                groups[name]=sum(x['full_MLP_wall_s'] for x in group if x['variant']=='A')/2-sum(x['full_MLP_wall_s'] for x in group if x['variant']=='B')/2
            p['positive_four_pair_CI_supported']=p['positive_benefit_supported']
            p['order_groups_saved_s']=groups
            p['positive_benefit_supported']=p['positive_four_pair_CI_supported'] and all(v>0 for v in groups.values())
            p['scope']='Actual serial wall of three fixed-input local T32 MLPs; not full request or sum of old measurements'
            need(r['performance']=={'M511N':p},'Independent frozen four-pair statistics')
    rows=r['raw_files'];need(len(rows)==len(expected_files) and {x['path'] for x in rows}==set(expected_files),'Exact binary whitelist')
    need(files is not None and set(files)==set(expected_files),'Independent complete saved binary whitelist')
    for x in rows:
        data=files[x['path']];need(data==expected_files[x['path']] and x['bytes']==len(data) and x['sha256']==hashlib.sha256(data).hexdigest(),'Whole independently collected binary '+x['path'])
    return r


def decode_files(text,raw_sha):
    headers=re.findall(r'(?m)^M511N_FILE_HEADER=([^\r\n]+)\r?$',text);chunks=re.findall(r'(?m)^M511N_FILE_CHUNK=(\d+)/(\d+)/(\d+):([A-Za-z0-9+/=]+)\r?$',text)
    done=re.findall(r'(?m)^M511N_FILES_DONE=([0-9a-f]{64})\r?$',text);need(done==[raw_sha],'Exporter binding and completion')
    need(0<len(headers)<=64,'Export member bound');result={};total=0;seen=set()
    for i,h in enumerate(headers):
        row=read(base64.b64decode(h,validate=True));name=row['path'];need(name not in result and not PurePosixPath(name).is_absolute() and '..' not in PurePosixPath(name).parts,'Export safe path')
        parts=[x for x in chunks if int(x[0])==i];need(parts and [int(x[1]) for x in parts]==list(range(len(parts))) and all(int(x[2])==len(parts) for x in parts),'Ordered complete file chunks')
        b=b''.join(base64.b64decode(x[3],validate=True) for x in parts);total+=len(b)
        need(total<=24<<20 and len(b)==row['bytes'] and hashlib.sha256(b).hexdigest()==row['sha256'],'Export file SHA/size bound');result[name]=b;seen.add(i)
    need(len(chunks)==sum(1 for x in chunks if int(x[0]) in seen),'Unknown export chunk');return result

def collect(log,level,filelog=None):
    # Decoder's callback checks identity; complete PASS validation occurs below.
    r,raw=decode(log.read_text(encoding='utf-8-sig'),lambda v:need(v.get('gate_level')==level and v.get('manifest_sha256')==MANIFEST,'Raw envelope identity'))
    r=read(raw);digest=hashlib.sha256(raw).hexdigest();out=BASE/'runs'/('M511N-board-'+level.lower()+'-01')
    # Preserve the original result even when strict collection rejects it.
    atomic(out/'BOARD_RESULT.json',raw,immutable=True)
    files=decode_files(filelog.read_text(encoding='utf-8-sig'),digest) if filelog else None
    try:validate(r,level,files)
    except Exception as exc:
        atomic(out/'COLLECTION_REJECTED.json',encoded(dict(status='REJECTED_SAVED_M511N_GATE_COLLECTION',reason=repr(exc),raw_sha256=digest,collector_sha256=sha(Path(__file__)),hardware_rerun=False)),immutable=True)
        synchronized('latest_m511n_board_'+level.lower()+'01',dict(status='REJECTED_SAVED_M511N_GATE_COLLECTION',result=(out/'BOARD_RESULT.json').relative_to(ROOT).as_posix(),sha256=digest,board=True,performance=False),f"## M511N {level} 原始结果采集拒绝\n\n原raw SHA `{digest}`，严格采集拒绝：{exc}。不能晋级，不重跑硬件补采集；保留原进程/owner和保存文件，仅检查本级原证据。")
        raise
    for name,b in (files or {}).items():atomic(out/'raw'/name,b,immutable=True)
    receipt=dict(status='PASS_SAVED_M511N_GATE_AUDIT' if not r['gate_return_code'] else 'SAVED_ACTUAL_M511N_GATE_FAILURE',raw_sha256=digest,log_sha256=sha(log),file_log_sha256=sha(filelog) if filelog else None,collector_sha256=sha(Path(__file__)),original_gate_rc=r['gate_return_code'],reexecuted=False,gate_scope='three fixed-input local T32 MLPs; actual serial wall, not full request' if level in ('Layer','Timing') else level)
    atomic(out/'COLLECTION.json',encoded(receipt),immutable=True)
    synchronized('latest_m511n_board_'+level.lower()+'01',dict(status=r['status'],result=(out/'BOARD_RESULT.json').relative_to(ROOT).as_posix(),sha256=digest,board=True,performance=level=='Timing' and not r['gate_return_code']),f"## M511N 真实{level}独立保存证据\n\n原raw SHA `{digest}`，原rc{r['gate_return_code']}；{r['status']}，完整输出逐字/实际配置PFN/同TTY环境/原七owner逆序释放/稳定恢复及clocks已严格核对（仅PASS时成立）。此级为{receipt['gate_scope']}，不自动晋级、不称整模型或纯计算时间；失败只本级，未知owner保留。")
    return r['gate_return_code']
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('log',type=Path);ap.add_argument('level',choices=LEVELS);ap.add_argument('--files-log',type=Path);a=ap.parse_args();raise SystemExit(collect(a.log,a.level,a.files_log))
