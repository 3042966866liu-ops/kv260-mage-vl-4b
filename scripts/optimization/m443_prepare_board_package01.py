"""Fresh exact M443 lower-gate hardware package. No transfer or board execution."""
import ast,json,re,sys
from pathlib import Path
import m351_workflow as w
from m441_host_io08 import atomic
from m443_transfer import verify_directory
PKG=w.BASE/'candidates/M443-pair-pipeline-01'
BOOT=w.BASE/'candidates/M443-transfer-bootstrap-01'
RUN=w.BASE/'runs/M443-board-package-preparation-01'
def manifest(directory,schema):
    rows=[dict(path=p.relative_to(directory).as_posix(),bytes=p.stat().st_size,sha256=w.sha(p)) for p in sorted(directory.rglob('*')) if p.is_file()]
    spec=dict(schema=schema,files=rows,file_count=len(rows),total_bytes=sum(x['bytes'] for x in rows))
    atomic(directory/'PACKAGE_MANIFEST.json',w.encoded(spec),immutable=True);s=w.sha(directory/'PACKAGE_MANIFEST.json')
    verify_directory(directory,s);return spec,s
def main():
    assert not PKG.exists() and not BOOT.exists() and not RUN.exists(),'Fresh staging required'
    names=[
      ('M443-full-shell-04','PASS_M443_FULL_SHELL_ROUTED_TIMING04'),
      ('M443-pair-pipeline-core-OOC-closure-03','PASS_M443_SAME_CONSTRAINT_CORE_ROUTED_TIMING'),
      ('M443-full-numeric-csim-03','PASS_M443_FULL_REAL_WEIGHT_CHAIN_CSIM03'),
      ('M443-W2-W4-pair-pipeline-RTL-04','PASS_M441_W2_W4_SUPPLEMENTAL_SIMULATION_CLOSED19'),
      ('M443-board-support-preparation-01','PREPARED_M443_FROZEN_FIXTURES_AND_CONFIGURATION_CONTRACT01'),
      ('M443-board-controls-preparation-01','PREPARED_M443_DISABLED_LOWER_CONTROLS01_UNTESTED'),
      ('M443-board-controls-checks-01','PASS_M443_ACTUAL_LOWER_CONTROL_AND_TRANSFER_FIXTURES01')]
    proofs=[];data={}
    for name,status in names:
        p=w.BASE/'runs'/name/'RESULT.json';d=json.loads(p.read_bytes());s=w.sha(p);assert d['status']==status
        for n in ('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'):assert s in (w.ROOT/n).read_text(encoding='utf-8-sig')
        data[name]=d;proofs.append(dict(path=p.relative_to(w.ROOT).as_posix(),sha256=s,status=status))
    shell=data[names[0][0]];assert all(shell['checks'].values()) and not shell['errors']
    for row in shell['artifacts']:assert w.sha(w.ROOT/row['path'])==row['sha256']
    for name in [x[0] for x in names[4:]]:
        for row in data[name]['files']:assert w.sha(w.ROOT/row['path'])==row['sha256']
    assert all(x['rc']==0 for x in data[names[-1][0]]['checks'])
    header=w.BASE/'runs/M443-pair-pipeline-preparation-03/RESULT.json';headers=json.loads(header.read_bytes())
    for row in headers['files']:assert w.sha(w.ROOT/row['path'])==row['sha256']
    recursive=[];seen=set();missing=[]
    def visit(path):
        path=path.resolve()
        if path in seen:return
        seen.add(path);recursive.append(dict(path=path.relative_to(w.ROOT).as_posix(),sha256=w.sha(path)))
        for name in re.findall(r'(?m)^\s*#\s*include\s*"([^"]+)"',path.read_text(encoding='utf-8')):
            child=(path.parent/name).resolve()
            if child.is_file():visit(child)
            else:missing.append(dict(source=path.relative_to(w.ROOT).as_posix(),include=name))
    for row in headers['files']:
        if row['path'].endswith(('.cpp','.hpp','.h')):visit(w.ROOT/row['path'])
    assert not missing,missing
    oldprep=json.loads((w.BASE/'runs/M441-board-package-preparation-01/RESULT.json').read_bytes())
    old=w.ROOT/oldprep['package_path'];verify_directory(old,oldprep['manifest_sha256'])
    copies={}
    foundation=w.ROOT/'tmp/m443_board_support_01'
    for row in data[names[4][0]]['files']:
        p=w.ROOT/row['path'];copies[p.relative_to(foundation).as_posix()]=p
    for name in ('board_safety.py','owned_buffer_release.py','measurement.py','m341_build_id_gate.py','m120_board_common.py','m120_board_env_preflight.py'):copies[name]=old/name
    controls=w.ROOT/'tmp/m443_board_controls_01'
    for name in ('m443_configuration01.py','m443_board_probe.py','m443_gate_runner.sh','m443_export_result.py','m443_completion_observer.py','m443_comparison.py'):copies[name]=controls/name
    python={Path(n).stem:p for n,p in copies.items() if n.endswith('.py')};missing_python=[];edges=[]
    external={'numpy','pynq','board_runtime'};standard=set(sys.stdlib_module_names)|{'fcntl'}
    for name,p in python.items():
        for node in ast.walk(ast.parse(p.read_bytes(),feature_version=(3,10))):
            modules=[x.name.split('.')[0] for x in node.names] if isinstance(node,ast.Import) else ([node.module.split('.')[0]] if isinstance(node,ast.ImportFrom) and node.module else [])
            for module in modules:
                if module in python:edges.append(dict(source=name,module=module,sha256=w.sha(python[module])))
                elif module not in standard and module not in external:missing_python.append(dict(source=name,module=module))
    assert not missing_python,missing_python
    PKG.mkdir(parents=True)
    for name,p in copies.items():
        assert p.is_file() and not p.is_symlink() and not any(x in name for x in ('__pycache__','.pyc','.log'))
        atomic(PKG/name,p.read_bytes(),immutable=True)
    for row in proofs:
        p=w.ROOT/row['path'];atomic(PKG/'evidence'/p.parent.name/p.name,p.read_bytes(),immutable=True)
    dep=dict(status='PASS_RECURSIVE_FROZEN_DEPENDENCY_CLOSURE',header_preparation_sha256=w.sha(header),recursive_headers=recursive,
        missing_headers=missing,python_edges=edges,missing_python=missing_python,
        external_modules=['PYNQ venv Python stdlib','numpy','pynq'],external_stable_runtime=json.loads((PKG/'BOARD_CASES.json').read_bytes())['stable_sources'],
        copied_files=[dict(path=n,sha256=w.sha(PKG/n),source_path=p.relative_to(w.ROOT).as_posix(),source_sha256=w.sha(p)) for n,p in sorted(copies.items())])
    atomic(PKG/'DEPENDENCY_CLOSURE.json',w.encoded(dep),immutable=True)
    from m443_configuration01 import BIT,SHELL,validate_application
    validate_application(json.loads((PKG/'CONFIGURATION_APPLICATION.json').read_bytes()))
    assert w.sha(PKG/'overlay/m120_m89x2_t32.bit')==BIT and proofs[0]['sha256']==SHELL
    assert w.sha(PKG/'baseline/overlay/m120_m89x2_t32.bit')=='73350f615a5bc98d1d8aa2b5c69c4d6fd399aa1ef651f37411cbed21c0daed2e'
    closure=dict(status='PASS_ALL_NEW_CIRCUIT_PREREQUISITES',build_id='0x4D343433',baseline_build_id='0x4D343431',stable_build_id='0x4D395832',prerequisites=proofs,
        baseline_manifest_sha256=oldprep['manifest_sha256'],baseline_bit_sha256=w.sha(PKG/'baseline/overlay/m120_m89x2_t32.bit'),candidate_bit_sha256=BIT,shell_closure_sha256=SHELL,
        change='Independent four-pair 64-input II1 MAC, depth34 and original FP32 order; original parser for eventual hardware comparison.',
        retained_strict_shell03_failure_sha256='17783ff1dd8ed80c434555f79102110de945cd8396596057a7cb08d24815e4e1',
        extra_PS_slots=0,extra_CMA_banks=0,seven_owner_policy_unchanged=True,PS_budget_unchanged=True,
        configuration_application_accepted=False,configuration_credits_granted=0,board_pass=False,model_pass=False,video_pass=False,promoted=False)
    atomic(PKG/'HARDWARE_CLOSURE.json',w.encoded(closure),immutable=True);spec,digest=manifest(PKG,'m443-independent-pair-pipeline-candidate-v1')
    rows=[dict(path='PACKAGE_MANIFEST.json',bytes=(PKG/'PACKAGE_MANIFEST.json').stat().st_size,sha256=digest)]+spec['files']
    transport=dict(schema='m443-specific-peer-transfer-v1',package_manifest_sha256=digest,files=rows,file_count=len(rows),total_bytes=sum(r['bytes'] for r in rows))
    BOOT.mkdir(parents=True);atomic(BOOT/'m443_transfer.py',(w.HERE/'m443_transfer.py').read_bytes(),immutable=True);atomic(BOOT/'TRANSPORT_MANIFEST.json',w.encoded(transport),immutable=True)
    oldboot=w.ROOT/oldprep['bootstrap_path']
    runner=(oldboot/'run_m441_transfer.sh').read_text(encoding='utf-8').replace('m441','m443').replace('M441','M443')
    atomic(BOOT/'run_m443_transfer.sh',runner.encode(),immutable=True);_,bootdigest=manifest(BOOT,'m443-transfer-bootstrap-v1')
    result=dict(status='PREPARED_NEW_CIRCUIT_BOARD_PACKAGE_AFTER_ALL_GATES',build_id='0x4D343433',baseline_build_id='0x4D343431',
        package_path=PKG.relative_to(w.ROOT).as_posix(),manifest_sha256=digest,package_files=spec['file_count'],package_bytes=spec['total_bytes'],
        bootstrap_path=BOOT.relative_to(w.ROOT).as_posix(),bootstrap_manifest_sha256=bootdigest,transport_manifest_sha256=w.sha(BOOT/'TRANSPORT_MANIFEST.json'),
        dependency_closure_sha256=w.sha(PKG/'DEPENDENCY_CLOSURE.json'),missing_headers=0,missing_python=0,prerequisites=proofs,
        files=[dict(path=x.relative_to(w.ROOT).as_posix(),sha256=w.sha(x)) for directory in (PKG,BOOT) for x in sorted(directory.rglob('*')) if x.is_file()],
        preparer_sha256=w.sha(Path(__file__)),board=False,promoted=False,configuration_application_accepted=False,configuration_credits_granted=0,
        next_step='COM3 sameTTY sudo, exact bootstrap and bounded specific-peer transfer. BuildID only with actual new-bit samePID/PFN CMA observation.')
    atomic(RUN/'RESULT.json',w.encoded(result),immutable=True);w.atomic=atomic;s=w.sha(RUN/'RESULT.json')
    w.sync('latest_m443_board_package_preparation01',dict(status=result['status'],result=(RUN/'RESULT.json').relative_to(w.ROOT).as_posix(),sha256=s,build_id=result['build_id'],manifest_sha256=digest,board=False),
        '## M443独立干净板端包01（2026-10-11）\n\nSHA '+s+'；manifest '+digest+'；'+str(spec['file_count'])+'文件/'+str(spec['total_bytes'])+'字节；原递归头及Python依赖missing=0、逐SHA及白名单完整复核。新M443 bit/HWH、精确M441 baseline、原完整Q/gate_up/down参考与禁默认执行低级probe。原严格shell03失败保留，独立shell04/组件fixture已门禁；尚未传输/Overlay/配置实证，0credit/0板端数值或性能/0晋级。下一步指定peer有界传输/地址恢复后COM3先BuildID及新bit同PID/PFN1904页配置释放申请。')
    print(result['status'],s,digest,spec['file_count'],spec['total_bytes'])
if __name__=='__main__':main()
