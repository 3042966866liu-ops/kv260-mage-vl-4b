"""One explicit COM3 gate; serialized ownership, original bytes, no retries."""
import argparse,base64,concurrent.futures,hashlib,json,re,subprocess,time
from pathlib import Path
from m351_workflow import BASE,sha,atomic,encoded
from m455456_workflow02 import synchronized
import jf_collect_board05 as c
from jf_saved_wire01 import decode
import jf_saved_fetch01 as saved
ROOT=Path(__file__).resolve().parents[2];R=BASE/'runs';LOG=ROOT/'tmp/jf_board02';OUT=R/'JF-gate-control-preparation-04'
UART=ROOT/'scripts/m455_original94_uart03.ps1';REMOTE='/dev/shm/jf_width_board_02';EVIDENCE='/home/ubuntu/jf_width_evidence_01'
PWSH='C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe'
def read(p):return json.loads(p.read_bytes())
def save(p,v):atomic(p,encoded(v),immutable=True)
def uart(command,label,seconds=30,retained=''):
    LOG.mkdir(parents=True,exist_ok=True);path=LOG/(label+'.log');host=LOG/(label+'_host.log')
    if path.exists() or host.exists():raise RuntimeError('Original COM3 attempt exists; observe/collect only')
    args=[PWSH,'-NoProfile','-ExecutionPolicy','Bypass','-File',str(UART),'-Command',command,'-LogPath',path.relative_to(ROOT).as_posix(),'-TimeoutSeconds',str(seconds),'-MarkerPrefix','__JF_'+label.upper()+'_RC_']
    if retained:args+=['-RetainedMarker',retained]
    with host.open('xb') as f:rc=subprocess.run(args,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT).returncode
    return rc,path
def board_available():
    latest=R/'J1-prefill-comparison-board-01'
    audit=read(latest/'EXIT_AUDIT.json');raw=read(latest/'BOARD_RESULT.json')
    assert audit['actual_host_rc']==0 and audit['raw_sha256']==sha(latest/'BOARD_RESULT.json')
    assert raw['safe_buffers_released'] and not raw['unsafe_buffers_retained'] and raw['original_clocks_restored'] and raw['stable_overlay_reloaded']
    current=R/'J1-prefill-numerical-board-01'
    if (current/'HOST_START.json').exists():
        verdict=current/'VERDICT.json';raw=current/'BOARD_RESULT.json'
        if not verdict.exists() or not raw.exists():raise RuntimeError('J1 prefill active/unknown: no COM3 or network command')
        v,z=read(verdict),read(raw)
        assert v['status']=='PASS_J1_CASE0_PREFILL_NUMERICAL_ALL_SAVED_EVIDENCE' and v['prefill_numerical_pass'] and v['raw_sha256']==sha(raw)
        assert v['actual_gate_process_rc']==v['actual_export_rc']==v['actual_UART_command_rc']==0
        assert z['safe_buffers_released'] is True and z['unsafe_buffers_retained'] is False and z['original_clocks_restored'] is True
        assert z['stable_overlay_reloaded'] is True and z['stable_restore']['status']=='PASS_STABLE_RESTORE' and z['stable_restore']['unsafe_retained'] is False
        for n in ('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'):assert sha(verdict) in (ROOT/n).read_text(encoding='utf-8-sig')
    old=R/'J1-board-timing-01/BOARD_RESULT.json';z=read(old)
    assert z['gate_return_code']==0 and z['safe_buffers_released'] and z['stable_restored'] and z['original_clocks_restored'] and not z['unsafe_dma_buffers_retained']
    assert read(old.parent/'COLLECTION.json')['raw_sha256']==sha(old)
    # All prior known board owners must have strictly closed; never query a live gate.
    start=R/'M482-parser-full-board-01/HOST_START.json'
    if start.exists():
        raw=R/'M482-parser-full-board-01/BOARD_RESULT.json';col=raw.parent/'COLLECTION.json'
        if not raw.exists() or not col.exists():raise RuntimeError('M482 active/unknown; no COM3 command allowed')
        r=read(raw);a=read(col)
        assert a['strict_validation'] and a['raw_sha256']==sha(raw) and a['gate_return_code']==0
        assert r['unsafe_buffers_retained'] is False and r['safe_buffers_released'] and r['stable_restore_pass'] and r['original_clocks_restored']
        for name in ('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'):assert sha(raw) in (ROOT/name).read_text(encoding='utf-8-sig')
    for rel,keys in [
        ('M486-board-timing-01/BOARD_RESULT.json',('safe_buffers_released','stable_restored','original_clocks_restored')),
        ('M487-layout-A53-board-02/BOARD_RESULT.json',())]:
        path=R/rel;row=read(path)
        if rel.startswith('M486'):
            assert row['gate_return_code']==0 and row['unsafe_dma_buffers_retained'] is False and all(row[k] is True for k in keys)
            assert read(path.parent/'COLLECTION.json')['raw_sha256']==sha(path)
        else:
            # CPU-only run must have naturally ended in its saved producer contract.
            assert sha(path)=='51a47919704cd672e9922bff27aeb5a450ae7d8f4bb8c047fbca7bba39e2dba1'
    latest=R/'M489-board-timing-01/BOARD_RESULT.json';old=read(latest)
    assert old['gate_return_code']==0 and old['safe_buffers_released'] and old['stable_restored'] and old['original_clocks_restored'] and not old['unsafe_dma_buffers_retained']
    assert read(latest.parent/'COLLECTION.json')['raw_sha256']==sha(latest)
    last=R/'M492-board-timing-01/BOARD_RESULT.json';z=read(last)
    assert z['gate_return_code']==0 and z['safe_buffers_released'] and z['stable_restored'] and z['original_clocks_restored'] and not z['unsafe_dma_buffers_retained']
    assert read(last.parent/'COLLECTION.json')['raw_sha256']==sha(last)
    keys=read(R/'M494-own-numerical-plan-01/RESULT.json')['keys']
    for key in keys:
        tag='M494_'+key;low=tag.lower();folder=ROOT/'tmp'/(low+'_board')
        for level in ('BuildID','Descriptor','Chain','Layer','Timing'):
            if (folder/(level+'_Run01.log')).exists():
                raw=R/(tag+'-board-'+level.lower()+'-01')/'BOARD_RESULT.json';audit=raw.parent/'COLLECTION.json'
                assert raw.exists() and audit.exists(),'Prior M494 gate active/unknown: no COM3 commands'
                a,b=read(raw),read(audit)
                assert a['gate_return_code']==0 and b['raw_sha256']==sha(raw) and a['safe_buffers_released'] and a['stable_restored'] and a['original_clocks_restored'] and not a['unsafe_dma_buffers_retained']


def prepare():
    assert not OUT.exists()
    tests=[R/'JF-joint-entry-component-01/RESULT.json',R/'JF-joint-collector-component-03/RESULT.json',R/'JF-sealed-collector-binding-component-01/RESULT.json',R/'JF-new-weights-csim-01/RESULT.json']
    assert all(read(t)['status'].startswith('PASS_') for t in tests)
    assert read(tests[2])['collector_sha256']==sha(Path(c.__file__))
    paths=[Path(__file__),Path(c.__file__),Path(saved.__file__),ROOT/'scripts/optimization/jf_saved_wire01.py',ROOT/'scripts/optimization/jf_fetch_pc_network02.ps1',UART]
    p=dict(status='FROZEN_JF_ONE_GATE_CONTROL_NO_BOARD',frozen={p.relative_to(ROOT).as_posix():sha(p) for p in paths},tests={p.relative_to(ROOT).as_posix():sha(p) for p in tests},manifest_sha256=c.MANIFEST,board=False,explicit_Run_required=True,prior_J1_prefill_must_be_strictly_closed=True)
    save(OUT/'RESULT.json',p)
    synchronized('latest_JF_gate_control01',dict(status=p['status'],result=(OUT/'RESULT.json').relative_to(ROOT).as_posix(),sha256=sha(OUT/'RESULT.json'),board=False),'## FLAP局部逐级控制冻结\n\nSHA `'+sha(OUT/'RESULT.json')+'`；仅BuildID→Descriptor→Chain→Layer→Timing逐级自身原字节，通过才下一项。J1已有唯一prefill无完整安全原退出/采集前，禁止任何新COM3/网络/上传；本次不重复成功门禁，不中断未知owner。')
    print(p['status'],sha(OUT/'RESULT.json'))


def checked():
    p=read(OUT/'RESULT.json')
    for n,h in p['frozen'].items():assert sha(ROOT/n)==h,n
    for n,h in p['tests'].items():assert sha(ROOT/n)==h,n
    assert p['manifest_sha256']==c.MANIFEST==sha(c.PKG/'PACKAGE_MANIFEST.json')
    for n in ('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'):assert sha(OUT/'RESULT.json') in (ROOT/n).read_text(encoding='utf-8-sig')
    transfer=read(R/'JF-board-artifact-transfer-02/BOARD_RESULT.json')
    assert transfer['status']=='PASS_JF_ARTIFACT_TRANSFER_ONLY' and transfer['temporary_address_restored'] and transfer['package_manifest_sha256']==c.MANIFEST
    board_available();return p
def network(level,mode):
    cmd=[PWSH,'-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'scripts/optimization/jf_fetch_pc_network02.ps1'),'-Mode',mode,'-Level',level]
    subprocess.run(cmd,cwd=ROOT,check=True)
def fetch_saved(r,raw,level):
    digest=hashlib.sha256(raw).hexdigest();net=LOG/(level+'_fetch');net.mkdir();save(net/'RAW_BINDING.json',dict(raw_sha256=digest))
    network(level,'Before')
    command='sudo -n /usr/local/share/pynq-venv/bin/python -B '+REMOTE+'/jf_saved_fetch01.py serve '+level+' '+digest+' --self-sha '+sha(Path(saved.__file__))
    server=LOG/(level+'_Fetch01.log');error=None;receipt=None
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        future=pool.submit(uart,command,level+'_Fetch01',420)
        try:
            deadline=time.monotonic()+40
            while not (server.exists() and 'JF_SAVED_FETCH02_READY' in server.read_text(encoding='utf-8-sig')):
                if future.done():raise RuntimeError('Saved-only server ended before listening')
                if time.monotonic()>deadline:raise TimeoutError('Saved-only readiness budget')
                time.sleep(.1)
            receipt=saved.fetch(raw,digest,level,net/'received')
        except BaseException as e:error=e
        host_rc,_=future.result()
    network(level,'After')
    if error is not None:
        save(net/'FETCH_REJECTED.json',dict(status='WAIT_SAVED_BYTES_COLLECTION_ONLY_NO_GATE_RERUN',error=repr(error),original_host_rc=host_rc));raise error
    assert host_rc==0 and receipt['status']=='PC_BYTES_VERIFIED_AWAITING_COM3_NETWORK_CLOSURE'
    text=server.read_text(encoding='utf-8-sig');hs=re.findall(r'(?m)^JF_FETCH_RAW_SHA256=([0-9a-f]{64})\r?$',text);parts=re.findall(r'(?m)^JF_FETCH_RAW_PART=([A-Za-z0-9+/=]+)\r?$',text)
    b=b''.join(base64.b64decode(z,validate=True) for z in parts);assert hs==[hashlib.sha256(b).hexdigest()]
    proof=json.loads(b);assert proof['status']=='PASS_JF_SAVED_FETCH02' and proof['raw_sha256']==digest and proof['files']==r['raw_files'] and not proof['errors'] and proof['temporary_address_restored']
    assert saved.addresses(proof['addresses_before'])==saved.addresses(proof['addresses_after']) and proof['default_routes_before']==proof['default_routes_after']
    atomic(net/'received/TRANSFER_RESULT.json',b,immutable=True)
    files={z['path']:(net/'received'/z['path']).read_bytes() for z in r['raw_files']}
    c.validate(r,level,files)
    out=R/('JF-board-'+level.lower()+'-02');atomic(out/'BOARD_RESULT.json',raw,immutable=True)
    for n,b in files.items():atomic(out/'raw'/n,b,immutable=True)
    audit=dict(status='PASS_SAVED_JF_GATE_AUDIT',raw_sha256=digest,original_gate_rc=r['gate_return_code'],reexecuted=False,collector_sha256=sha(Path(c.__file__)),network_proof_sha256=hs[0],UART_sha256=sha(server),PC_before_sha256=sha(net/'pc_network_before01.json'),PC_after_sha256=sha(net/'pc_network_after01.json'),complete_binary_count=len(files))
    save(out/'COLLECTION.json',audit)
    synchronized('latest_jf_board_'+level.lower()+'01',dict(status=r['status'],result=(out/'BOARD_RESULT.json').relative_to(ROOT).as_posix(),sha256=digest,board=True,performance=level=='Timing'),f"## JF 真实{level}原字节严格闭合\n\n原raw SHA `{digest}`；原rc0，{len(files)}份完整binary/逐位数值/原配置同PID-PFN/同TTY环境/七owner逆序释放/稳定与原四时钟和双方网络恢复全部独立核验。仅JF的L0与L18原版和冻结候选四链T32串行完整局部MLP诊断，不代表质量，非Transformer整层/整模型。Timing固定4预热8正式，同次原层重测，收益由原配对CI裁决，不追加样本，不自动晋级。")
def run(level):
    checked();assert level in c.LEVELS
    assert not (LOG/(level+'_Run01.log')).exists() and not (R/('JF-board-'+level.lower()+'-02')/'BOARD_RESULT.json').exists()
    prior=''
    if level!='BuildID':
        prev=c.LEVELS[c.LEVELS.index(level)-1];path=R/('JF-board-'+prev.lower()+'-02')/'BOARD_RESULT.json';r=read(path);audit=read(path.parent/'COLLECTION.json');prior=sha(path)
        assert r['gate_return_code']==0 and audit['status']=='PASS_SAVED_JF_GATE_AUDIT' and audit['raw_sha256']==prior
        for n in ('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'):assert prior in (ROOT/n).read_text(encoding='utf-8-sig')
    rc,auth=uart('sudo -n true',level+'_sudo01',15)
    if rc:
        out=R/('JF-'+level+'-authorization-required-01');save(out/'RESULT.json',dict(status='WAIT_JF_CURRENT_COM3_SUDO_BEFORE_GATE',original_host_rc=rc,log_sha256=sha(auth),board=False,Overlay=0,DMA=0))
        synchronized('latest_jf_auth_required01',dict(status='WAIT_JF_CURRENT_COM3_SUDO_BEFORE_GATE',result=(out/'RESULT.json').relative_to(ROOT).as_posix(),sha256=sha(out/'RESULT.json'),board=False),f"## JF 同TTY授权在{level}前停止\n\nSHA `{sha(out/'RESULT.json')}`，原host rc{rc}、log `{sha(auth)}`；原串口记录为准，未执行本级Overlay/DMA，不当DUT失败，不重复命令。需真人恢复shell或sudo-v后另立新日志版本。")
        raise RuntimeError('Current same-terminal sudo failed; no gate attempted')
    rc,_=uart('test ! -e '+EVIDENCE+'/'+level,level+'_absent01',15);assert rc==0
    command='sudo -n bash /home/ubuntu/jf_run_gate_lf02.sh '+'63b16687daadb08b1b73be36bdf912136bf36c60c2b97e7100090902714ce013'+' '+c.MANIFEST+' '+level+(' --prior-sha '+prior if prior else '')+' --enable-gate'
    rc,log=uart(command,level+'_Run01',1200,'JF_RETAIN_PROCESS_OVERLAY_ALL_OWNERS_DO_NOT_INTERRUPT')
    try:r,raw=decode(log.read_text(encoding='utf-8-sig'),lambda z:c.need(z.get('gate_level')==level and z.get('manifest_sha256')==c.MANIFEST,'Actual raw envelope'))
    except BaseException:
        save(LOG/(level+'_HOST_UNRESOLVED.json'),dict(status='WAIT_ORIGINAL_SAVED_BYTES_NO_COMMAND_OR_RERUN',original_host_rc=rc,log_sha256=sha(log),board_owner_unknown=True));raise
    if r['gate_return_code']!=0:c.collect(log,level);raise RuntimeError('Actual gate failed; stop at this level')
    assert rc==0 and r['safe_buffers_released'] and r['stable_restored'] and not r['unsafe_dma_buffers_retained']
    if level in ('BuildID','Descriptor'):
        file_rc,fileslog=uart('sudo -n /usr/local/share/pynq-venv/bin/python -B '+REMOTE+'/jf_saved_files01.py '+level+' '+hashlib.sha256(raw).hexdigest(),level+'_Files01',120)
        assert file_rc==0,'Collect existing bytes only; no gate rerun';c.collect(log,level,fileslog)
    else:fetch_saved(r,raw,level)
    print('JF_ACTUAL_'+level.upper()+'_COLLECTED',hashlib.sha256(raw).hexdigest())
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=('Prepare','Run'));p.add_argument('--level',choices=c.LEVELS);a=p.parse_args()
    if a.mode=='Prepare':prepare()
    elif a.level is None:raise ValueError('Explicit one level required')
    else:run(a.level)
