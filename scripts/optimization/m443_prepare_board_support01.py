"""M443 host-only frozen fixtures and proposed configuration contract; zero hardware."""
import ast,copy,hashlib,json,struct
from pathlib import Path
import m351_workflow as w
from m441_host_io08 import atomic
OUT=w.ROOT/'tmp/m443_board_support_01'
RUN=w.BASE/'runs/M443-board-support-preparation-01'
BIT='555ae52842ae901c863152a5a02b2dd4583ed95691255d98889a25ae579c27ae'
def digest(b):return hashlib.sha256(b).hexdigest()
def row(p):return dict(path=p.relative_to(w.ROOT).as_posix(),bytes=p.stat().st_size,sha256=w.sha(p))
def proof(name,status):
    p=w.BASE/'runs'/name/'RESULT.json';d=json.loads(p.read_bytes());s=w.sha(p)
    assert d['status']==status and all(s in (w.ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'))
    return d,dict(path=p.relative_to(w.ROOT).as_posix(),sha256=s,status=status)
def main():
    assert not OUT.exists() and not RUN.exists(),'Existing preparation; inspect only'
    proofs=[]
    names=[
      ('M443-full-shell-04','PASS_M443_FULL_SHELL_ROUTED_TIMING04'),
      ('M443-pair-pipeline-core-OOC-closure-03','PASS_M443_SAME_CONSTRAINT_CORE_ROUTED_TIMING'),
      ('M443-full-numeric-csim-03','PASS_M443_FULL_REAL_WEIGHT_CHAIN_CSIM03'),
      ('M443-W2-W4-pair-pipeline-RTL-04','PASS_M441_W2_W4_SUPPLEMENTAL_SIMULATION_CLOSED19'),
      ('M443-full-numeric-preparation-03','PREPARED_M443_FULL_REAL_NUMERIC03'),
      ('M441-board-package-preparation-01','PREPARED_NEW_CIRCUIT_BOARD_PACKAGE_AFTER_ALL_GATES')]
    data={}
    for name,status in names:
        d,p=proof(name,status);proofs.append(p);data[name]=d
    shell=data[names[0][0]];assert all(shell['checks'].values()) and not shell['errors'] and shell['build_id']=='0x4D343433'
    for x in shell['artifacts']:assert w.sha(w.ROOT/x['path'])==x['sha256']
    oldprep=data[names[-1][0]];old=w.ROOT/oldprep['package_path']
    from m441_transfer import verify_directory
    verify_directory(old,oldprep['manifest_sha256'])
    original=json.loads((old/'BOARD_CASES.json').read_bytes())
    original_files={x['path']:x for x in original['files']};files={};cases={}
    simple=('build_packet.bin','build_golden.bin','w2_packet.bin','w2_golden.bin','w4_packet.bin','w4_golden.bin')+tuple('w'+str(b)+'_w'+str(i)+'.bin' for b in (2,4) for i in range(4))
    for name in simple:
        assert w.sha(old/name)==original_files[name]['sha256'];files[name]=(old/name).read_bytes()
    for name in ('w2','w4'):cases[name]=copy.deepcopy(original['cases'][name])
    for case in data['M443-full-numeric-preparation-03']['cases']:
        p=w.ROOT/case['fixture_path'];assert w.sha(p)==case['fixture_sha256']
        raw=p.read_bytes();assert raw[:8]==b'M441FUL1'
        config,dc,inp,outp,window=struct.unpack('<5I',raw[8:28]);packet=raw[28:28+inp];cursor=28+inp
        weights=[raw[cursor+i*window:cursor+(i+1)*window] for i in range(4)];golden=raw[cursor+4*window:]
        assert len(golden)==outp and len(packet)==inp and digest(packet)==case['packet_sha256'] and digest(golden)==case['golden_sha256']
        name={'q':'q_full','gate_up':'gate_up_full','mlp_down':'mlp_down_full'}[case['family']]
        saved=original['cases'][name]
        assert saved['packet_sha256']==digest(packet) and saved['golden_sha256']==digest(golden) and int(saved['config_u32'],16)==config and saved['chain']==case['chain']
        files[name+'_packet.bin']=packet;files[name+'_golden.bin']=golden;windows=[]
        for i,value in enumerate(weights):
            assert len(value)==window and digest(value)==case['sources'][i]['window_sha256']
            fn=name+'_w'+str(i)+'.bin';files[fn]=value;windows.append(dict(path=fn,bytes=len(value),sha256=digest(value)))
        cases[name]=dict(name=name,packet=name+'_packet.bin',golden=name+'_golden.bin',config_u32=hex(config),windows=windows,window_bytes_per_port=window,packet_bytes=inp,output_bytes=outp,chain=case['chain'],packet_sha256=digest(packet),golden_sha256=digest(golden),full_real_weight_fixture_sha256=case['fixture_sha256'],descriptor_count=dc)
    ledger=w.HERE/'m441_cma_ledger15.py';text=ledger.read_text(encoding='utf-8')
    validator=text[text.index('def validate(record):'):text.index('\nclass StagePolicy')]
    contract='"""Proposed exact-bit contract; no actual configuration proof or credit."""\nimport hashlib,re\nBITS={'+repr(BIT)+'}\nKERNEL=\'5.15.0-1027-xilinx-zynqmp\'\n\n'+validator
    ast.parse(contract,feature_version=(3,10));ns={};exec(compile(contract,'contract','exec'),ns)
    trace=''.join('python-123 [0] '+event+': name=reserved '+fields+' count=1904\n => zynqmp_fpga_ops_write\n => '+stack+'\n' for event,fields,stack in [('cma_alloc_start','','dma_alloc_attrs'),('cma_alloc_finish','pfn=0x1234','dma_alloc_attrs'),('cma_release','pfn=0x1234','dma_free_attrs')])
    fixture=dict(kernel=ns['KERNEL'],page_size=4096,pid=123,bit_sha256=BIT,bit_bytes=7797914,pages=1904,before={'reserved:alloc_pages_success':100,'reserved:alloc_pages_fail':0},after={'reserved:alloc_pages_success':2004,'reserved:alloc_pages_fail':0},trace=dict(trace_text=trace,trace_sha256=digest(trace.encode()),observer_errors=[],own_instance_removed=True,owned_instance_only=True,shared_root_configuration_changed=False,pid=123,elapsed_trace_s=1,stats={f'cpu{i}':'overrun: 0\ncommit overrun: 0\ndropped events: 0\n' for i in range(4)}))
    assert ns['validate'](fixture)=={'reserved:alloc_pages_success':1904};tests=['explicit-positive-fixture-only']
    def rejected(name,bad):
        try:ns['validate'](bad)
        except (AssertionError,KeyError,TypeError):tests.append(name)
        else:raise AssertionError(name)
    for name,key,value in [('unknown-bit','bit_sha256','0'*64),('old-M441-bit','bit_sha256','73350f615a5bc98d1d8aa2b5c69c4d6fd399aa1ef651f37411cbed21c0daed2e'),('bit-size','bit_bytes',1),('page-count','pages',1903),('kernel','kernel','unknown'),('page-size','page_size',8192),('same-PID','pid',124)]:
        bad=copy.deepcopy(fixture);bad[key]=value;rejected(name,bad)
    for name,key,value in [('extra-allocation','reserved:alloc_pages_success',2005),('failed-allocation','reserved:alloc_pages_fail',1),('counter-identity','other',0)]:
        bad=copy.deepcopy(fixture);bad['after'][key]=value;rejected(name,bad)
    for name,key,value in [('observer-error','observer_errors',['lost']),('not-removed','own_instance_removed',False),('not-owned','owned_instance_only',False),('shared-root-changed','shared_root_configuration_changed',True),('duration','elapsed_trace_s',31),('trace-SHA','trace_sha256','0'*64),('missing-CPU','stats',{})]:
        bad=copy.deepcopy(fixture);bad['trace'][key]=value;rejected(name,bad)
    bad=copy.deepcopy(fixture);bad['trace']['stats']['cpu0']='overrun: 1\ncommit overrun: 0\ndropped events: 0\n';rejected('lost-events',bad)
    for name,value in [('missing-release',trace[:trace.index('python-123 [0] cma_release')]),('PFN-mismatch',trace.replace('cma_release: name=reserved pfn=0x1234','cma_release: name=reserved pfn=0x5678')),('driver-stack',trace.replace('zynqmp_fpga_ops_write','unknown')),('allocator-stack',trace.replace('dma_alloc_attrs','unknown')),('release-stack',trace.replace('dma_free_attrs','unknown')),('foreign-PID',trace.replace('python-123','python-124')),('region',trace.replace('name=reserved','name=other')),('extra-event',trace+trace),('busy-retry',trace.replace('cma_alloc_finish','cma_alloc_busy_retry'))]:
        bad=copy.deepcopy(fixture);bad['trace'].update(trace_text=value,trace_sha256=digest(value.encode()));rejected(name,bad)
    files['m443_cma_contract01.py']=contract.encode()
    oldtrace=w.HERE/'m441_cma_trace15.py'
    tr=oldtrace.read_text(encoding='utf-8').replace("TRACE_NAME='m441_performance_cma15'","TRACE_NAME='m443_configuration01'").replace('M441_CONFIGURATION15','M443_CONFIGURATION01')
    ast.parse(tr,feature_version=(3,10));files['m443_cma_trace01.py']=tr.encode()
    bit=w.ROOT/'tmp/m443_shell_01/out/m443_t32.bit';assert w.sha(bit)==BIT;files['overlay/m120_m89x2_t32.bit']=bit.read_bytes()
    hwh=w.ROOT/shell['HWH']['candidate_path'];assert w.sha(hwh)==shell['HWH']['candidate_hwh_sha256'];files['overlay/m120_m89x2_t32.hwh']=hwh.read_bytes()
    assert w.sha(old/'overlay/m120_m89x2_t32.bit')=='73350f615a5bc98d1d8aa2b5c69c4d6fd399aa1ef651f37411cbed21c0daed2e'
    for suffix in ('bit','hwh'):files['baseline/overlay/m120_m89x2_t32.'+suffix]=(old/('overlay/m120_m89x2_t32.'+suffix)).read_bytes()
    OUT.mkdir(parents=True)
    for name,value in files.items():atomic(OUT/name,value,immutable=True)
    spec=dict(schema='m443-lower-gate-fixtures01',build_id='0x4D343433',baseline_build_id='0x4D343431',restore_build_id='0x4D395832',build_config=original['build_config'],cases=cases,gate_cases=dict(Descriptor=['w2','w4'],Chain=['q_full','gate_up_full','mlp_down_full']),stable_sources=original['stable_sources'],files=[dict(path=n,bytes=len(v),sha256=digest(v)) for n,v in files.items() if n.endswith('.bin')],M443_numeric_preparation_sha256=proofs[-2]['sha256'],original_M441_package_manifest_sha256=oldprep['manifest_sha256'])
    atomic(OUT/'BOARD_CASES.json',w.encoded(spec),immutable=True)
    application=dict(status='PROPOSED_M443_CONFIGURATION_APPLICATION_NOT_BOARD_VERIFIED',build_id='0x4D343433',bit_sha256=BIT,bit_bytes=7797914,pages=1904,page_size=4096,kernel=ns['KERNEL'],same_PID=True,same_PFN_release_required=True,exact_counter_delta={'reserved:alloc_pages_success':1904,'reserved:alloc_pages_fail':0},trace_limit_bytes=1<<20,trace_budget_s=30,unknown_or_failed_allocations_rejected=True,original_baseline_reset_allowed=False,seven_owner_policy_unchanged=True,PS_budget_unchanged=True,old_CMA15_whitelist_modified=False,actual_configuration_proof_required_before_credit=True,credits_granted=0,board=False)
    atomic(OUT/'CONFIGURATION_APPLICATION.json',w.encoded(application),immutable=True)
    result=dict(status='PREPARED_M443_FROZEN_FIXTURES_AND_CONFIGURATION_CONTRACT01',build_id='0x4D343433',prerequisites=proofs,files=[row(p) for p in sorted(OUT.rglob('*')) if p.is_file()],original_validator_source=row(ledger),original_trace_source=row(oldtrace),preparer=row(Path(__file__)),validator_fixture_checks=tests,fixture_test_not_board_evidence=True,hardware_package=False,board=False,configuration_application_accepted=False,configuration_credits_granted=0,performance=False,promotion=False,next_step='Prepare disabled lower-gate probe/control/collector and real safety negatives. Clean package after checks; COM3 bounded transfer then BuildID with actual new-bit samePID/PFN trace. No credits or later gate before raw PASS.')
    atomic(RUN/'RESULT.json',w.encoded(result),immutable=True);w.atomic=atomic;s=w.sha(RUN/'RESULT.json')
    w.sync('latest_m443_board_support_preparation01',dict(status=result['status'],result=(RUN/'RESULT.json').relative_to(w.ROOT).as_posix(),sha256=s,build_id=result['build_id'],board=False),'## M443板端夹具与独立配置合同01（2026-10-11）\n\nSHA '+s+'；新整壳04/CSim/六RTL/核心三同步后冻结新bit/HWH、精确M441对照及原完整Q/gate_up/down参考。仅支持材料，没有上传或上板包；新bit配置申请仅提案，'+str(len(tests))+'明确fixture检查通过但0实际配置证据/0credit。原CMA15白名单及累计基线/七owner/PS预算不改；下一步独立低级probe/control/collector及失败保留检查后干净打包，COM3先BuildID及samePID/PFN释放1904页实证。')
    print(result['status'],s,len(result['files']),len(tests),flush=True)
if __name__=='__main__':main()
