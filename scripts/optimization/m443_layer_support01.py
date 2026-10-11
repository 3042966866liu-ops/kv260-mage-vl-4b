"""Explicit component/collector fixtures and saved UART receipt, never board inference."""
import base64
import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path
import m351_workflow as w
from m441_host_io08 import atomic
import m443_layer_collect01 as c
from m443_layer_configuration01 import LayerConfiguration


def emit(r):
    raw=w.encoded(r);chunks=[raw[i:i+900] for i in range(0,len(raw),900)]
    return 'M443L_RESULT_SHA256='+hashlib.sha256(raw).hexdigest()+'\nM443L_SAVED_GATE_RC='+str(r['gate_return_code'])+'\n'+''.join('M443L_RESULT_CHUNK='+str(i)+'/'+str(len(chunks))+':'+base64.b64encode(b).decode()+'\n' for i,b in enumerate(chunks))+f'M443L_DONE case=B1 gate_rc={r["gate_return_code"]} export_rc=0\n'


def fixtures():
    # These explicit fixtures exercise actual wrapper guards without a programming API.
    calls=[]
    class Observer:
        def __init__(self,*a): self.unknown=False;self.record=None;self.overlay=None
        def load(self,bit,loader):
            self.unknown=True;self.record={'explicit_fixture':True};self.overlay=loader()
            self.unknown=False;return self.overlay
    result={};x=LayerConfiguration(result,Path('/explicit-fixture'), 'fixture', 'fixture', 'fixture',factory=Observer)
    try:x.require_allocation_eligibility()
    except RuntimeError:pass
    else:raise AssertionError('Unproven configuration allocated')
    for args,kwargs in (((),{}), ((),{'download':False}), ((1,),{'download':True})):
        try:x.load(x.bit,lambda:calls.append(1),*args,**kwargs)
        except RuntimeError:pass
        else:raise AssertionError('Changed Overlay call accepted')
    try:x.load(Path('/wrong/bit'),lambda:calls.append(1),download=True)
    except RuntimeError:pass
    else:raise AssertionError('Different bit accepted')
    assert not calls
    token=object();assert x.load(x.bit,lambda:token,download=True) is token
    x.require_allocation_eligibility();assert x.accepted and not x.retain_required
    class Unknown(Observer):
        def load(self,bit,loader):
            self.unknown=True;self.record={'explicit_fixture_unknown':True};self.overlay=token
            raise RuntimeError('EXPLICIT_PROGRAMMING_OWNERSHIP_UNKNOWN')
    failed_result={};failed=LayerConfiguration(failed_result,Path('/explicit-fixture'),'fixture','fixture','fixture',factory=Unknown)
    try:failed.load(failed.bit,lambda:token,download=True)
    except RuntimeError as e:assert str(e)=='EXPLICIT_PROGRAMMING_OWNERSHIP_UNKNOWN'
    else:raise AssertionError('Unknown transition passed')
    assert failed.retain_required and failed.observer.overlay is token and not failed.accepted
    assert failed_result['unknown_configuration_ownership'] and not failed_result['configuration_application_accepted']
    try:failed.require_allocation_eligibility()
    except RuntimeError:pass
    else:raise AssertionError('Unknown configuration allocated')
    prep=json.loads(c.PREP.read_bytes())
    # A prior real M441 layer raw is explicitly relabeled only for decoder tests.
    old=w.BASE/'runs/M441-single-layer-board-09/BOARD_RESULT.json'
    r=json.loads(old.read_bytes());assert r['status']=='PASS_M441L_SINGLE_LAYER_DIAGNOSTIC'
    build=json.loads((c.PKG/'M443_BUILD_CONFIGURATION_PROOF.json').read_bytes())
    r.update(status='PASS_M443L_SINGLE_LAYER_DIAGNOSTIC',build_id='0x4D343433',manifest_sha256=prep['manifest_sha256'],
             prior_board_sha256=prep['prior_raw_sha256'],configuration_application_build_raw_sha256=prep['configuration_build_raw_sha256'],
             configuration_application_accepted=True,unknown_configuration_ownership=False,configuration_record=build['configuration_record'])
    r['final_snapshot']['ap_return']=0x4d343433
    assert c.decode(emit(r))[2]==r
    failure=dict(r,status='FAIL_UNSAFE_RETAINED',gate_return_code=1,errors=['explicit unknown configuration fixture'],
                 unknown_configuration_ownership=True,configuration_application_accepted=False,unsafe_buffers_retained=True,safe_buffers_released=False)
    assert c.decode(emit(failure))[2]==failure
    negatives=[emit(r)+emit(r),emit(r).replace('CHUNK=0/','CHUNK=1/'),emit(r).replace('export_rc=0','export_rc=1'),emit(r).replace('SAVED_GATE_RC=0','SAVED_GATE_RC=1')]
    for key,value in [('manifest_sha256','0'*64),('prior_board_sha256','0'*64),('configuration_application_build_raw_sha256','0'*64),
                      ('configuration_application_accepted',False),('unknown_configuration_ownership',True),('source_compatibility_checked_before_overlay',False),
                      ('additional_cma_requests_allowed',True),('numerical_pass',False),('performance_pass',True),('unsafe_buffers_retained',True),
                      ('safe_buffers_released',False),('model_forward_calls',2),('exact_comparison',{'hidden':False}),('released_buffers',[]),
                      ('fpga_transactions',0),('stable_overlay_reloaded',False),('errors',['explicit fixture'])]:
        negatives.append(emit(dict(r,**{key:value})))
    for key,value in [('manifest_sha256','0'*64),('bit_sha256','0'*64),('pid',1),('configuration_credits_granted',1904)]:
        bad=copy.deepcopy(r);bad['configuration_record'][key]=value;negatives.append(emit(bad))
    bad=copy.deepcopy(r);bad['configuration_record']['trace']['own_instance_removed']=False;negatives.append(emit(bad))
    for log in negatives:
        try:c.decode(log)
        except (ValueError,KeyError,AssertionError,RuntimeError):pass
        else:raise AssertionError('Changed layer evidence accepted')
    control=w.HERE/'m443_layer_control01.ps1'
    tested=subprocess.run(['C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe','-NoLogo','-NoProfile','-File',str(control),'-Mode','SelfTest'],capture_output=True,text=True,encoding='utf-8')
    assert tested.returncode==0 and 'M443L_CONTROL_SELFTEST_PASS' in tested.stdout,tested.stdout+tested.stderr
    paths=list(sorted(c.PKG.iterdir()))+[control,w.HERE/'m443_layer_collect01.py',w.HERE/'m443_layer_configuration01.py',w.HERE/'m365_collect.py',Path(__file__)]
    out=w.BASE/'runs/M443-single-layer-support-01'
    result=dict(status='PASS_M443_SINGLE_LAYER_SUPPORT_FIXTURES01',manifest_sha256=prep['manifest_sha256'],preparation_sha256=w.sha(c.PREP),
                configuration_wrapper_component_guards_pass=True,unknown_overlay_object_retained=True,allocator_refused_without_actual_proof=True,
                explicit_prior_raw_fixture_not_new_board_evidence=True,prior_fixture_raw_sha256=w.sha(old),collector_negative_checks=len(negatives),
                collector_pass_and_unknown_failure_verified=True,control_parser_and_failure_collection_pass=True,
                files=[dict(path=p.relative_to(w.ROOT).as_posix(),sha256=w.sha(p)) for p in paths],board_executed=False,performance_pass=False,promoted=False)
    atomic(out/'CONTROL_SELFTEST.stdout.txt',tested.stdout.encode('utf-8'),immutable=True)
    atomic(out/'CONTROL_SELFTEST.stderr.txt',tested.stderr.encode('utf-8'),immutable=True)
    atomic(out/'CONTROL_SELFTEST.rc.txt',(str(tested.returncode)+'\n').encode(),immutable=True)
    atomic(out/'RESULT.json',w.encoded(result),immutable=True);s=w.sha(out/'RESULT.json');w.atomic=atomic
    w.sync('latest_m443_single_layer_support01',dict(status=result['status'],result=(out/'RESULT.json').relative_to(w.ROOT).as_posix(),sha256=s,manifest_sha256=prep['manifest_sha256']),
           '## M443单层支持组件检查01（2026-10-11）\n\nSHA '+s+'；实际新配置wrapper未证明时拒绝分配、精确Overlay调用/正例及未知保留对象路径核对；显式旧raw派生collector PASS/未知FAIL及'+str(len(negatives))+'破坏负例；PowerShell原stdout/stderr/rc0及失败仍采集检查通过。只离线组件，不是新板端数值。冻结所有31包文件/控制/原decoder SHA，下一步新目录逐SHA上传/精确旧文件复制完整白名单后一次单层。')
    print(result['status'],s,'negative_checks',len(negatives))


def receipt():
    logs=w.ROOT/'tmp/m443_layer01';a=logs/'assembly.log';s=logs/'upload_syntax.log'
    assert 'M443L_ALL_PAYLOAD_SHA_VERIFIED_NO_GATE' in a.read_text(encoding='utf-8-sig') and '__M443L_ASSEMBLY_RC_0__' in a.read_text(encoding='utf-8-sig')
    assert '__M443L_SYNTAX_RC_0__' in s.read_text(encoding='utf-8-sig')
    out=w.BASE/'runs/M443-single-layer-transfer-01'
    result=dict(status='PASS_M443_SINGLE_LAYER_TRANSFER_ONLY01',manifest_sha256=w.sha(c.PKG/'PACKAGE_MANIFEST.json'),
                logs=[dict(path=p.relative_to(w.ROOT).as_posix(),bytes=p.stat().st_size,sha256=w.sha(p)) for p in sorted(logs.glob('*.log'))],
                assembly_whole_whitelist_verified=True,bash_n_pass=True,board_executed=False,overlay_loaded=False,numerical_pass=False,performance_pass=False)
    atomic(out/'RESULT.json',w.encoded(result),immutable=True);digest=w.sha(out/'RESULT.json');w.atomic=atomic
    w.sync('latest_m443_single_layer_transfer01',dict(status=result['status'],result=(out/'RESULT.json').relative_to(w.ROOT).as_posix(),sha256=digest,manifest_sha256=result['manifest_sha256']),
           '## M443单层包传输01（2026-10-11）\n\nSHA '+digest+'；manifest先发900B分块，所有新增文件逐SHA，旧M441和新M443已有文件及原BuildID/chain证据仅精确SHA复制；整体31成员白名单核对及root bash-n rc0，无Overlay/单层执行。下一步仅Run一次单层，有attempt只Collect。')
    print(result['status'],digest)


if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='receipt':receipt()
    else:fixtures()
