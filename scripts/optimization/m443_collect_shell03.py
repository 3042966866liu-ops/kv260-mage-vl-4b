"""M443 saved-byte full-shell collector. No AMD, UART or implementation entry."""
import argparse,copy,json,re,zipfile,xml.etree.ElementTree as E
import m351_workflow as w
from m441_host_io08 import atomic
w.atomic=atomic
ROOT,BASE,HERE=w.ROOT,w.BASE,w.HERE
SHELL=ROOT/'tmp/m443_shell_01'
OUT=SHELL/'out'
SUP=BASE/'runs/M443-shell-supervision-03'
PREP=BASE/'runs/M443-shell-collector-preparation-03/RESULT.json'
RESULT=BASE/'runs/M443-full-shell-03/RESULT.json'
OLD_HWH=ROOT/'deployment/mage_vl4b/m175_m120_fixed_text_candidate/overlay/m120_m89x2_t32.hwh'
OLD_TIMING=ROOT/'tmp/m120_m89x2_highddr/out/impl_timing_summary.rpt'
CHECK_NAMES=('no_clock','constant_clock','pulse_width_clock','unconstrained_internal_endpoints','no_input_delay','no_output_delay','multiple_clock','generated_clocks','loops','partial_input_delay','partial_output_delay','latch_loops')

def clocks(text):
    return re.findall(r'^(clk_pl_\d+)\s+\{[^}]+\}\s+([\d.]+)\s+([\d.]+)',text,re.M)

def timing(text):
    table=re.search(r'WNS\(ns\)[^\r\n]+\r?\n[^\r\n]+\r?\n([^\r\n]+)',text)
    vals=table[1].split() if table else []
    assert len(vals)==12,'Timing summary missing'
    v=[float(x) for x in vals]
    assert all(v[i]>=0 for i in (0,4,8)) and all(v[i]==0 for i in (1,2,5,6,9,10)), 'Setup/hold/pulse violation'
    assert v[3]>0 and v[7]>0 and v[11]>0,'Empty timing endpoints'
    assert 'All user specified timing constraints are met.' in text
    for label in CHECK_NAMES:
        n=re.findall(r'checking '+label+r' \((\d+)\)',text)
        assert n and all(int(x)==0 for x in n),'Unconstrained timing '+label
    assert clocks(text)==[('clk_pl_0','5.000','200.000'),('clk_pl_1','10.000','100.000')],'Clock constraint differs'
    return dict(WNS_ns=v[0],TNS_ns=v[1],setup_failing_endpoints=int(v[2]),setup_endpoints=int(v[3]),WHS_ns=v[4],THS_ns=v[5],hold_failing_endpoints=int(v[6]),hold_endpoints=int(v[7]),WPWS_ns=v[8],TPWS_ns=v[9],pulse_failing_endpoints=int(v[10]),pulse_endpoints=int(v[11]))

def hwh_proof(path,component):
    assert w.sha(OLD_HWH)=='9bd6100bcc274486ddd51133e4dc2247f35c030d49e53cc709438f2a74ee3520'
    a,b=[E.parse(p).getroot() for p in (OLD_HWH,path)]
    revision=next(e.text for e in E.parse(component).getroot().iter() if e.tag.endswith('}coreRevision'))
    def sig(e):
        return (e.tag,tuple(sorted(e.attrib.items())),(e.text or '').strip(),tuple(sorted(sig(x) for x in e)))
    def kernel(e):
        xs=[m for m in e.findall('./MODULES/MODULE') if m.get('INSTANCE')=='mage_m120_m89x2_0']
        assert len(xs)==1
        return xs[0]
    x,y=kernel(a),kernel(b)
    assert x.get('VLNV')=='tellme.local:hls:m89x_runtime_kernel:1.0'
    assert y.get('VLNV')=='xilinx.com:hls:m89x_runtime_kernel:1.0' and y.get('COREREVISION')==revision
    deltas=[]
    for key in ('COREREVISION','VLNV'):
        deltas.append(dict(field='kernel.'+key,original=x.get(key),candidate=y.get(key)));y.set(key,x.get(key))
    px=x.find('./PARAMETERS/PARAMETER[@NAME="II"]');py=y.find('./PARAMETERS/PARAMETER[@NAME="II"]')
    assert px is not None and py is not None
    deltas.append(dict(field='kernel.PARAMETER.II',original=px.get('VALUE'),candidate=py.get('VALUE')));py.set('VALUE',px.get('VALUE'))
    dx=x.find('DOCUMENTS');dy=y.find('DOCUMENTS')
    assert dx is not None and dy is not None
    deltas.append(dict(field='kernel.DOCUMENTS',original=E.tostring(dx).decode(),candidate=E.tostring(dy).decode()))
    y.remove(dy);y.append(copy.deepcopy(dx));b.set('TIMESTAMP',a.get('TIMESTAMP'))
    assert sig(a)==sig(b),'Unexpected HWH register/interface/PS/clock/address/topology difference'
    return dict(candidate_path=path.relative_to(ROOT).as_posix(),candidate_hwh_sha256=w.sha(path),stable_hwh_sha256=w.sha(OLD_HWH),component_sha256=w.sha(component),permitted_metadata_deltas=deltas,module_count=len(a.findall('./MODULES/MODULE')))

def preparation():
    from m443_shell_control03 import validate
    prerequisites=validate()
    assert not PREP.exists() and not RESULT.exists(),'Frozen collector already exists'
    baseline=OLD_TIMING.read_text(encoding='utf-8-sig')
    timing(baseline)
    rejected=0
    for bad in (baseline.replace('      0.147','     -0.147',1),baseline.replace('checking no_clock (0)','checking no_clock (1)'),baseline.replace('200.000','199.000')):
        try:timing(bad)
        except AssertionError:rejected+=1
        else:raise AssertionError('Invalid timing accepted')
    assert rejected==3
    paths=[HERE/'m443_collect_shell03.py',HERE/'m351_workflow.py',HERE/'m441_host_io08.py',OLD_HWH,OLD_TIMING,HERE/'m357_collect_shell.py',HERE/'m441_record_hwh07.py',HERE/'m441_collect_shell09.py',SUP/'PREPARATION.json',SUP/'START.json']
    for p in (SUP/'PREPARATION.json',):
        for row in json.loads(p.read_bytes())['files']+json.loads(p.read_bytes())['prerequisites']:
            assert w.sha(ROOT/row['path'])==row['sha256']
    r=dict(status='PREPARED_M443_SAVED_ONLY_SHELL_COLLECTOR03',build_id='0x4D343433',saved_only=True,board=False,promotion=False,implementation_rerun=False,
           template_policy='Original M357/M441 strict shell/HWH; no startup-error waiver. Any actual ERROR stops this level until independent saved-attempt review.',
           baseline_timing_parser_pass=True,negative_timing_rejections=rejected,prerequisites=prerequisites,
           files=[dict(path=p.relative_to(ROOT).as_posix(),sha256=w.sha(p)) for p in paths])
    atomic(PREP,w.encoded(r),immutable=True)
    w.sync('latest_m443_shell_collector_preparation03',dict(status=r['status'],result=PREP.relative_to(ROOT).as_posix(),sha256=w.sha(PREP),board=False),
           '## M443 saved-only shell collector03 (2026-10-11)\n\nSHA '+w.sha(PREP)+'; independent collector frozen while implementation continues unchanged. Original timing/clocks/resources/route/DRC/generated RTL/full HWH/separate-bit XSA checks; original ERROR denied, no old-attempt waiver. Actual baseline timing and three negative timing checks passed. No implementation rerun or board work.')
    print(r['status'],w.sha(PREP))

def collect():
    from m441_protocol_control import synchronized
    prep=synchronized(PREP,'PREPARED_M443_SAVED_ONLY_SHELL_COLLECTOR03','latest_m443_shell_collector_preparation03')
    for row in prep['files']+prep['prerequisites']:
        assert w.sha(ROOT/row['path'])==row['sha256'],'Frozen input changed'
    spec=json.loads((SUP/'PREPARATION.json').read_bytes())
    for row in spec['files']+spec['prerequisites']:assert w.sha(ROOT/row['path'])==row['sha256']
    exitpath=ROOT/'tmp/m443_shell_exit.json'
    assert exitpath.exists(),'Native implementation pending: inspect only'
    assert (SUP/'RESULT.json').exists(),'Supervisor original receipt pending: inspect only'
    assert not RESULT.exists(),'Immutable verdict exists: inspect only'
    sr=json.loads((SUP/'RESULT.json').read_bytes())
    assert not sr['process_retained'] and sr['original_host_rc'] is not None,'Active/unknown tool retained'
    synchronized(SUP/'RESULT.json',sr['status'],'latest_m443_shell_supervision_result03')
    for row in sr['evidence']:assert w.sha(ROOT/row['path'])==row['sha256']
    logs=sorted(SHELL.glob('*.runs/*/runme.log'))+[ROOT/'tmp/m443_shell_console.log']
    paths=set(logs+[exitpath,ROOT/'tmp/m443_shell_mapping.json',SUP/'RESULT.json',SUP/'START.json',SUP/'CONTROLLER.log',PREP,OLD_TIMING,OLD_HWH])
    paths.update(OUT.glob('*'))
    r=dict(status='FAIL_M443_FULL_SHELL_GATE03',build_id='0x4D343433',board=False,performance=False,promotion=False,errors=[],checks={},resources={},artifacts=[],prerequisites=prep['prerequisites'],preparation_sha256=w.sha(PREP),supervision_sha256=w.sha(SUP/'RESULT.json'),original_host_rc=sr['original_host_rc'])
    def check(name,ok):
        r['checks'][name]=bool(ok);assert ok,name
    try:
        native=json.loads(exitpath.read_bytes());r['original_vivado_rc']=native['vivado_rc']
        check('original_rc',sr['status']=='COMPLETED_M443_SHELL_TOOL03_AWAITING_STRICT_COLLECT' and sr['original_host_rc']==0 and native['vivado_rc']==0)
        check('mapping_restored',json.loads((ROOT/'tmp/m443_shell_mapping.json').read_bytes())['removed'] is True)
        from m443_shell_control03 import validate
        validate()
        p=BASE/'runs/M443-shell-preparation-01/RESULT.json';j=json.loads(p.read_bytes());manifest=ROOT/j['manifest_path'];staged=json.loads(manifest.read_bytes())
        check('manifest_exact',w.sha(manifest)==j['manifest_sha256'])
        for row in staged['files']:assert w.sha(manifest.parent/row['path'])==row['sha256']
        generated=list(SHELL.rglob('m89x_runtime_kernel.v'));check('unique_generated_top',len(generated)==1)
        rtl=[]
        for source in sorted((manifest.parent/'ip/hdl/verilog').iterdir()):
            if not source.is_file():continue
            target=generated[0].parent/source.name
            assert target.is_file() and w.sha(target)==w.sha(source),'Generated RTL differs: '+source.name
            rtl.append(dict(path=target.relative_to(ROOT).as_posix(),sha256=w.sha(target)))
        check('all_computational_RTL_exact',len(rtl)==83 and j['same_computational_rtl']==77);r['actual_generated_ip_rtl']=rtl
        text=logs[-1].read_text(encoding='utf-8-sig')
        check('native_completion_marker','M443_FULL_SHELL_ROUTED timing_pass=1 build=0x4D343433' in text)
        check('actual_run_logs',any(p.parent.name=='impl_1' for p in logs) and any(p.parent.name=='synth_1' for p in logs))
        for p in logs:
            t=p.read_text(encoding='utf-8-sig')
            assert not re.search(r'^ERROR:|^CRITICAL WARNING:',t,re.M),'Original actual error/critical warning: '+p.relative_to(ROOT).as_posix()
        check('no_original_tool_errors',True)
        values=(OUT/'shell_route_receipt.txt').read_text(encoding='utf-8-sig')
        r['wns_ns']=float(re.search(r'WNS_NS=([^\s]+)',values)[1]);r['whs_ns']=float(re.search(r'WHS_NS=([^\s]+)',values)[1]);r['unrouted_nets']=int(re.search(r'UNROUTED_NETS=(\d+)',values)[1])
        check('route_receipt',r['wns_ns']>=0 and r['whs_ns']>=0 and r['unrouted_nets']==0)
        route=(OUT/'route_status.rpt').read_text(encoding='utf-8-sig')
        check('actual_route_clean',bool(re.search(r'# of nets with routing errors\.+\s*:\s*0\b',route)))
        t=(OUT/'impl_timing.rpt').read_text(encoding='utf-8-sig');r['timing_summary']=timing(t)
        check('setup_hold_pulse',True);check('same_clocks',clocks(t)==clocks(OLD_TIMING.read_text(encoding='utf-8-sig')));r['clock_constraints']=clocks(t)
        util=(OUT/'impl_utilization.rpt').read_text(encoding='utf-8-sig')
        for label in ('CLB LUTs','CLB Registers','Block RAM Tile','URAM','DSPs','Register as Latch'):
            m=re.search(r'^\|\s*'+re.escape(label)+r'\*?\s*\|\s*([\d.]+)\s*\|\s*\d+\s*\|\s*\d+\s*\|\s*([\d.]+)',util,re.M)
            assert m,label
            used,available=map(float,m.groups());assert used<=available,label
            r['resources'][label]=dict(used=used,available=available)
        check('resources_fit_no_latch',r['resources']['Register as Latch']['used']==0)
        drc=(OUT/'impl_drc.rpt').read_text(encoding='utf-8-sig')
        check('DRC_no_error_critical',bool(drc.strip()) and not re.search(r'\|\s*(?:Error|Critical Warning)\s*\|',drc))
        hwh=SHELL/'mage_m120_m89x2_highddr.gen/sources_1/bd/qwen25_mixed_gs/hw_handoff/qwen25_mixed_gs.hwh'
        r['HWH']=hwh_proof(hwh,manifest.parent/'ip/component.xml');paths.add(hwh);check('whole_HWH_ABI_topology',True)
        for name in ('m443_t32.bit','m443_t32.xsa','candidate_routed.dcp'):
            p=OUT/name;assert p.is_file() and p.stat().st_size>0
            r['artifacts'].append(dict(path=p.relative_to(ROOT).as_posix(),bytes=p.stat().st_size,sha256=w.sha(p)))
        with zipfile.ZipFile(OUT/'m443_t32.xsa') as z:
            check('separate_bit_XSA',not any(n.endswith('.bit') for n in z.namelist()))
            check('full_XSA_HWH_exact',z.read('qwen25_mixed_gs.hwh')==hwh.read_bytes())
        r['status']='PASS_M443_FULL_SHELL_ROUTED_TIMING03'
    except Exception as exc:r['errors'].append(type(exc).__name__+': '+str(exc))
    r['evidence']=[dict(path=p.relative_to(ROOT).as_posix(),sha256=w.sha(p)) for p in sorted(paths) if p.is_file()]
    r['limitation']='Full board shell implementation only. No new board correctness, request speed or promotion.'
    atomic(RESULT,w.encoded(r),immutable=True)
    atomic(RESULT.parent/'REPORT.md',('# M443 full shell saved-byte verdict\n\n'+r['status']+'\n\n'+json.dumps({k:r[k] for k in ('checks','errors','resources','limitation')},ensure_ascii=False,indent=2)+'\n').encode('utf-8'),immutable=True)
    w.sync('latest_m443_full_shell03',dict(status=r['status'],result=RESULT.relative_to(ROOT).as_posix(),sha256=w.sha(RESULT),build_id=r['build_id'],board=False),
           '## M443 full-shell original-byte closure03 (2026-10-11)\n\nSHA '+w.sha(RESULT)+'; '+r['status']+'. Original rc, strict 200/100MHz setup/hold/pulse, route/resources/DRC/log/generated RTL/full HWH/separate-bit XSA checked. Only this level; no board result or measured benefit. Original errors retained; no implementation rerun.')
    print(r['status'],w.sha(RESULT),json.dumps(r['errors']))
    return 0 if r['status'].startswith('PASS_') else 1

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('mode',choices=['Prepare','Collect']);a=ap.parse_args()
    if a.mode=='Prepare':preparation()
    else:raise SystemExit(collect())
