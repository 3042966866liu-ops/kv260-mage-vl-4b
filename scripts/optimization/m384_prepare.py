"""Expand only single descriptor to its frozen complete two-descriptor Q chain."""
import ast,json,shutil,sys,symtable
from m351_workflow import ROOT,HERE,BASE,sha,atomic,encoded,sync
from m377_prepare import once
OLD=BASE/'candidates/M383-ps-descriptor-01'
PKG=BASE/'candidates/M384-ps-chain-01'
DESCRIPTOR_RAW='6d1d646117c8945847811fb70cb7e81b3a7792b3ed63ac53f7aeeb91e0973d1a'
def main():
    if PKG.exists():raise RuntimeError('Immutable candidate exists')
    board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_text(encoding='utf-8'));prior=board['latest_m383_ps_descriptor_closure'];assert sha(ROOT/prior['result'])==prior['sha256']
    assert json.loads((ROOT/prior['result']).read_text(encoding='utf-8'))['status']=='PASS_SINGLE_DESCRIPTOR_PS_BINDING_ONLY'
    assert all(prior['sha256'] in (ROOT/n).read_text(encoding='utf-8') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    m=json.loads((OLD/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))
    for r in m['files']:assert sha(OLD/r['path'])==r['sha256']
    PKG.mkdir(parents=True)
    excluded={'m383_assemble.py','m383_ps_descriptor_gate.py','m383_export_result.py','run_m383_ps_descriptor.sh','SHA256SUMS'}
    for r in m['files']:
        if r['path'] not in excluded:shutil.copyfile(OLD/r['path'],PKG/r['path'])
    s=(OLD/'m383_ps_descriptor_gate.py').read_text(encoding='utf-8').replace('M383','M384').replace('m383_export_result','m384_export_result').replace('/home/ubuntu/m383_ps_descriptor_01','/home/ubuntu/m384_ps_chain_01').replace('--enable-ps-descriptor','--enable-ps-chain').replace('args.enable_ps_descriptor','args.enable_ps_chain').replace('sealed-DMA-PS-single-descriptor-numerical','sealed-DMA-PS-single-chain-numerical')
    s=once(s,"        result['slot_prerequisite_sha256']=sha256(slot_path)","        result['slot_prerequisite_sha256']=sha256(slot_path)\n        descriptor_path=Path('/home/ubuntu/m383_ps_descriptor_01/B1/load-memory.json')\n        descriptor=json.loads(descriptor_path.read_text(encoding='utf-8'))\n        if sha256(descriptor_path)!='"+DESCRIPTOR_RAW+"' or descriptor['status']!='PASS_M383_PS_DESCRIPTOR_NUMERICAL' or not descriptor['session_weakref_dead']:raise RuntimeError('Actual prior descriptor PS binding differs')\n        result['descriptor_prerequisite_sha256']=sha256(descriptor_path)")
    s=once(s,"chain=spec['single_descriptor_chain'];layout=runtime.language_layout","chain=spec['original_q_case']['chain'];layout=runtime.language_layout")
    s=s.replace("CANDIDATE/'descriptor_packet.bin'","CANDIDATE/'q_packet.bin'").replace("CANDIDATE/'descriptor_golden.bin'","CANDIDATE/'q_golden.bin'")
    s=once(s,"chain['descriptor_count']!=1 or words!=0 or size!=368640 or len(packet)!=102416 or len(golden)!=262144","chain['descriptor_count']!=2 or words!=0 or size!=737280 or len(packet)!=102432 or len(golden)!=524288")
    s=s.replace('descriptor_count=1','descriptor_count=2').replace('single-descriptor','single-chain').replace('descriptor geometry','chain geometry').replace('Descriptor completion','Chain completion').replace('Full descriptor output','Full chain output').replace('PASS_M384_PS_DESCRIPTOR_NUMERICAL','PASS_M384_PS_CHAIN_NUMERICAL').replace("'baseline_descriptor'","'baseline_chain'").replace("'candidate_descriptor'","'candidate_chain'")
    s=s.replace('original baseline and isolated one-slot PS staging single descriptor','original baseline and isolated one-slot PS staging complete Q chain').replace('Single-descriptor numerical/lifecycle adjudication and three-record synchronization; only then prepare representative chain; stop expansion on capacity/lifecycle issue','Complete-Q-chain numerical/lifecycle adjudication and three-record synchronization; only then prepare isolated layer0 five-family plan; stop expansion on capacity/lifecycle issue')
    atomic(PKG/'m384_ps_chain_gate.py',s.encode('utf-8'))
    a=(OLD/'m383_assemble.py').read_text(encoding='utf-8').replace('M383','M384').replace('/home/ubuntu/m382_sealed_ps_slot_candidate_01','/home/ubuntu/m383_ps_descriptor_candidate_01').replace(sha(BASE/'candidates/M382-sealed-ps-slot-01/PACKAGE_MANIFEST.json'),sha(OLD/'PACKAGE_MANIFEST.json'));atomic(PKG/'m384_assemble.py',a.encode('utf-8'))
    a=(OLD/'m383_export_result.py').read_text(encoding='utf-8').replace('M383','M384').replace('/home/ubuntu/m383_ps_descriptor_01','/home/ubuntu/m384_ps_chain_01').replace('sealed-DMA-PS-single-descriptor-numerical','sealed-DMA-PS-single-chain-numerical');atomic(PKG/'m384_export_result.py',a.encode('utf-8'))
    a=(OLD/'run_m383_ps_descriptor.sh').read_text(encoding='utf-8').replace('M383','M384').replace('m383_export_result','m384_export_result').replace('m383_ps_descriptor_gate','m384_ps_chain_gate').replace('/home/ubuntu/m383_ps_descriptor_01','/home/ubuntu/m384_ps_chain_01').replace('ENABLE_PS_DESCRIPTOR','ENABLE_PS_CHAIN').replace('--enable-ps-descriptor','--enable-ps-chain');atomic(PKG/'run_m384_ps_chain.sh',a.encode('utf-8'))
    closure=json.loads((PKG/'SOURCE_CLOSURE.json').read_text(encoding='utf-8'));trees={p.stem:ast.parse(p.read_text(encoding='utf-8'),feature_version=(3,10)) for p in PKG.glob('*.py')};allowed=set(sys.stdlib_module_names)|set(closure['modules'])|{'numpy','pynq','tokenizers'};missing=[]
    for mod,tree in trees.items():
        for node in ast.walk(tree):
            names=[n.name.split('.')[0] for n in node.names] if isinstance(node,ast.Import) else ([(node.module or '').split('.')[0]] if isinstance(node,ast.ImportFrom) else [])
            missing.extend((mod,n) for n in names if n and n not in trees and n not in allowed)
    assert not missing
    symbols=next(t for t in symtable.symtable(s,'gate','exec').get_children() if t.get_name()=='main');assert next(t for t in symbols.get_children() if t.get_name()=='tracked_allocate').lookup('SHAPES').is_global()
    for n in ('m383_sealed_ps_read.py','ps_read_ahead.py','m382_ps_slot.py','m365_stage_policy.py'):assert sha(PKG/n)==sha(OLD/n)
    for row in json.loads((PKG/'HARDWARE_CLOSURE.json').read_text(encoding='utf-8'))['prerequisites']:assert sha(ROOT/row['path'])==row['sha256']
    rows=[dict(path=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(PKG.iterdir())];atomic(PKG/'SHA256SUMS',''.join(r['sha256']+'  '+r['path']+'\n' for r in rows).encode('ascii'));rows.append(dict(path='SHA256SUMS',bytes=(PKG/'SHA256SUMS').stat().st_size,sha256=sha(PKG/'SHA256SUMS')))
    atomic(PKG/'PACKAGE_MANIFEST.json',encoded(dict(schema='m384-sealed-PS-chain-v1',files=rows,file_count=len(rows),total_bytes=sum(r['bytes'] for r in rows))))
    out=BASE/'runs/M384-ps-chain-preparation-01';r=dict(status='PASS_OFFLINE_PS_COMPLETE_Q_CHAIN_PREPARATION',descriptor_closure_sha256=prior['sha256'],descriptor_raw_sha256=DESCRIPTOR_RAW,manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),package_files=len(rows),package_bytes=sum(r['bytes'] for r in rows),adapter_source_unchanged=True,PS_source_unchanged=True,recursive_missing=missing,python310_syntax=True,production64MiB_unchanged=True,planned_transactions=3,model_forward_calls=0,board_run=False,performance_pass=False)
    atomic(out/'RESULT.json',encoded(r),immutable=True);d=sha(out/'RESULT.json');sync('latest_m384_ps_chain_preparation',dict(status=r['status'],result=(out/'RESULT.json').relative_to(ROOT).as_posix(),sha256=d,manifest_sha256=r['manifest_sha256']),f'## M384 PS暂存完整Q chain准备（2026-10-03）\n\nM383 descriptor原SHA {DESCRIPTOR_RAW}及闭合已同步；仅扩成冻结原双descriptor Q，packet102,432B/output524,288B、每port737,280B；原暂存/PS暂存两次完整wire FTZ及权重对照，0forward/新增DMA。准入/PS源/生命周期同SHA不重复组件检查，依赖missing0/3.10/作用域通过。准备SHA {d}；下一步控制/回收支持后一次本级，未新增性能。')
    print('M384_PREPARED',d,r['manifest_sha256'])
if __name__=='__main__':main()
