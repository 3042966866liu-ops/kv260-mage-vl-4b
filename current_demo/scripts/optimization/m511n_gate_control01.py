"""One explicit COM3 gate; serialized ownership, original bytes, no retries."""
import argparse,base64,concurrent.futures,hashlib,json,re,subprocess,time
from pathlib import Path
from m351_workflow import BASE,sha,atomic,encoded
from m455456_workflow02 import synchronized
import m511n_collect_board01 as c
from m511n_saved_wire01 import decode
import m511n_saved_fetch02 as saved
ROOT=Path(__file__).resolve().parents[2];R=BASE/'runs';LOG=ROOT/'tmp/m511n_board01';OUT=R/'M511N-gate-control-preparation-01'
UART=ROOT/'scripts/m455_original94_uart03.ps1';REMOTE='/dev/shm/m511n_width_board_01';EVIDENCE='/home/ubuntu/m511n_width_evidence_01'
PWSH='C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe'
def read(p):return json.loads(p.read_bytes())
def save(p,v):atomic(p,encoded(v),immutable=True)
def uart(command,label,seconds=30,retained=''):
    LOG.mkdir(parents=True,exist_ok=True);path=LOG/(label+'.log');host=LOG/(label+'_host.log')
    if path.exists() or host.exists():raise RuntimeError('Original COM3 attempt exists; observe/collect only')
    args=[PWSH,'-NoProfile','-ExecutionPolicy','Bypass','-File',str(UART),'-Command',command,'-LogPath',path.relative_to(ROOT).as_posix(),'-TimeoutSeconds',str(seconds),'-MarkerPrefix','__M511N_'+label.upper()+'_RC_']
    if retained:args+=['-RetainedMarker',retained]
    with host.open('xb') as f:rc=subprocess.run(args,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT).returncode
    return rc,path
def board_available():
    import jf_gate_control04 as old
    old.board_available()
    f=R/'M507-board-timing-01/BOARD_RESULT.json';r=read(f)
    assert read(f.parent/'COLLECTION.json')['raw_sha256']==sha(f)
    assert r['gate_return_code']==0 and r['safe_buffers_released'] and r['stable_restored'] and r['original_clocks_restored'] and not r['unsafe_dma_buffers_retained']
    for level in c.LEVELS:
        if (LOG/(level+'_Run01.log')).exists():
            f=R/('M511N-board-'+level.lower()+'-01')/'BOARD_RESULT.json'
            if not f.exists() or not (f.parent/'COLLECTION.json').exists():raise RuntimeError('M511N owner/collection unknown; no command')
            r=read(f);a=read(f.parent/'COLLECTION.json')
            assert a['raw_sha256']==sha(f) and r['gate_return_code']==0 and r['safe_buffers_released'] and r['stable_restored'] and r['original_clocks_restored'] and not r['unsafe_dma_buffers_retained']


def checked():
    p=read(OUT/'RESULT.json')
    for n,h in p['frozen'].items():assert sha(ROOT/n)==h,n
    assert p['manifest_sha256']==c.MANIFEST==sha(c.PKG/'PACKAGE_MANIFEST.json')
    for row in read(c.PKG/'PACKAGE_MANIFEST.json')['files']:assert sha(c.PKG/row['path'])==row['sha256']
    transfer=read(R/'M511N-board-artifact-transfer-01/BOARD_RESULT.json')
    assert transfer['status']=='PASS_M511N_ARTIFACT_TRANSFER_ONLY' and transfer['temporary_address_restored'] and transfer['package_manifest_sha256']==c.MANIFEST
    for n in ('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'):assert sha(OUT/'RESULT.json') in (ROOT/n).read_text(encoding='utf-8-sig')
    board_available();return p

def network(level,mode):
    cmd=[PWSH,'-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'scripts/optimization/m511n_fetch_pc_network02.ps1'),'-Mode',mode,'-Level',level]
    subprocess.run(cmd,cwd=ROOT,check=True)
def fetch_saved(r,raw,level):
    digest=hashlib.sha256(raw).hexdigest();net=LOG/(level+'_fetch');net.mkdir();save(net/'RAW_BINDING.json',dict(raw_sha256=digest))
    network(level,'Before')
    command='sudo -n /usr/local/share/pynq-venv/bin/python -B '+REMOTE+'/m511n_saved_fetch02.py serve '+level+' '+digest+' --self-sha '+sha(Path(saved.__file__))
    server=LOG/(level+'_Fetch01.log');error=None;receipt=None
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        future=pool.submit(uart,command,level+'_Fetch01',420)
        try:
            deadline=time.monotonic()+40
            while not (server.exists() and 'M511N_SAVED_FETCH02_READY' in server.read_text(encoding='utf-8-sig')):
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
    text=server.read_text(encoding='utf-8-sig');hs=re.findall(r'(?m)^M511N_FETCH_RAW_SHA256=([0-9a-f]{64})\r?$',text);parts=re.findall(r'(?m)^M511N_FETCH_RAW_PART=([A-Za-z0-9+/=]+)\r?$',text)
    b=b''.join(base64.b64decode(z,validate=True) for z in parts);assert hs==[hashlib.sha256(b).hexdigest()]
    proof=json.loads(b);assert proof['status']=='PASS_M511N_SAVED_FETCH02' and proof['raw_sha256']==digest and proof['files']==r['raw_files'] and not proof['errors'] and proof['temporary_address_restored']
    assert saved.addresses(proof['addresses_before'])==saved.addresses(proof['addresses_after']) and proof['default_routes_before']==proof['default_routes_after']
    atomic(net/'received/TRANSFER_RESULT.json',b,immutable=True)
    files={z['path']:(net/'received'/z['path']).read_bytes() for z in r['raw_files']}
    c.validate(r,level,files)
    out=R/('M511N-board-'+level.lower()+'-01');atomic(out/'BOARD_RESULT.json',raw,immutable=True)
    for n,b in files.items():atomic(out/'raw'/n,b,immutable=True)
    audit=dict(status='PASS_SAVED_M511N_GATE_AUDIT',raw_sha256=digest,original_gate_rc=r['gate_return_code'],reexecuted=False,collector_sha256=sha(Path(c.__file__)),network_proof_sha256=hs[0],UART_sha256=sha(server),PC_before_sha256=sha(net/'pc_network_before01.json'),PC_after_sha256=sha(net/'pc_network_after01.json'),complete_binary_count=len(files))
    save(out/'COLLECTION.json',audit)
    synchronized('latest_m511n_board_'+level.lower()+'01',dict(status=r['status'],result=(out/'BOARD_RESULT.json').relative_to(ROOT).as_posix(),sha256=digest,board=True,performance=level=='Timing'),f"## M511N 真实{level}原字节严格闭合\n\n原raw SHA `{digest}`；原rc0，{len(files)}份完整binary/逐位数值/原配置同PID-PFN/同TTY环境/七owner逆序释放/稳定与原四时钟和双方网络恢复全部独立核验。仅冻结S与neighbor双方L0/L18/L35三处T32完整MLP连续串行墙钟诊断，不代表质量，非Transformer整层/整模型。Timing固定4预热8正式，同次S/neighbor双组重测，收益由原配对CI裁决，不追加样本，不自动晋级。")
def run(level):
    checked();assert level in c.LEVELS
    assert not (LOG/(level+'_Run01.log')).exists() and not (R/('M511N-board-'+level.lower()+'-01')/'BOARD_RESULT.json').exists()
    prior=''
    if level!='BuildID':
        prev=c.LEVELS[c.LEVELS.index(level)-1];path=R/('M511N-board-'+prev.lower()+'-01')/'BOARD_RESULT.json';r=read(path);audit=read(path.parent/'COLLECTION.json');prior=sha(path)
        assert r['gate_return_code']==0 and audit['status']=='PASS_SAVED_M511N_GATE_AUDIT' and audit['raw_sha256']==prior
        for n in ('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'):assert prior in (ROOT/n).read_text(encoding='utf-8-sig')
    rc,auth=uart('sudo -n true',level+'_sudo01',15)
    if rc:
        out=R/('M511N-'+level+'-authorization-required-01');save(out/'RESULT.json',dict(status='WAIT_M511N_CURRENT_COM3_SUDO_BEFORE_GATE',original_host_rc=rc,log_sha256=sha(auth),board=False,Overlay=0,DMA=0))
        synchronized('latest_m511n_auth_required01',dict(status='WAIT_M511N_CURRENT_COM3_SUDO_BEFORE_GATE',result=(out/'RESULT.json').relative_to(ROOT).as_posix(),sha256=sha(out/'RESULT.json'),board=False),f"## M511N 同TTY授权在{level}前停止\n\nSHA `{sha(out/'RESULT.json')}`，原host rc{rc}、log `{sha(auth)}`；原串口记录为准，未执行本级Overlay/DMA，不当DUT失败，不重复命令。需真人恢复shell或sudo-v后另立新日志版本。")
        raise RuntimeError('Current same-terminal sudo failed; no gate attempted')
    rc,_=uart('test ! -e '+EVIDENCE+'/'+level,level+'_absent01',15);assert rc==0
    command='sudo -n bash '+REMOTE+'/run_gate01.sh '+sha(c.PKG/'run_gate01.sh')+' '+c.MANIFEST+' '+level+(' --prior-sha '+prior if prior else '')+' --enable-gate'
    rc,log=uart(command,level+'_Run01',1200,'M511N_RETAIN_PROCESS_OVERLAY_ALL_OWNERS_DO_NOT_INTERRUPT')
    try:r,raw=decode(log.read_text(encoding='utf-8-sig'),lambda z:c.need(z.get('gate_level')==level and z.get('manifest_sha256')==c.MANIFEST,'Actual raw envelope'))
    except BaseException:
        save(LOG/(level+'_HOST_UNRESOLVED.json'),dict(status='WAIT_ORIGINAL_SAVED_BYTES_NO_COMMAND_OR_RERUN',original_host_rc=rc,log_sha256=sha(log),board_owner_unknown=True));raise
    if r['gate_return_code']!=0:c.collect(log,level);raise RuntimeError('Actual gate failed; stop at this level')
    assert rc==0 and r['safe_buffers_released'] and r['stable_restored'] and not r['unsafe_dma_buffers_retained']
    if level in ('BuildID','Descriptor'):
        file_rc,fileslog=uart('sudo -n /usr/local/share/pynq-venv/bin/python -B '+REMOTE+'/m511n_saved_files01.py '+level+' '+hashlib.sha256(raw).hexdigest(),level+'_Files01',120)
        assert file_rc==0,'Collect existing bytes only; no gate rerun';c.collect(log,level,fileslog)
    else:fetch_saved(r,raw,level)
    print('M511N_ACTUAL_'+level.upper()+'_COLLECTED',hashlib.sha256(raw).hexdigest())
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=('Prepare','Run'));p.add_argument('--level',choices=c.LEVELS);a=p.parse_args()
    if a.mode=='Prepare':raise RuntimeError('Prepared by frozen m511n_prepare_controls01 only')
    elif a.level is None:raise ValueError('Explicit one level required')
    else:run(a.level)
