"""Reuse frozen fixtures and checked control; add real full W4 chains only.
No Overlay, DMA, or board access. This support is not a hardware package.
"""
import ast,json,struct
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync

OUT=ROOT/'tmp/m441_board_support_07'

def main():
    assert not OUT.exists(),'Existing support; inspect only'
    old=BASE/'runs/M439-board-support-preparation-01/RESULT.json';prior=json.loads(old.read_bytes())
    assert prior['status']=='PREPARED_M439_BOARD_SUPPORT_NO_HARDWARE_PACKAGE'
    for row in prior['files']:assert sha(ROOT/row['path'])==row['sha256']
    numeric=BASE/'runs/M441-full-numeric-csim-01/RESULT.json'
    assert json.loads(numeric.read_bytes())['status']=='PASS_M441_FULL_REAL_WEIGHT_CHAIN_CSIM'
    for n in ('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'):
        assert sha(numeric) in (ROOT/n).read_text(encoding='utf-8-sig')
    fixture_prep=BASE/'runs/M441-full-numeric-preparation-01/RESULT.json'
    fixture_spec=json.loads(fixture_prep.read_bytes())
    oldout=ROOT/'tmp/m439_board_support_01';spec=json.loads((oldout/'BOARD_CASES.json').read_bytes())
    files={}
    for row in spec['files']:
        p=oldout/row['path'];assert sha(p)==row['sha256'];files[p.name]=p.read_bytes()
    cases=spec['cases'].copy()
    for family in ('gate_up','mlp_down'):
        row=next(r for r in fixture_spec['cases'] if r['family']==family)
        path=ROOT/row['fixture_path'];assert sha(path)==row['fixture_sha256']
        raw=path.read_bytes();assert raw[:8]==b'M441FUL1'
        config,dc,inp,outp,window=struct.unpack('<5I',raw[8:28]);cursor=28
        packet=raw[cursor:cursor+inp];cursor+=inp
        weights=[raw[cursor+i*window:cursor+(i+1)*window] for i in range(4)];cursor+=4*window
        golden=raw[cursor:];assert len(golden)==outp and len(packet)==inp and all(len(w)==window for w in weights)
        import hashlib
        assert hashlib.sha256(packet).hexdigest()==row['packet_sha256'] and hashlib.sha256(golden).hexdigest()==row['golden_sha256']
        name=family+'_full';files[name+'_packet.bin']=packet;files[name+'_golden.bin']=golden
        windows=[]
        for i,w in enumerate(weights):
            fn=name+'_w'+str(i)+'.bin';files[fn]=w
            windows.append(dict(path=fn,bytes=len(w),sha256=hashlib.sha256(w).hexdigest()))
        cases[name]=dict(name=name,packet=name+'_packet.bin',golden=name+'_golden.bin',config_u32=hex(config),
          windows=windows,window_bytes_per_port=window,packet_bytes=inp,output_bytes=outp,chain=row['chain'],
          packet_sha256=row['packet_sha256'],golden_sha256=row['golden_sha256'],full_real_weight_fixture_sha256=row['fixture_sha256'],descriptor_count=dc)
    text=(HERE/'m439_board_probe.py').read_text(encoding='utf-8-sig')
    text=text.replace('m439','m441').replace('M439','M441').replace('0x4d343339','0x4d343431').replace('0x4D343339','0x4D343431')
    oldcases="cases=[spec['cases']['w2']] if args.mode=='Descriptor' else [spec['cases']['q_full'],spec['cases']['w4_chain']]"
    assert text.count(oldcases)==1
    text=text.replace(oldcases,"cases=[spec['cases'][n] for n in (['w2','w4'] if args.mode=='Descriptor' else ['q_full','gate_up_full','mlp_down_full'])]")
    files['m441_board_probe.py']=text.encode()
    for name in ('m439_comparison.py','m439_completion_observer.py','m439_export_result.py','m439_gate_runner.sh','m439_transfer.py','m439_transfer_collection.py'):
        text=(HERE/name).read_text(encoding='utf-8-sig').replace('m439','m441').replace('M439','M441').replace('0x4D343339','0x4D343431')
        files[name.replace('m439','m441')]=text.encode()
    # Keep the repaired manifest-first bounded transfer and its original rc checks.
    text=(HERE/'m439_control02.ps1').read_text(encoding='utf-8-sig').replace('m439','m441').replace('M439','M441')
    files['m441_control07.ps1']=text.encode()
    spec.update(schema='m441-full-W4-board-v1',build_id='0x4D343431',cases=cases,
      comparison_cases=['gate_up_full','mlp_down_full'],comparison_order='ABBABAAB',comparison_repeats=8,primer_repeats=1,
      gate_cases=dict(Descriptor=['w2','w4'],Chain=['q_full','gate_up_full','mlp_down_full']),
      full_numeric_preparation_sha256=sha(fixture_prep),full_numeric_sha256=sha(numeric),files=[])
    OUT.mkdir()
    for name,raw in files.items():
        atomic(OUT/name,raw,immutable=True)
        if name.endswith('.py'):ast.parse(raw.decode('utf-8'),feature_version=(3,10))
        if name.endswith('.bin'):spec['files'].append(dict(path=name,bytes=len(raw),sha256=sha(OUT/name)))
    atomic(OUT/'BOARD_CASES.json',encoded(spec),immutable=True)
    # Adapt strict saved-byte collection to the frozen new shape counts/order.
    text=(HERE/'m439_board_collection.py').read_text(encoding='utf-8-sig').replace('m439','m441').replace('M439','M441').replace('0x4d343339','0x4d343431').replace('0x4D343339','0x4D343431')
    text=text.replace('tmp/m441_board_support_01','tmp/m441_board_support_07')
    replacements={
      'dict(BuildID=2,Descriptor=2,Chain=3,Compare=217)':'dict(BuildID=2,Descriptor=3,Chain=4,Compare=145)',
      'dict(BuildID=2,Descriptor=2,Chain=3,Compare=25)':'dict(BuildID=2,Descriptor=3,Chain=4,Compare=17)',
      "dict(BuildID=[None],Descriptor=['w2'],Chain=['q_full','w4_chain'])":"dict(BuildID=[None],Descriptor=['w2','w4'],Chain=['q_full','gate_up_full','mlp_down_full'])"}
    for a,b in replacements.items():assert text.count(a)==1;text=text.replace(a,b)
    ast.parse(text,feature_version=(3,10));atomic(OUT/'m441_board_collection.py',text.encode(),immutable=True)
    r=dict(status='PREPARED_M441_FULL_W4_BOARD_SUPPORT07',build_id='0x4D343431',baseline_build_id='0x4D333537',restore_build_id='0x4D395832',
      full_numeric_sha256=sha(numeric),fixture_preparation_sha256=sha(fixture_prep),original_support_sha256=sha(old),
      files=[dict(path=p.relative_to(ROOT).as_posix(),bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(OUT.iterdir())],
      extra_PS_slots=0,extra_CMA_banks=0,fixed64MiB_reserve=False,board=False,hardware_package=False,
      comparison=dict(cases=spec['comparison_cases'],blocks='ABBABAAB',primer_per_shape_per_block=1,measured_per_shape_per_block=8,
        boundary='S2MM submit through latched AP_DONE and both DMA idle; exact staging and hash outside timing',
        pass_rule='Both full W4 chains: both balanced groups positive and all candidate block medians below all original block medians; observed clocks equal; no repeat to obtain PASS'),
      next_step='Run offline actual prepared control and collector negatives. Package requires current M441 full shell PASS; then COM3 Build -> descriptor -> chain -> fixed comparison.')
    ev=BASE/'runs/M441-board-support-preparation-07/RESULT.json';atomic(ev,encoded(r),immutable=True)
    sync('latest_m441_board_support_preparation07',dict(status=r['status'],result=ev.relative_to(ROOT).as_posix(),sha256=sha(ev),build_id=r['build_id'],board=False),
      f'## M441 真实完整W4板端支持准备07（2026-10-09）\n\nSHA {sha(ev)}；复用已完整CSim及Zero闭合的原非零T32真实gate_up/down输入、权重窗口和全部golden，不从小W4外推。Descriptor覆盖W2/W4，Chain覆盖Q与两条完整W4；仅两条W4固定ABBA/BAAB各block一primer加8正式事务，不丢样本/加测求PASS。原M357对照，原M9恢复；0新增PS槽/CMA bank，原生产入口不改。仅支持未离线检查/打包/上传，整壳PASS才解锁包。')
    print(r['status'],sha(ev),flush=True)

if __name__=='__main__':main()
