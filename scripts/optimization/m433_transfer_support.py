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
import m433_workflow as w


def main():
    b=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    e=b['latest_m433_performance_support'];assert sha(ROOT/e['result'])==e['sha256']
    pkg=w.PKG;old=BASE/'candidates/M432-late11-integrated-video-02';digest=sha(pkg/'PACKAGE_MANIFEST.json')
    m=json.loads((pkg/'PACKAGE_MANIFEST.json').read_bytes());old_m=json.loads((old/'PACKAGE_MANIFEST.json').read_bytes())
    byname={x['path']:x for x in old_m['files']}
    expected=['PACKAGE_MANIFEST.json']+[x['path'] for x in m['files'] if byname.get(x['path'])!=x]
    assert w.upload_names()==expected and expected[0]=='PACKAGE_MANIFEST.json'
    rejected=[]
    def reject(name, fn):
        try:fn()
        except (RuntimeError,ValueError,AssertionError,OSError,KeyError):rejected.append(name)
        else:raise AssertionError('Invalid assembly/transfer accepted:'+name)
    with tempfile.TemporaryDirectory(dir=ROOT/'tmp',prefix='m433-transfer-') as temporary:
        folder=Path(temporary);src=folder/'old';dst=folder/'candidate'
        shutil.copytree(old,src);dst.mkdir()
        for name in expected:shutil.copyfile(pkg/name,dst/name)
        original=(pkg/'m433_assemble.py').read_text(encoding='utf-8')
        assert original.count("Path('/home/ubuntu/m432_late11_integrated_candidate_02')")==1
        assembly=original.replace("Path('/home/ubuntu/m432_late11_integrated_candidate_02')",'Path('+repr(src.as_posix())+')')
        def assemble():
            with patch.object(sys,'argv',[str(dst/'m433_assemble.py'),digest]),contextlib.redirect_stdout(io.StringIO()):
                exec(compile(assembly,str(pkg/'m433_assemble.py'),'exec'),dict(__file__=str(dst/'m433_assemble.py'),__name__='explicit_local_assembly_fixture'))
        assemble()
        assert {p.name:sha(p) for p in dst.iterdir()}=={p.name:sha(p) for p in pkg.iterdir()}
        changed=next(name for name in expected if name not in ('PACKAGE_MANIFEST.json','m433_assemble.py'))
        payload=(dst/changed).read_bytes();(dst/changed).unlink()
        reject('changed-file-not-old-source',assemble);(dst/changed).write_bytes(payload)
        extra=dst/'unexpected.log';extra.write_text('explicit extra file',encoding='utf-8');reject('path-whitelist-extra',assemble);extra.unlink()
        p=src/old_m['files'][0]['path'];saved=p.read_bytes();p.write_bytes(saved+b'bad');reject('old-payload-SHA',assemble);p.write_bytes(saved)
        p=dst/changed;p.write_bytes(payload+b'bad');reject('final-payload-SHA',assemble);p.write_bytes(payload)
        # Actual transfer function sees only bounded fixture logs and sandbox result/sync.
        pseudo=folder/'root';logs=pseudo/'tmp/m43301/board';logs.mkdir(parents=True)
        old_manifest=pseudo/'deployment/mage_vl4b/optimization_v1/candidates/M432-late11-integrated-video-02/PACKAGE_MANIFEST.json'
        old_manifest.parent.mkdir(parents=True)
        shutil.copyfile(old/'PACKAGE_MANIFEST.json',old_manifest)
        for name in expected:
            size=(pkg/name).stat().st_size;count=(size+899)//900;prefix='upload_'+name.replace('.','_')
            (logs/(prefix+'_final.log')).write_text('M212_CHUNKED_FILE_PASS '+sha(pkg/name)+'\n',encoding='utf-8')
            for i in range(1,count+1):
                (logs/f'{prefix}_chunk_{i:06d}.log').write_text(f'M212_CHUNK_PASS {i} {count} {min(i*900,size)} fixture\n',encoding='utf-8')
        (logs/'assembly.log').write_text(f'M433_ASSEMBLY_PASS {digest} {m["file_count"]} {m["total_bytes"]}\n',encoding='utf-8')
        (logs/'syntax.log').write_text('__M433_SYNTAX_RC_0__\n',encoding='utf-8')
        notes=[]
        def transfer():
            with patch.object(w,'ROOT',pseudo),patch.object(w,'BASE',pseudo/'deployment/mage_vl4b/optimization_v1'),patch.object(w,'sync',lambda *args:notes.append(args)),contextlib.redirect_stdout(io.StringIO()):w.transfer()
        transfer()
        out=pseudo/'deployment/mage_vl4b/optimization_v1/runs/M433-performance-transfer-01/RESULT.json'
        r=json.loads(out.read_bytes());assert [x['path'] for x in r['receipts']]==expected and notes[0][0]=='latest_m433_performance_transfer'
        chunk=next(logs.glob('upload_PACKAGE_MANIFEST_json_chunk_*.log'));raw=chunk.read_bytes();chunk.unlink();reject('missing-upload-chunk',transfer);chunk.write_bytes(raw)
        chunk.write_text('M212_CHUNK_PASS 999 999 1 bad\n',encoding='utf-8');reject('bad-upload-order',transfer);chunk.write_bytes(raw)
        final=logs/'upload_PACKAGE_MANIFEST_json_final.log';raw=final.read_bytes();final.write_text('M212_CHUNKED_FILE_PASS '+'0'*64+'\n',encoding='utf-8');reject('bad-upload-full-SHA',transfer);final.write_bytes(raw)
        p=logs/'syntax.log';raw=p.read_bytes();p.write_text('__M433_SYNTAX_RC_1__\n',encoding='utf-8');reject('bad-bash-n',transfer);p.write_bytes(raw)
        p=logs/'assembly.log';raw=p.read_bytes();p.write_text('M433_ASSEMBLY_PASS wrong\n',encoding='utf-8');reject('bad-final-assembly',transfer);p.write_bytes(raw)
        # Also execute the actual PowerShell delta expression, not a Python-only equivalent.
        script=folder/'delta.ps1'
        script.write_text("$ErrorActionPreference='Stop'\n$manifest=Get-Content -Raw -Encoding UTF8 -LiteralPath '"+(pkg/'PACKAGE_MANIFEST.json').as_posix()+"' | ConvertFrom-Json\n$old=Get-Content -Raw -Encoding UTF8 -LiteralPath '"+(old/'PACKAGE_MANIFEST.json').as_posix()+"' | ConvertFrom-Json\n$delta=@($manifest.files | Where-Object { $item=$_; -not @($old.files | Where-Object { $_.path -eq $item.path -and $_.sha256 -eq $item.sha256 -and $_.bytes -eq $item.bytes }).Count } | ForEach-Object path)\nConvertTo-Json -Compress -InputObject (@('PACKAGE_MANIFEST.json')+$delta)\n",encoding='utf-8')
        ps='C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe'
        cp=subprocess.run([ps,'-NoProfile','-File',str(script)],capture_output=True,text=True,encoding='utf-8')
        if cp.returncode or json.loads(cp.stdout)!=expected:raise RuntimeError('Actual PowerShell selection differs')
    control=(HERE/'m433_control.ps1').read_text(encoding='utf-8')
    anchor="foreach ($key in @('latest_m432_integrated_board','latest_m432_integrated_closure','latest_m433_complete_request_protocol','latest_m433_complete_request_preparation','latest_m433_timed_provider_component','latest_m433_performance_support')) { VerifyEvidence $key }"
    if control.count(anchor)!=1:raise RuntimeError('Control preparation anchor differs')
    control=control.replace(anchor,anchor+"\nVerifyEvidence 'latest_m433_actual_transfer_support'\n$finalSupport=Get-Content -Raw -Encoding UTF8 -LiteralPath (Join-Path $workspace $board.latest_m433_actual_transfer_support.result) | ConvertFrom-Json\nif ($finalSupport.manifest_sha256 -ne $digest -or -not $finalSupport.actual_assembly_pass -or -not $finalSupport.actual_transfer_pass) { throw 'Assembly/transfer support incomplete' }\nforeach ($p in $finalSupport.source_sha256.PSObject.Properties) { if ((Get-FileHash -LiteralPath (Join-Path $PSScriptRoot $p.Name) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $p.Value) { throw 'Final control identity changed' } }")
    atomic(HERE/'m433_control02.ps1',control.encode('utf-8'),immutable=True)
    ps='C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe'
    cp=subprocess.run([ps,'-NoProfile','-File',str(HERE/'m433_control02.ps1'),'-Mode','SelfTest'],capture_output=True)
    assert cp.returncode==0 and b'M433_CONTROL_SELF_TEST_PASS' in cp.stdout
    record=dict(status='PASS_M433_ACTUAL_ASSEMBLY_AND_TRANSFER_SUPPORT_ONLY',manifest_sha256=digest,
                actual_assembly_pass=True,actual_transfer_pass=True,actual_PowerShell_delta_pass=True,
                assembler_paths_adapted_only_for_self_owned_local_fixture=True,transfer_logs_explicit_synthetic=True,
                host_support_sha256=e['sha256'],negative_checks=rejected,uploaded_names=expected,
                control02_actual_failure_collection_selftest=True,source_sha256={'m433_control02.ps1':sha(HERE/'m433_control02.ps1'),'m433_transfer_support.py':sha(HERE/'m433_transfer_support.py')},
                board_run=False,numerical_pass=False,performance_pass=False,temperature_measurement_enabled=False)
    out=BASE/'runs/M433-actual-transfer-support-01/RESULT.json';atomic(out,encoded(record),immutable=True)
    sync('latest_m433_actual_transfer_support',dict(status=record['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out),manifest_sha256=digest),
         f'## M433 实际组装/上传回执配套（2026-10-07）\n\nSHA {sha(out)}；实际assembler同SHA旧包白名单完整组装、实际PowerShell差量选择与host transfer原子目的地/BOARD键通过，{len(rejected)}缺失/改动/额外文件/乱序/整SHA/bash拒绝；回执明确fixture。02控制强制本支持及源码SHA并通过故意失败收集自测，原02保持。所有离线支持已齐，下一步COM3一次sudo后manifest-first上传、组装、固定环境及预定4预热＋8正式完整请求；尚无上板/完整请求性能，不测温。')
    print('M433_TRANSFER_SUPPORT_SYNC',sha(out),len(rejected))


if __name__=='__main__':main()
