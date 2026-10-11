"""Execute actual assembler and transfer checker on self-owned fixtures only."""
import contextlib
import copy
import io
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from unittest.mock import patch
from m351_workflow import ROOT, BASE, HERE, atomic, encoded, sha, sync
import m437_workflow as w


def main():
    b=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    e=b['latest_m437_support'];assert sha(ROOT/e['result'])==e['sha256']
    pkg=w.PKG;old=BASE/'candidates/M433-late11-complete-request-warm-01';digest=sha(pkg/'PACKAGE_MANIFEST.json')
    m=json.loads((pkg/'PACKAGE_MANIFEST.json').read_bytes());old_m=json.loads((old/'PACKAGE_MANIFEST.json').read_bytes())
    byname={x['path']:x for x in old_m['files']}
    expected=['PACKAGE_MANIFEST.json']+[x['path'] for x in m['files'] if byname.get(x['path'])!=x]
    assert w.upload_names()==expected and expected[0]=='PACKAGE_MANIFEST.json'
    rejected=[]
    def reject(name, fn):
        try:fn()
        except (RuntimeError,ValueError,AssertionError,OSError,KeyError):rejected.append(name)
        else:raise AssertionError('Invalid assembly/transfer accepted:'+name)
    with tempfile.TemporaryDirectory(dir=ROOT/'tmp',prefix='m437-transfer-') as temporary:
        folder=Path(temporary);src=folder/'old';dst=folder/'candidate'
        shutil.copytree(old,src);dst.mkdir()
        for name in expected:shutil.copyfile(pkg/name,dst/name)
        original=(pkg/'m437_assemble.py').read_text(encoding='utf-8')
        assert original.count("Path('/home/ubuntu/m433_late11_warm_candidate_01')")==1
        assembly=original.replace("Path('/home/ubuntu/m433_late11_warm_candidate_01')",'Path('+repr(src.as_posix())+')')
        def assemble():
            with patch.object(sys,'argv',[str(dst/'m437_assemble.py'),digest]),contextlib.redirect_stdout(io.StringIO()):
                exec(compile(assembly,str(pkg/'m437_assemble.py'),'exec'),dict(__file__=str(dst/'m437_assemble.py'),__name__='explicit_local_assembly_fixture'))
        assemble()
        assert {p.name:sha(p) for p in dst.iterdir()}=={p.name:sha(p) for p in pkg.iterdir()}
        changed=next(name for name in expected if name not in ('PACKAGE_MANIFEST.json','m437_assemble.py'))
        payload=(dst/changed).read_bytes();(dst/changed).unlink()
        reject('changed-file-not-old-source',assemble);(dst/changed).write_bytes(payload)
        extra=dst/'unexpected.log';extra.write_text('explicit extra file',encoding='utf-8');reject('path-whitelist-extra',assemble);extra.unlink()
        p=src/old_m['files'][0]['path'];saved=p.read_bytes();p.write_bytes(saved+b'bad');reject('old-payload-SHA',assemble);p.write_bytes(saved)
        p=dst/changed;p.write_bytes(payload+b'bad');reject('final-payload-SHA',assemble);p.write_bytes(payload)
        # Actual transfer function sees only bounded fixture logs and sandbox result/sync.
        pseudo=folder/'root';logs=pseudo/'tmp/m43701/board';logs.mkdir(parents=True)
        old_manifest=pseudo/'deployment/mage_vl4b/optimization_v1/candidates/M433-late11-complete-request-warm-01/PACKAGE_MANIFEST.json'
        old_manifest.parent.mkdir(parents=True)
        shutil.copyfile(old/'PACKAGE_MANIFEST.json',old_manifest)
        for name in expected:
            size=(pkg/name).stat().st_size;count=(size+899)//900;prefix='upload_'+name.replace('.','_')
            (logs/(prefix+'_final.log')).write_text('M212_CHUNKED_FILE_PASS '+sha(pkg/name)+'\n',encoding='utf-8')
            for i in range(1,count+1):
                (logs/f'{prefix}_chunk_{i:06d}.log').write_text(f'M212_CHUNK_PASS {i} {count} {min(i*900,size)} fixture\n',encoding='utf-8')
        (logs/'assembly.log').write_text(f'M437_ASSEMBLY_PASS {digest} {m["file_count"]} {m["total_bytes"]}\n',encoding='utf-8')
        (logs/'syntax.log').write_text('__M437_SYNTAX_RC_0__\n',encoding='utf-8')
        notes=[]
        def transfer():
            with patch.object(w,'ROOT',pseudo),patch.object(w,'BASE',pseudo/'deployment/mage_vl4b/optimization_v1'),patch.object(w,'sync',lambda *args:notes.append(args)),contextlib.redirect_stdout(io.StringIO()):w.transfer()
        transfer()
        out=pseudo/'deployment/mage_vl4b/optimization_v1/runs/M437-natural-IO-transfer-01/RESULT.json'
        r=json.loads(out.read_bytes());assert [x['path'] for x in r['receipts']]==expected and notes[0][0]=='latest_m437_natural_IO_transfer'
        chunk=next(logs.glob('upload_PACKAGE_MANIFEST_json_chunk_*.log'));raw=chunk.read_bytes();chunk.unlink();reject('missing-upload-chunk',transfer);chunk.write_bytes(raw)
        chunk.write_text('M212_CHUNK_PASS 999 999 1 bad\n',encoding='utf-8');reject('bad-upload-order',transfer);chunk.write_bytes(raw)
        final=logs/'upload_PACKAGE_MANIFEST_json_final.log';raw=final.read_bytes();final.write_text('M212_CHUNKED_FILE_PASS '+'0'*64+'\n',encoding='utf-8');reject('bad-upload-full-SHA',transfer);final.write_bytes(raw)
        p=logs/'syntax.log';raw=p.read_bytes();p.write_text('__M437_SYNTAX_RC_1__\n',encoding='utf-8');reject('bad-bash-n',transfer);p.write_bytes(raw)
        p=logs/'assembly.log';raw=p.read_bytes();p.write_text('M437_ASSEMBLY_PASS wrong\n',encoding='utf-8');reject('bad-final-assembly',transfer);p.write_bytes(raw)
        # Also execute the actual PowerShell delta expression, not a Python-only equivalent.
        script=folder/'delta.ps1'
        script.write_text("$ErrorActionPreference='Stop'\n$manifest=Get-Content -Raw -Encoding UTF8 -LiteralPath '"+(pkg/'PACKAGE_MANIFEST.json').as_posix()+"' | ConvertFrom-Json\n$old=Get-Content -Raw -Encoding UTF8 -LiteralPath '"+(old/'PACKAGE_MANIFEST.json').as_posix()+"' | ConvertFrom-Json\n$delta=@($manifest.files | Where-Object { $item=$_; -not @($old.files | Where-Object { $_.path -eq $item.path -and $_.sha256 -eq $item.sha256 -and $_.bytes -eq $item.bytes }).Count } | ForEach-Object path)\nConvertTo-Json -Compress -InputObject (@('PACKAGE_MANIFEST.json')+$delta)\n",encoding='utf-8')
        ps='C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe'
        cp=subprocess.run([ps,'-NoProfile','-File',str(script)],capture_output=True,text=True,encoding='utf-8')
        if cp.returncode or json.loads(cp.stdout)!=expected:raise RuntimeError('Actual PowerShell selection differs')
    import ast
    from pathlib import PurePosixPath
    control=(HERE/'m437_control02.ps1').read_text(encoding='utf-8')
    candidate='/home/ubuntu/m437_natural_IO_candidate_01';evidence='/home/ubuntu/m437_natural_IO_result_01'
    assert candidate!=evidence and not PurePosixPath(candidate).is_relative_to(PurePosixPath(evidence)) and not PurePosixPath(evidence).is_relative_to(PurePosixPath(candidate))
    assert f"$remote='{candidate}'" in control
    gate_ast=ast.parse((pkg/'m437_gate.py').read_text(encoding='utf-8'))
    main_fn=next(n for n in gate_ast.body if isinstance(n,ast.FunctionDef) and n.name=='main')
    assignments=[n for n in main_fn.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='EVIDENCE' for t in n.targets)]
    assert len(assignments)==1 and ast.literal_eval(assignments[0].value.args[0])==evidence
    exp=next(n for n in ast.parse((pkg/'m437_export.py').read_text(encoding='utf-8')).body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='OUTPUT' for t in n.targets))
    assert ast.literal_eval(exp.value.args[0])==evidence+'/BOARD_RESULT.json'
    runner=(pkg/'run_m437.sh').read_text(encoding='utf-8')
    assert f'[[ ! -e {evidence} ]] || exit 67' in runner
    assert 'Collect' in runner and 'M437_ENABLE_INTEGRATED_VIDEO' in runner
    assert '1600' in control and '5100' in control
    assert w.OUT==BASE/'runs/M437-natural-IO-board-01/BOARD_RESULT.json'
    closure=json.loads((pkg/'DEPENDENCY_CLOSURE.json').read_bytes())
    assert not closure['missing'] and all(closure['files'][p.stem]==sha(p) for p in pkg.glob('*.py'))
    assert sha(pkg/'m433_timed_visual.py')==sha(old/'m433_timed_visual.py')
    assert sha(pkg/'m433_light_policy.py')==sha(old/'m433_light_policy.py')
    assert not any(p.name in ('m435_io_observer.py','m425_warm.py') for p in pkg.iterdir())
    cp=subprocess.run([ps,'-NoProfile','-File',str(HERE/'m437_control02.ps1'),'-Mode','SelfTest'],capture_output=True)
    assert cp.returncode==0 and b'M437_CONTROL_SELF_TEST_PASS' in cp.stdout
    record=dict(status='PASS_M437_ROUTE_ASSEMBLY_TRANSFER_SUPPORT_ONLY',manifest_sha256=digest,
        candidate_remote=candidate,evidence_remote=evidence,actual_assembly=True,actual_transfer_receipts=True,
        actual_PowerShell_delta=True,actual_route_AST=True,original_provider_and_policy_unchanged=True,
        local_dependency_SHA_complete=True,negative_checks=rejected,
        support_sha256=e['sha256'],host_sources={n:sha(HERE/n) for n in ('m437_control02.ps1','m437_workflow.py','m437_sequence.py','m437_transfer_support.py')},
        fixtures_explicitly_synthetic=True,board_run=False,performance_pass=False,temperature_measurement_enabled=False)
    p=BASE/'runs/M437-transfer-support-01/RESULT.json';atomic(p,encoded(record),immutable=True)
    sync('latest_m437_transfer_support',dict(status=record['status'],result=p.relative_to(ROOT).as_posix(),sha256=sha(p),manifest_sha256=digest),
        f'## M437 独立路径与实际组装传输配套（2026-10-07）\n\nSHA {sha(p)}；真实assembler同SHA白名单、实际PowerShell增量选择和host transfer回执/最终BOARD键、{len(rejected)}缺失/乱序/SHA/额外文件负例通过。actual gate/export/runner/control四路径严格独立，全部local依赖SHA，原provider/policy字节不改。02仅增收集预算至1600s覆盖4MiB原900B协议并强制本支持；Run5100s。0板端/性能，唯一下一步同COM3一次sudo、manifest-first上传及固定4＋8执行；已有run或raw只Collect，不测温。')
    print('M437_TRANSFER_SUPPORT_SYNC',sha(p),len(rejected))


if __name__=='__main__':main()
