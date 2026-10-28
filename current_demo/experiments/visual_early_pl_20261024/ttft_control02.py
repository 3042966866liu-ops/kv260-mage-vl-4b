"""Fixed-peer fresh transfer, then explicitly ordered own M455 lower gates."""
import argparse,ast,json,re,subprocess,sys,time
from pathlib import Path,PurePosixPath
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2];H=Path(__file__).resolve().parent
sys.path[:0]=[str(H),str(ROOT/'experiments/pruning_plan_20261020'),str(ROOT/'experiments/speed_target_30s_20261020')]
from prepare_adaptive522 import R,read,save,sha,synchronized
from m441_host_io08 import atomic
from b0_collection523 import decode
from M455_P1_shape_prepare52303 import decode_shape
import ttft_ingress02 as transport
transport.TARGET=PurePosixPath('/dev/shm/m523_V12_ttft_package_20261024_02')
import native_control52203 as serial
PWSH='C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe'
LOG=ROOT/'tmp/m523_V12_ttft_20261024_02';serial.LOG=LOG
PREP=R/'M523-V12-ttft-control-02/RESULT.json'
CAP=R.parent/'candidates/M523-V12-ttft-control-20261024-02'
REMOTE='/dev/shm/m523_V12_ttft_control_20261024_02'
OUT=R/'M523-V12-ttft-board-02'

def freeze():
    raise RuntimeError('Prepared only by versioned prepare_L2_board52301')

def checked():
    p=read(PREP);assert sha(__file__)==p['source_sha256'] and sha(CAP/'PACKAGE_MANIFEST.json')==p['capsule_manifest_sha256']
    pkg=ROOT/p['package'];assert sha(pkg/'PACKAGE_MANIFEST.json')==p['manifest_sha256']
    for d in (CAP,pkg):
        m=read(d/'PACKAGE_MANIFEST.json')
        assert {f.relative_to(d).as_posix() for f in d.rglob('*') if f.is_file()}=={r['path'] for r in m['files']}|{'PACKAGE_MANIFEST.json'}
        for r in m['files']:assert (d/r['path']).stat().st_size==r['bytes'] and sha(d/r['path'])==r['sha256']
    return p,pkg
def require_sudo(label):
    rc=serial.uart('sudo -n true',label,15)
    if rc:
        out=OUT/(label+'_AUTH_STOP');save(out/'BOARD_RESULT.json',dict(status='SUDO_EXPIRED_NO_GATE_START',primary_rc=rc,
            gate_started=False,model_runs=0,log_sha256=sha(LOG/(label+'.log'))))
        h=sha(out/'BOARD_RESULT.json')
        synchronized('latest_m523_V12_ttft_20261024_auth_stop',dict(status='SUDO_EXPIRED_NO_GATE_START',result=(out/'BOARD_RESULT.json').relative_to(ROOT).as_posix(),sha256=h,board=True,hardware=False),
            '## M523当前22完整请求组件最小板测实际同TTY授权停止\n\nRESULT SHA '+h+'；COM3原sudo返回'+str(rc)+'，未启动本次门禁/模型/Overlay。原回执保持，只等待本次sudo续期，不重复前模型或假定旧授权永久有效。')
    return rc
def upload_capsule():
    p,pkg=checked();LOG.mkdir(parents=True,exist_ok=True)
    assert serial.uart('test ! -e '+REMOTE,'ControlAbsent01',15)==0
    m=read(CAP/'PACKAGE_MANIFEST.json')
    for i,name in enumerate(['PACKAGE_MANIFEST.json']+[r['path'] for r in m['files']]):
        raw=LOG/('ControlUpload'+str(i)+'_host.raw')
        with raw.open('xb') as f:
            rc=subprocess.run([PWSH,'-NoProfile','-File',str(ROOT/'scripts/m462_uart_put_file01.ps1'),
                '-LocalPath',(CAP/name).relative_to(ROOT).as_posix(),'-RemotePath',REMOTE+'/'+name,
                '-LogPrefix',LOG.relative_to(ROOT).as_posix()+'/ControlUpload'+str(i),'-ChunkBytes','900','-TimeoutSeconds','25'],
                cwd=ROOT,stdout=f,stderr=subprocess.STDOUT).returncode
        save(raw.with_suffix('.EXIT.json'),dict(original_host_rc=rc,host_sha256=sha(raw)))
        assert rc==0 and 'sha256='+sha(CAP/name) in raw.read_text(encoding='utf-8-sig')
    save(LOG/'CONTROL_UPLOAD.json',dict(manifest_sha256=p['capsule_manifest_sha256']))
def pc_network(mode):
    raw=LOG/('PCNetwork'+mode+'_host.raw')
    with raw.open('xb') as f:rc=subprocess.run([PWSH,'-NoProfile','-File',str(CAP/'pc_network.ps1'),'-Mode',mode,'-Level','Baseline'],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT).returncode
    save(raw.with_suffix('.EXIT.json'),dict(original_host_rc=rc,host_sha256=sha(raw)));assert rc==0
def install():
    p,pkg=checked();LOG.mkdir(parents=True,exist_ok=True)
    if require_sudo('IngressSudo02'):return 1
    upload_capsule();pc_network('Before')
    command='sudo -n /usr/local/share/pynq-venv/bin/python -I -B '+REMOTE+'/ingress.py '+p['ingress_sha256']+' '+p['manifest_sha256']
    args=[PWSH,'-NoProfile','-File',str(ROOT/'scripts/m455_original94_uart03.ps1'),'-Command',command,
        '-LogPath',(LOG/'Ingress01.log').relative_to(ROOT).as_posix(),'-TimeoutSeconds','700','-MarkerPrefix','__M523_P1_INGRESS_RC_']
    with (LOG/'Ingress01_host.raw').open('xb') as f:
        child=subprocess.Popen(args,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
        started=time.monotonic();ready=False
        while child.poll() is None and time.monotonic()-started<45:
            log=LOG/'Ingress01.log'
            if log.exists() and 'M523_M455_P1_INGRESS_READY' in log.read_text(encoding='utf-8-sig'):ready=True;break
            time.sleep(.25)
        if ready:
            try:save(LOG/'PC_SENT.json',transport.send(pkg,p['manifest_sha256']))
            except BaseException:
                # Receiver is independently bounded; do not kill its network cleanup.
                save(LOG/'PC_SEND_FAILED.json',dict(error_type=sys.exc_info()[0].__name__,model_runs=0))
        rc=child.wait(timeout=730)
    save(LOG/'Ingress01_EXIT.json',dict(original_host_rc=rc,log_sha256=sha(LOG/'Ingress01.log')))
    pc_network('After')
    v,raw=decode((LOG/'Ingress01.log').read_text(encoding='utf-8-sig'));d=OUT/'Install'
    atomic(d/'BOARD_RESULT.json',raw,immutable=True);save(d/'EXIT.json',dict(original_host_rc=rc,raw_sha256=sha(d/'BOARD_RESULT.json')))
    assert v['primary_rc']==rc and v['manifest_sha256']==p['manifest_sha256']
    h=sha(d/'BOARD_RESULT.json')
    synchronized('latest_m523_V12_ttft_20261024_install01',dict(status=v['status'],result=(d/'BOARD_RESULT.json').relative_to(ROOT).as_posix(),sha256=h,board=True,hardware=False),
        '## M523当前22完整请求组件最小板测包真实固定peer传输\n\nRESULT SHA '+h+'；原host/native '+str(rc)+'，独立有界RAM白名单/全SHA/字节/内存准入/网络恢复按原记录，0模型/Overlay/DMA。此为传输级，不是硬件PASS；失败只调试传输。')
    return rc
def import_gate():
    p,_=checked();prior=OUT/'Install/BOARD_RESULT.json';v=read(prior)
    assert v['primary_rc']==0 and v['temporary_address_restored']
    for name in ('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'):
        assert sha(prior) in (ROOT/name).read_text(encoding='utf-8-sig')
    command='/usr/local/share/pynq-venv/bin/python -I -B '+REMOTE+'/probe.py '+p['capsule_manifest_sha256']+' '+p['manifest_sha256']+' '+p['probe_sha256']
    rc=serial.uart(command,'Import01',180)
    v,raw=decode_shape((LOG/'Import01.log').read_text(encoding='utf-8-sig'));d=OUT/'Import'
    atomic(d/'BOARD_RESULT.json',raw,immutable=True);save(d/'EXIT.json',dict(original_host_rc=rc,native_primary_rc=v['primary_rc'],raw_sha256=sha(d/'BOARD_RESULT.json')))
    h=sha(d/'BOARD_RESULT.json');synchronized('latest_m523_V12_ttft_20261024_import',dict(status=v['status'],result=(d/'BOARD_RESULT.json').relative_to(ROOT).as_posix(),sha256=h,board=True,hardware=False),
        '## M523当前22固定完整请求A53导入\n\nRESULT SHA '+h+'；原host/native '+str(rc)+'/'+str(v['primary_rc'])+'，全包SHA/nlink/编译、实际adapter/native导入、原tokenizer128ID/4块/cap32与实际A53原copy插桩编译、实际boot核。0模型构造/Overlay/DMA；失败只本级，原字节保留。')
    assert rc==v['primary_rc'];return rc

def run_gate():
    p,_=checked();im=OUT/'Import/BOARD_RESULT.json';v=read(im)
    assert v['primary_rc']==0 and v['status']=='PASS_A53_V12_TTFT_IMPORT_CPU_ZERO_MODEL'
    prior=R/'M523-V12-local-board-01/Layer/BOARD_RESULT.json';v=read(prior)
    assert sha(prior)==p['actual_layer_sha256'] and v['primary_rc']==0 and v['safe_cleanup_complete'] and not v['unsafe_retained']
    for r in (im,prior):
        for name in ('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'):
            assert sha(r) in (ROOT/name).read_text(encoding='utf-8-sig')
    cfg=R/'M523-V12-config-retry-board02/BuildID/BOARD_RESULT.json';assert sha(cfg)==p['configuration_build_sha256'] and read(cfg)['primary_rc']==0
    if require_sudo('RequestSudo01'):return 1
    command='sudo -n bash '+str(transport.TARGET)+'/run.sh '+p['runner_sha256']+' '+p['manifest_sha256']
    assert '\\' not in command and command.startswith('sudo -n bash /dev/shm/')
    log=LOG/'Request01.log';host=LOG/'Request01_host.raw';assert not log.exists() and not host.exists()
    with host.open('xb') as f:
        rc=subprocess.run([PWSH,'-NoProfile','-File',str(ROOT/'scripts/m455_original94_uart03.ps1'),'-Command',command,
            '-LogPath',log.relative_to(ROOT).as_posix(),'-TimeoutSeconds','2400','-MarkerPrefix','__M523_NATIVE_PAIR_RC_',
            '-RetainedMarker','M523_M455_P1_RETAIN_PROCESS_LOCK_OVERLAY_ALL_OWNERS'],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT).returncode
    save(LOG/'Request01_EXIT.json',dict(original_host_rc=rc,log_sha256=sha(log),host_sha256=sha(host)))
    try:v,raw=decode_shape(log.read_text(encoding='utf-8-sig'))
    except BaseException:
        d=OUT/'CollectionPending';save(d/'RESULT.json',dict(status='COLLECTION_PENDING_GATEUP_NATIVE_NO_RERUN',original_host_rc=rc,log_sha256=sha(log),may_retain_process=True))
        h=sha(d/'RESULT.json');synchronized('latest_m523_V12_ttft_20261024_pending',dict(status='COLLECTION_PENDING_GATEUP_NATIVE_NO_RERUN',result=(d/'RESULT.json').relative_to(ROOT).as_posix(),sha256=h,board=True),
            '## M523 权重预取完整请求采集未闭合\n\nRESULT SHA '+h+'；原host '+str(rc)+'，只收原字节，不重跑/信号/free/reset，不猜完成或恢复。');return 1
    d=OUT/'Request';atomic(d/'BOARD_RESULT.json',raw,immutable=True)
    save(d/'EXIT.json',dict(original_host_rc=rc,native_primary_rc=v['primary_rc'],raw_sha256=sha(d/'BOARD_RESULT.json')))
    h=sha(d/'BOARD_RESULT.json');synchronized('latest_m523_V12_ttft_20261024_result',dict(status=v['status'],result=(d/'BOARD_RESULT.json').relative_to(ROOT).as_posix(),sha256=h,board=True,hardware=True,performance_pass=False,production_promoted=False),
        '## M523 Gate/Up 权重预取完整预热ABBA原结果（2026-10-24）\n\nRESULT SHA '+h+'；原host/native '+str(rc)+'/'+str(v['primary_rc'])+'，状态'+v['status']+'。当前22 A与仅V12原宽迁移B，128/4T32，两臂同C解析/单slot预取；各1预热+热态ABBABAAB，共10次首token/0Decode。原始结果待逐请求数值/物理/计时保存审计，不自动宣称提速或晋级。')
    assert rc==v['primary_rc'] and v['manifest_sha256']==p['exact_lower_package_manifest_sha256']
    if rc==0:
        assert v['status']=='PASS_V12_CURRENT22_128_WARMED_MATCHED_PENDING_SAVED_AUDIT'
        assert v['model_forwards']==v['total_prefills_returned']==10 and v['first_token_samples_returned']==10
        assert v['actual_input_tokens']==128 and v['input_T32_blocks']==4 and v['decode_calls']==0
        assert v['safe_cleanup_complete'] and not v['unsafe_retained'] and len(v['allocations'])==len(v['releases'])==7
        assert v['clock_final']==v['clock_initial']
    print('GATEUP_FULL_RESULT',h,rc,v['status'],v['errors'],flush=True);return rc

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('action',choices=('Install','Import','Run'));a=ap.parse_args().action
    raise SystemExit(install() if a=='Install' else import_gate() if a=='Import' else run_gate())
