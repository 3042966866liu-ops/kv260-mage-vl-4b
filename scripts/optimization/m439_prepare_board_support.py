"""Freeze first-version isolated board fixtures/control. Never load an Overlay."""
import ast
import hashlib
import json
import struct
from m351_workflow import ROOT, BASE, HERE, atomic, encoded, sha, sync
from m438_prepare import values, PREFIX
from m439_prepare_rtl import w4_fixture
from m355_reference import full_reference

OUT = ROOT / 'tmp/m439_board_support_01'

def replace_once(text, old, new):
    assert text.count(old) == 1, old[:100]
    return text.replace(old, new)

def freeze(path, raw):
    atomic(OUT/path, raw.encode('utf-8') if isinstance(raw, str) else raw, immutable=True)

def fixture(name, packet, golden, weights, config, chain=None):
    freeze(name+'_packet.bin', packet); freeze(name+'_golden.bin', golden)
    windows=[]
    for i,raw in enumerate(weights):
        path=name+'_w'+str(i)+'.bin';freeze(path,raw)
        windows.append(dict(path=path,bytes=len(raw),sha256=sha(OUT/path)))
    return dict(name=name,packet=name+'_packet.bin',golden=name+'_golden.bin',
                config_u32=hex(config),windows=windows,window_bytes_per_port=len(weights[0]),
                packet_bytes=len(packet),output_bytes=len(golden),chain=chain,
                packet_sha256=hashlib.sha256(packet).hexdigest(),golden_sha256=hashlib.sha256(golden).hexdigest())

def main():
    assert not OUT.exists(), 'Existing support; inspect only'
    original=HERE/'m357_board_probe.py';text=original.read_text(encoding='utf-8')
    text=text.replace('m357','m439').replace('M357','M439').replace('0x4d333537','0x4d343339').replace('0x4D333537','0x4D343339')
    text=replace_once(text,'OLD_BUILD=0x4d395832', 'OLD_BUILD=0x4d333537\nRESTORE_BUILD=0x4d395832\nREPEATS=8')
    text=replace_once(text,"row=dict(label=label,**meminfo(),required_cma_free_bytes=64<<20);result['memory'].append(row)\n        if row['CmaFree']<64<<20:raise MemoryError('Real allocated diagnostic reserve below64MiB: '+str(row['CmaFree']))", "row=dict(label=label,**meminfo(),fixed_cma_reserve_enforced=False);result['memory'].append(row)\n        if any(type(row[k]) is not int or row[k]<0 for k in ('CmaFree','MemAvailable','Cached')):raise RuntimeError('Invalid actual memory counters')")
    text=replace_once(text,"target=STABLE if variant=='A' else HERE\n        digest=STABLE_SHA if variant=='A' else args.manifest_sha", "target=STABLE if variant=='R' else HERE\n        digest=STABLE_SHA if variant=='R' else args.manifest_sha")
    text=replace_once(text,"overlay=Overlay(str(target/'overlay/m120_m89x2_t32.bit'),download=True)", "bit=target/('baseline/overlay/m120_m89x2_t32.bit' if variant=='A' else 'overlay/m120_m89x2_t32.bit')\n        overlay=Overlay(str(bit),download=True)")
    text=replace_once(text,"expected_build=OLD_BUILD if variant=='A' else NEW_BUILD", "expected_build=RESTORE_BUILD if variant=='R' else (OLD_BUILD if variant=='A' else NEW_BUILD)")
    text=replace_once(text,"bit_sha256=sha256(target/'overlay/m120_m89x2_t32.bit')", "bit_sha256=sha256(bit)")
    begin=text.index('        else:\n            case=spec[\'original_q_case\']')
    end=text.index("        phase[0]='restore-stable'",begin)
    text=text[:begin]+'''        else:
            cases=[spec['cases']['w2']] if args.mode=='Descriptor' else [spec['cases']['q_full'],spec['cases']['w4_chain']]
            if args.mode=='Compare':cases=[spec['cases'][n] for n in spec['comparison_cases']]
            variants='ABBABAAB' if args.mode=='Compare' else 'B'
            result['balanced_orders']=['A-B-B-A','B-A-A-B'] if args.mode=='Compare' else []
            result['cache_policy']='Natural cache. Exact fixture staging before timing; no clearing or eviction.'
            result['comparison_repeats']=REPEATS if args.mode=='Compare' else 1
            for index,variant in enumerate(variants):
                label=args.mode.lower()+'-'+str(index)+'-'+variant
                load(variant,label)
                for case in cases:
                    name=case['name'];packet=(HERE/case['packet']).read_bytes();golden=(HERE/case['golden']).read_bytes()
                    allocate_owned([case['window_bytes_per_port']]*4+[len(packet),len(golden)],label+':'+name)
                    phase[0]='stage:'+label+':'+name
                    for buffer,window in zip(buffers[:4],case['windows']):
                        path=(ROOT/window['installed_path']) if 'installed_path' in window else (HERE/window['path'])
                        before=identity(path)
                        if before[2]!=window['bytes']:raise RuntimeError('Weight identity size differs')
                        with path.open('rb',buffering=0) as stream:
                            stream.seek(case.get('base_words',0)*16);raw=stream.read(case['window_bytes_per_port'])
                        if identity(path)!=before or len(raw)!=case['window_bytes_per_port'] or hashlib.sha256(raw).hexdigest()!=window['sha256']:raise RuntimeError('Frozen weight window differs')
                        buffer[:len(raw)]=np.frombuffer(raw,np.uint8);buffer.sync_to_device();del raw
                    repetitions=range(-1,REPEATS) if args.mode=='Compare' else range(1)
                    for repeat in repetitions:
                        transact(packet,golden,int(case['config_u32'],16),label+':'+name+':'+str(repeat),variant)
                        result['transactions'][-1].update(case=name,block=index,repeat=repeat,measured=repeat>=0)
                    release_all()
            result['numerical_pass']=True
            if args.mode=='Compare':
                result['comparison']=derive_comparison(result['transactions'],result['overlay_loads'],spec['comparison_cases'])
                result['chain_performance_pass']=result['comparison']['all_cases_pass']
                if not result['chain_performance_pass']:raise RuntimeError('No separated balanced benefit for all frozen cases; stop first version')
''' +text[end:]
    text=text.replace("zero('A','stable-restored-build-id')", "zero('R','stable-restored-build-id')").replace("zero('A','failure-stable-restored-build-id')", "zero('R','failure-stable-restored-build-id')")
    text=text.replace("chain_identity='minimal-zero' if args.mode=='BuildID' else 'original-layer0:q'", "chain_identity=transaction.get('label','minimal-zero' if args.mode=='BuildID' else 'frozen-W2-W4')")
    text=replace_once(text,"from m439_completion_observer import wait_observed,ObservationFailure", "from m439_completion_observer import wait_observed,ObservationFailure\nfrom m439_comparison import derive_comparison")
    freeze('m439_board_probe.py',text)
    freeze('m439_comparison.py',(HERE/'m439_comparison.py').read_bytes())
    freeze('m439_completion_observer.py',(ROOT/'tmp/m357_board_support_01/m357_completion_observer.py').read_bytes())
    for name in ('m357_export_result.py','m357_gate_runner.sh','m357_transfer.py','m357_transfer_collection.py','m357_control.ps1'):
        newname=name.replace('m357','m439');s=(HERE/name).read_text(encoding='utf-8').replace('m357','m439').replace('M357','M439').replace('0x4D333537','0x4D343339')
        if name=='m357_transfer_collection.py':s=s.replace('build_id=\'0x4D333537\'', 'build_id=\'0x4D343339\'')
        freeze(newname,s)
    # Exact M438 packet, compact selected records, original complete wire reference.
    src=ROOT/'tmp/m438_weight_wait_03';data=src/'tv/cdatafile'
    w2packet=b''.join(x.to_bytes(16,'little') for x in values(data/(PREFIX+'autotvin_tx_V_data_V.dat')))
    w2weights=[]
    for i in range(4):
        raw=(data/(PREFIX+f'autotvin_w{i}.dat')).read_bytes()
        assert struct.unpack('>Q',raw[:8])[0]==360 and len(raw)==5776
        w2weights.append(b''.join(raw[j:j+16][::-1] for j in range(8,len(raw)-8,16)))
    chain=dict(groups=40,bits=2,descriptors=[dict(rows_per_shard=8,encoded_u64=hex(8<<32|2<<42))],output_bytes=4096)
    w2gold=(src/'golden.bin').read_bytes();assert full_reference(chain,w2weights,0,w2packet)==w2gold
    w2=fixture('w2',w2packet,w2gold,w2weights,0x10228,chain)
    d,gold,_=w4_fixture();w4=fixture('w4',d['packet'],gold,d['weights'],d['config'])
    # Two-descriptor W4 real-record CSim case. No invented duplicate records.
    import importlib.util,sys
    p=ROOT/'deployment/mage_vl4b/m120_text4b_runtime/m120_fixture.py'
    sp=importlib.util.spec_from_file_location('m439_board_original_fixture',p);module=importlib.util.module_from_spec(sp);sys.modules[sp.name]=module;sp.loader.exec_module(module)
    case=module.load_fixture(ROOT/'deployment/mage_vl4b/artifacts/m128_m120_real_record_csim_fixture.bin')[1]
    d2=module.build_case(case,2)
    chain2=dict(groups=40,bits=4,descriptors=[dict(rows_per_shard=8,encoded_u64=hex((j*680)|(8<<32)|(4<<42))) for j in range(2)],output_bytes=8192)
    gold2=full_reference(chain2,d2['weights'],0,d2['packet'])
    import numpy as np
    ref=np.frombuffer(d2['expected'],dtype='<u2').copy();mask=((ref&0x7c00)==0)&((ref&0x3ff)!=0);ref[mask]&=np.uint16(0x8000);assert gold2==ref.tobytes()
    w4chain=fixture('w4_chain',d2['packet'],gold2,d2['weights'],d2['config'],chain2)
    old=ROOT/'tmp/m357_board_fixture_02';spec=json.loads((old/'BOARD_CASES.json').read_bytes());q=spec['original_q_case']
    for n in ('build_packet.bin','build_golden.bin','q_packet.bin','q_golden.bin'):freeze(n,(old/n).read_bytes())
    qfull=dict(name='q_full',packet='q_packet.bin',golden='q_golden.bin',packet_sha256=sha(OUT/'q_packet.bin'),golden_sha256=sha(OUT/'q_golden.bin'),packet_bytes=(OUT/'q_packet.bin').stat().st_size,output_bytes=(OUT/'q_golden.bin').stat().st_size,config_u32=q['chain']['config_u32'],chain=q['chain'],base_words=q['base_words'],window_bytes_per_port=q['window_bytes_per_port'],windows=[dict(installed_path='external_assets/weights/language_fourport/'+r['file'],bytes=r['file_bytes'],sha256=r['sha256']) for r in q['windows']])
    outspec=dict(schema='m439-first-record-board-v1',build_id='0x4D343339',baseline_build_id='0x4D333537',restore_build_id='0x4D395832',stable_sources=spec['stable_sources'],build_config=spec['build_config'],cases=dict(w2=w2,w4=w4,w4_chain=w4chain,q_full=qfull),comparison_cases=['w2','w4','q_full'],comparison_order='ABBABAAB',comparison_repeats=8,primer_repeats=1,old_Q_fixture_sha256=sha(old/'BOARD_CASES.json'),M438_W2_exact=True,files=[])
    for f in sorted(OUT.glob('*.bin')):outspec['files'].append(dict(path=f.name,bytes=f.stat().st_size,sha256=sha(f)))
    freeze('BOARD_CASES.json',encoded(outspec))
    for f in OUT.glob('*.py'):ast.parse(f.read_text(encoding='utf-8'),feature_version=(3,10))
    r=dict(status='PREPARED_M439_BOARD_SUPPORT_NO_HARDWARE_PACKAGE',build_id='0x4D343339',baseline_build_id='0x4D333537',restore_build_id='0x4D395832',source_template_sha256=sha(original),files=[dict(path=f.relative_to(ROOT).as_posix(),bytes=f.stat().st_size,sha256=sha(f)) for f in sorted(OUT.iterdir())],extra_PS_slots=0,extra_CMA_banks=0,fixed64MiB_reserve=False,board=False,full_shell_gate_required=True,next_step='Support negative tests and strict saved collection; package only after full-shell PASS.')
    p=BASE/'runs/M439-board-support-preparation-01/RESULT.json';atomic(p,encoded(r),immutable=True)
    sync('latest_m439_board_support_preparation',dict(status=r['status'],result=p.relative_to(ROOT).as_posix(),sha256=sha(p),build_id=r['build_id'],board=False),'## M439 板端隔离支持准备（2026-10-07）\n\nSHA '+sha(p)+'；仅支持/同输入W2-W4夹具，原完整Q链与同Build M357对照，0上板/硬件包。每个正式block每shape固定1次primer+8次；原算法/输出全核对，原M9仅恢复。遵守用户取消固定64MiB拒绝，仍跟踪实际分配/活动DMA所有者；整壳PASS与控制负例后才能打包。')
    print(r['status'],sha(p))

if __name__=='__main__':main()
