"""Verify clean-stage component and strict collector; fake records are explicit."""
import ast,base64,copy,hashlib,json,subprocess
from m351_workflow import ROOT,BASE,HERE,sha,atomic,encoded,sync
from m424_environment_workflow import PKG,decode


def main():
    outdir=BASE/'runs/M424-environment-support-02'
    if outdir.exists():raise RuntimeError('Original support exists')
    outdir.mkdir(parents=True)
    stage=ROOT/'tmp/m424environment/component_stage';linux='/mnt/c/'+stage.relative_to(ROOT.anchor).as_posix()
    code=f"import runpy,sys;sys.path.insert(0,{linux!r});runpy.run_path({(linux+'/test_m424_environment.py')!r},run_name='__main__')"
    p=subprocess.run(['wsl.exe','-d','Ubuntu-24.04','--','/home/lyy/projects/qwen_baseline/.venv/bin/python','-I','-B','-c',code],capture_output=True)
    atomic(outdir/'component.stdout.bin',p.stdout,immutable=True);atomic(outdir/'component.stderr.bin',p.stderr,immutable=True)
    if p.returncode or b'M424_FAKE_SYSFS_COMPONENT_PASS rejects=8' not in p.stdout:raise RuntimeError('Component rejected; raw streams preserved')
    try:stderr=p.stderr.decode('utf-8');stderr_encoding='utf-8'
    except UnicodeDecodeError:
        # Never guess the Windows/WSL warning's character encoding.
        # Preserve the full bytes and an explicitly uninterpreted hex display.
        stderr=p.stderr.hex();stderr_encoding='uninterpreted-raw-hex'
    env=json.loads((BASE/'runs/M404-environment-board-01/BOARD_RESULT.json').read_bytes())['environment']
    expected=json.loads((PKG/'AMS_EXPECTED.json').read_bytes())
    env['thermal_zones']={}
    for name in expected['inputs']:
        env['thermal_zones']['ams/'+name]=dict(type='ams:iio_hwmon:'+name,temperature_mC=31000,
                    source=expected['path']+'/'+name,resolved_path=expected['resolved_path']+'/'+name,
                    units='millidegree_Celsius',anatomical_channel_mapping_proven=False)
    env.update(observability_issues=[],temperature_channel_mapping_proven=False)
    r=dict(status='PASS_M424_READONLY_ENVIRONMENT_OBSERVABLE',gate_return_code=0,errors=[],
           manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),overlay_loaded=False,model_forward_calls=0,
           dma_allocations=0,fpga_transactions=0,cache_changes=False,performance_pass=False,
           throttling_absence_proven=False,environment=env,elapsed_s=.01)
    def export(row):
        raw=encoded(row);parts=[raw[i:i+900] for i in range(0,len(raw),900)]
        return 'M424_ENV_SHA256='+hashlib.sha256(raw).hexdigest()+'\n'+''.join(f'M424_ENV_CHUNK={i}/{len(parts)}:'+base64.b64encode(p).decode('ascii')+'\n' for i,p in enumerate(parts))+f'M424_ENV_DONE gate_rc={row["gate_return_code"]}\n'
    assert decode(export(r))[2]==r
    failed=dict(r,status='FAIL_M424_ENVIRONMENT_OBSERVABILITY',gate_return_code=1,errors=['intentional observation failure'])
    assert decode(export(failed))[2]==failed
    negatives=[]
    for k,v in [('gate_return_code',1),('overlay_loaded',True),('model_forward_calls',1),('performance_pass',True),('throttling_absence_proven',True),('elapsed_s',16),('manifest_sha256','0'*64),('errors',['bad'])]:negatives.append(export(dict(r,**{k:v})))
    for k,v in [('units','raw'),('source','/wrong'),('resolved_path','/wrong'),('anatomical_channel_mapping_proven',True),('temperature_mC',150001)]:
        bad=copy.deepcopy(r);bad['environment']['thermal_zones']['ams/temp1_input'][k]=v;negatives.append(export(bad))
    bad=copy.deepcopy(r);bad['environment']['thermal_zones'].pop('ams/temp3_input');negatives.append(export(bad))
    good=export(r);negatives.extend([good.replace('M424_ENV_CHUNK=1/','M424_ENV_CHUNK=0/'),good.replace('M424_ENV_DONE gate_rc=0','M424_ENV_DONE gate_rc=1'),good+'M424_ENV_SHA256='+'0'*64+'\n',good.split('M424_ENV_CHUNK=1/')[0]])
    for s in negatives:
        try:decode(s)
        except (ValueError,KeyError):pass
        else:raise AssertionError('Bad collector fixture accepted')
    for n in ('m424_environment.py','m424_environment_probe.py','m424_environment_workflow.py'):ast.parse((HERE/n).read_text(encoding='utf-8'),feature_version=(3,10))
    ctrl=subprocess.run([r'C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell\pwsh.exe','-NoProfile','-File',str(HERE/'m424_environment_control.ps1'),'-Mode','SelfTest'],capture_output=True)
    atomic(outdir/'control.stdout.bin',ctrl.stdout,immutable=True);atomic(outdir/'control.stderr.bin',ctrl.stderr,immutable=True)
    if ctrl.returncode or b'M424_ENV_CONTROL_SELF_TEST_PASS' not in ctrl.stdout:raise RuntimeError('Controller selftest failed')
    runner_linux='/mnt/c/'+(PKG/'run_m424_environment.sh').relative_to(ROOT.anchor).as_posix()
    shell=subprocess.run(['wsl.exe','-d','Ubuntu-24.04','--','bash','-n',runner_linux],capture_output=True)
    atomic(outdir/'bash.stderr.bin',shell.stderr,immutable=True)
    if shell.returncode:raise RuntimeError('Runner syntax failed')
    result=dict(status='PASS_OFFLINE_M424_ENVIRONMENT_COMPONENT_COLLECTOR_CONTROL',
                manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),
                component_stdout_sha256=sha(outdir/'component.stdout.bin'),component_stderr_sha256=sha(outdir/'component.stderr.bin'),
                component_stderr_encoding=stderr_encoding,component_stderr=stderr,
                component_rerun_reason='Prior host subprocess text reader raised UnicodeDecodeError on WSL stderr; raw byte capture resolves the unread stream. No board repetition.',
                fake_sysfs_component=True,synthetic_collector_records=True,collector_negative_checks=len(negatives),
                original_failure_rc_preserved=True,control_intentional_failure_collect_selftest=True,
                bash_syntax_pass=True,Python310_syntax_pass=True,board_run=False,performance_pass=False,
                source_sha256={n:sha(HERE/n) for n in ('m424_environment_workflow.py','m424_environment_control.ps1','m424_environment_support.py')})
    out=outdir/'RESULT.json';atomic(out,encoded(result),immutable=True)
    sync('latest_m424_environment_support',dict(status=result['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out),manifest_sha256=result['manifest_sha256']),
         f'## M424 已处理温度控制/回收检查（2026-10-06）\n\nSHA {sha(out)}；8 fake sysfs拒绝、{len(negatives)}合成回收负例及故意失败收集/rc保留、Python3.10/bash-n通过。'
         '首准备调用WSL stderr文本解码出现UnicodeDecodeError，旧准备保留；本次仅重做该离线组件边界并完整保存stdout/stderr原字节，未重跑板端。'
         '同manifest和原目录身份，0Overlay/模型/FPGA；允许一次CPU只读观察，不是暖请求或性能PASS。')
    print('M424_ENV_SUPPORT_SYNC',sha(out),len(negatives))


if __name__=='__main__':main()
