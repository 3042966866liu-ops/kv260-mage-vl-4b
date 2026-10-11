"""Prepare independent M443 lower controls; no board or package execution."""
import ast,json
from pathlib import Path
import m351_workflow as w
from m441_host_io08 import atomic
OUT=w.ROOT/'tmp/m443_board_controls_01'
FOUND=w.ROOT/'tmp/m443_board_support_01'
RUN=w.BASE/'runs/M443-board-controls-preparation-01'
def changed(text,a,b):
    assert a in text,a
    return text.replace(a,b)
def derive(name):
    text=(w.HERE/name).read_text(encoding='utf-8-sig')
    text=text.replace('m441','m443').replace('M441','M443')
    text=text.replace('0x4d343431','0x4d343433').replace('0x4D343431','0x4D343433')
    return text
def main():
    assert not OUT.exists() and not RUN.exists(),'Existing preparation; inspect only'
    p=w.BASE/'runs/M443-board-support-preparation-01/RESULT.json';foundation=json.loads(p.read_bytes())
    assert foundation['status']=='PREPARED_M443_FROZEN_FIXTURES_AND_CONFIGURATION_CONTRACT01'
    for row in foundation['files']:assert w.sha(w.ROOT/row['path'])==row['sha256']
    for n in ('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'):
        assert w.sha(p) in (w.ROOT/n).read_text(encoding='utf-8-sig')
    files={};originals=[]
    names=('m441_board_probe.py','m441_board_collection.py','m441_control07.ps1','m441_gate_runner.sh',
        'm441_export_result.py','m441_completion_observer.py','m441_comparison.py','m441_transfer.py','m441_transfer_collection.py')
    for name in names:originals.append(dict(path=(w.HERE/name).relative_to(w.ROOT).as_posix(),sha256=w.sha(w.HERE/name)))
    for name in names:
        text=derive(name)
        if name.endswith('.py'):text=text.replace("MODES=('BuildID','Descriptor','Chain','Compare')","MODES=('BuildID','Descriptor','Chain')")
        if name=='m441_board_probe.py':
            text=changed(text,'OLD_BUILD=0x4d333537','OLD_BUILD=0x4d343431')
            text=changed(text,'from m443_comparison import derive_comparison','from m443_comparison import derive_comparison\nfrom m443_configuration01 import Configuration,validate_record,sha as configuration_sha')
            text=changed(text,'active=False;ever_started=False;last_completed=False;expected_build=None','active=False;ever_started=False;last_completed=False;expected_build=None\n    configuration=None')
            text=changed(text,'if active or base is None or kernel is None:return False','if active or (configuration is not None and configuration.unknown) or base is None or kernel is None:return False')
            text=changed(text,'nonlocal kernel,dma,overlay,expected_build,ever_started,last_completed','nonlocal kernel,dma,overlay,expected_build,ever_started,last_completed,configuration')
            text=changed(text,"if active or buffers:raise RuntimeError('Live storage before Overlay change')","if active or buffers or (configuration is not None and configuration.unknown):raise RuntimeError('Live or unknown ownership before Overlay change')")
            text=changed(text,'overlay=Overlay(str(bit),download=True)',"""if variant=='B':
            configuration=Configuration(HERE/'CONFIGURATION_APPLICATION.json',args.manifest_sha,directory)
            try:overlay=configuration.load(bit,Overlay)
            finally:
                result['configuration_record']=configuration.record
                result['unknown_configuration_ownership']=configuration.unknown
            result['configuration_application_accepted']=True
        else:overlay=Overlay(str(bit),download=True)""")
            text=changed(text,"result['prior_raw_sha256']=args.prior_sha","""result['prior_raw_sha256']=args.prior_sha
            build_raw=EVIDENCE/'BuildID/BOARD_RESULT.json'
            application_sha=configuration_sha(HERE/'CONFIGURATION_APPLICATION.json')
            build_data=json.loads(build_raw.read_bytes())
            if build_data['status']!='PASS_M443_BUILDID' or build_data['gate_return_code']!=0 or build_data.get('configuration_application_accepted') is not True:
                raise RuntimeError('Actual new-bit configuration application missing')
            validate_record(build_data['configuration_record'],application_sha,args.manifest_sha)
            validate_record(prior_data['configuration_record'],application_sha,args.manifest_sha)
            result['configuration_application_build_raw_sha256']=configuration_sha(build_raw)""")
            text=changed(text,'if overlay is not None and not active and (not buffers or release_safe()):','if overlay is not None and not active and not (configuration is not None and configuration.unknown) and (not buffers or release_safe()):')
            text=changed(text,'unsafe=active or (bool(buffers) and not release_safe())','unsafe=active or (configuration is not None and configuration.unknown) or (bool(buffers) and not release_safe())')
            text=changed(text,"gate_return_code=1,unsafe_dma_buffers_retained=unsafe)","gate_return_code=1,unsafe_dma_buffers_retained=unsafe,unknown_configuration_ownership=bool(configuration and configuration.unknown))")
            text=text.replace('balanced original-Q comparison','exact configuration proof')
        elif name=='m441_board_collection.py':
            text=changed(text,'BUILDS=dict(A=0x4d333537,B=0x4d343433,R=0x4d395832)','BUILDS=dict(A=0x4d343431,B=0x4d343433,R=0x4d395832)')
            text=changed(text,"FIXTURE=ROOT/'tmp/m443_board_support_07/BOARD_CASES.json'","FIXTURE=ROOT/'tmp/m443_board_support_01/BOARD_CASES.json'\nfrom m443_configuration01 import validate_record,sha as configuration_sha")
            text=changed(text,"spec=json.loads(FIXTURE.read_bytes());rows=r['transactions']","""spec=json.loads(FIXTURE.read_bytes());rows=r['transactions']
        if r.get('configuration_application_accepted') is not True or r.get('unknown_configuration_ownership') is not False:
            raise ValueError('New-bit configuration not accepted or ownership unknown')
        validate_record(r['configuration_record'],configuration_sha(FIXTURE.parent/'CONFIGURATION_APPLICATION.json'),manifest_sha)
        if mode!='BuildID':
            proof=BASE/'runs/M443-buildid-board-01/BOARD_RESULT.json'
            if r.get('configuration_application_build_raw_sha256')!=sha(proof):raise ValueError('Actual BuildID configuration proof binding')
            b=json.loads(proof.read_bytes())
            if b['status']!='PASS_M443_BUILDID' or b['gate_return_code']!=0 or b.get('configuration_application_accepted') is not True:raise ValueError('Configuration origin rejected')
            validate_record(b['configuration_record'],configuration_sha(FIXTURE.parent/'CONFIGURATION_APPLICATION.json'),manifest_sha)""")
            text=changed(text,"atomic(p,raw,immutable=True)","from m441_host_io08 import atomic as durable_atomic\n    import m351_workflow as workflow\n    workflow.atomic=durable_atomic\n    durable_atomic(p,raw,immutable=True)")
            text=text.replace('A为M357','A为M441').replace('2026-10-07','2026-10-11')
        elif name=='m441_control07.ps1':
            text=text.replace(",'Compare'",'').replace(";Compare='chain'",'')
            text=text.replace('$taskPython -B (Join-Path','$taskPython -B -X utf8 (Join-Path').replace("@('-B',(Join-Path","@('-B','-X','utf8',(Join-Path")
        elif name=='m441_gate_runner.sh':text=text.replace('BuildID|Descriptor|Chain|Compare','BuildID|Descriptor|Chain')
        new=name.replace('m441','m443').replace('control07','control01')
        files[new]=text.encode('utf-8')
    files['m443_configuration01.py']=(w.HERE/'m443_configuration01.py').read_bytes()
    for name in ('m443_cma_contract01.py','m443_cma_trace01.py'):files[name]=(FOUND/name).read_bytes()
    OUT.mkdir()
    for name,raw in files.items():
        if name.endswith('.py'):ast.parse(raw.decode(),feature_version=(3,10))
        atomic(OUT/name,raw,immutable=True)
    # Host controller/collector import locations; board package copies exact frozen bytes.
    for name,raw in files.items():
        if name=='m443_configuration01.py':continue
        assert not (w.HERE/name).exists(),name
        atomic(w.HERE/name,raw,immutable=True)
    result=dict(status='PREPARED_M443_DISABLED_LOWER_CONTROLS01_UNTESTED',build_id='0x4D343433',
        foundation_sha256=w.sha(p),original_controls=originals,
        files=[dict(path=x.relative_to(w.ROOT).as_posix(),bytes=x.stat().st_size,sha256=w.sha(x)) for x in sorted(OUT.iterdir())],
        preparer_sha256=w.sha(Path(__file__)),board=False,hardware_package=False,
        configuration_application_accepted=False,configuration_credits_granted=0,
        next_step='Actual observer/probe/collector/control positive and negative fixture checks. No package, transfer or board gate before checks PASS.')
    atomic(RUN/'RESULT.json',w.encoded(result),immutable=True);w.atomic=atomic;s=w.sha(RUN/'RESULT.json')
    w.sync('latest_m443_board_controls_preparation01',dict(status=result['status'],result=(RUN/'RESULT.json').relative_to(w.ROOT).as_posix(),sha256=s,board=False,build_id=result['build_id']),
        '## M443禁默认执行低级控制准备01（2026-10-11）\n\nSHA '+s+'；独立BuildID/Descriptor/Chain、固定同TTY环境、原返回值保存采集、严格原完整参考及新bit配置观察模块。实际加载前标记未知所有权；同PID/PFN1904页释放/原累计计数/零事件丢失/实例自然回收全通过才接受；未知或异常保持Overlay、进程、buffer与锁。仅代码准备尚未完成组件正负检查，0板端/0配置实证/0credit；下一步实际模块失败路径测试后干净打包。')
    print(result['status'],s,len(files))
if __name__=='__main__':main()
