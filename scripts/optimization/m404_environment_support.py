"""Actual observer/exporter, transfer and collector fault checks; explicit fixtures."""
import base64
import copy
from contextlib import redirect_stdout
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
from m351_workflow import ROOT, BASE, HERE, sha, atomic, encoded, sync
from m404_environment_prepare import PKG, checks
import m404_environment_workflow as workflow
from m404_warm_conditions import PROTOCOL_SHA


def export_fixture(value):
    raw=encoded(value); chunks=[raw[i:i+900] for i in range(0,len(raw),900)]
    return 'M404_ENV_RESULT_SHA256='+hashlib.sha256(raw).hexdigest()+'\n'+''.join(
        f'M404_ENV_RESULT_CHUNK={i}/{len(chunks)}:'+base64.b64encode(p).decode()+'\n' for i,p in enumerate(chunks))


def main():
    root=ROOT/'tmp/m404env'; root.mkdir(parents=True,exist_ok=True)
    _, env=checks()
    spec=importlib.util.spec_from_file_location('m404_test_actual_probe',PKG/'m404_environment_probe.py')
    probe=importlib.util.module_from_spec(spec); spec.loader.exec_module(probe)
    with tempfile.TemporaryDirectory(dir=root) as d:
        directory=Path(d); probe.OUTPUT=directory/'saved/RESULT.json'
        probe.os=SimpleNamespace(geteuid=lambda:0,fsync=__import__('os').fsync,replace=__import__('os').replace)
        probe.read_environment=lambda:copy.deepcopy(env)
        old_argv=sys.argv
        try:
            sys.argv=['probe',sha(PKG/'PACKAGE_MANIFEST.json'),'--enable-readonly-observation']
            capture=io.StringIO()
            with redirect_stdout(capture): assert probe.main()==0
            digest,raw,value,count=workflow.decode(capture.getvalue())
            assert raw==probe.OUTPUT.read_bytes() and digest==sha(probe.OUTPUT)
            original=probe.OUTPUT.read_bytes()
            try: probe.main()
            except RuntimeError: pass
            else: raise AssertionError('Original observation overwritten')
            assert probe.OUTPUT.read_bytes()==original
            sys.argv=['probe'];
            try: probe.main()
            except RuntimeError: pass
            else: raise AssertionError('Default-off bypassed')
            sys.argv=['probe','Collect']; capture=io.StringIO()
            with redirect_stdout(capture): assert probe.main()==0
            assert workflow.decode(capture.getvalue())[1]==original
        finally: sys.argv=old_argv
        bad=[]
        for k,v in [('manifest_sha256','0'*64),('protocol_sha256','0'*64),('model_forward_calls',True),
                    ('dma_allocations',1),('overlay_loaded',True),('performance_pass',True),('elapsed_s',21),
                    ('status','WARM_ENVIRONMENT_UNPROVEN')]:
            q=copy.deepcopy(value);q[k]=v;bad.append(export_fixture(q))
        q=copy.deepcopy(value);q['environment']['pl_clocks']={};bad.append(export_fixture(q))
        q=copy.deepcopy(value);q['environment']['observability_issues']=['invented'];bad.append(export_fixture(q))
        valid=export_fixture(value);lines=valid.splitlines(True)
        bad += [valid+lines[0],valid.replace(lines[2],''),valid.replace('CHUNK=1/','CHUNK=0/')]
        for log in bad:
            try:workflow.decode(log)
            except (ValueError,KeyError,TypeError):pass
            else:raise AssertionError('Invalid raw observation accepted')
        # Actual early UNPROVEN remains an observation, never a performance pass.
        q=copy.deepcopy(value);q['environment']['missing']=['fake unavailable cooling'];
        from m404_warm_conditions import environment_issues
        q['environment']['observability_issues']=environment_issues(q['environment']);q['status']='WARM_ENVIRONMENT_UNPROVEN'
        assert workflow.decode(export_fixture(q))[2]==q
        saved=(workflow.ROOT,workflow.BASE,workflow.atomic,workflow.sync)
        actions=[]
        try:
            workflow.ROOT=directory;workflow.BASE=directory/'base'
            folder=directory/'tmp/m404env';folder.mkdir(parents=True)
            manifest=json.loads((PKG/'PACKAGE_MANIFEST.json').read_bytes())
            names=['PACKAGE_MANIFEST.json']+[r['path'] for r in manifest['files']]
            for name in names:
                size=(PKG/name).stat().st_size;n=(size+899)//900;prefix='upload_'+name.replace('.','_')
                (folder/(prefix+'_final.log')).write_text('M212_CHUNKED_FILE_PASS '+sha(PKG/name),encoding='utf-8')
                for i in range(1,n+1):
                    (folder/(prefix+f'_chunk_{i:05d}.log')).write_text(f'M212_CHUNK_PASS {i} {n} {min(i*900,size)} fake\n',encoding='utf-8')
            (folder/'syntax.log').write_text('__M404_ENV_SYNTAX_RC_0__',encoding='utf-8')
            def save(p,raw,**kw):
                actions.append(('atomic',p.relative_to(workflow.BASE).as_posix(),kw));saved[2](p,raw,**kw)
            workflow.atomic=save;workflow.sync=lambda key,*a:actions.append(('sync',key))
            with redirect_stdout(io.StringIO()):workflow.transfer()
            assert actions[0][:2]==('atomic','runs/M404-environment-transfer-01/RESULT.json') and actions[0][2]['immutable']
            assert actions[1]==('sync','latest_m404_environment_transfer')
            (folder/('upload_'+names[1].replace('.','_')+'_final.log')).unlink()
            try:workflow.transfer()
            except OSError:pass
            else:raise AssertionError('Missing transfer receipt accepted')
            log=directory/'saved.log';log.write_text(valid,encoding='utf-8')
            with redirect_stdout(io.StringIO()):workflow.collect(log)
            assert actions[2][:2]==('atomic','runs/M404-environment-board-01/BOARD_RESULT.json') and actions[2][2]['immutable']
            assert actions[3]==('sync','latest_m404_environment_board')
        finally: workflow.ROOT,workflow.BASE,workflow.atomic,workflow.sync=saved
    ps=Path(r'C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell\pwsh.exe')
    tested=subprocess.run([str(ps),'-NoProfile','-File',str(HERE/'m404_environment_control.ps1'),'-Mode','SelfTest'],capture_output=True,text=True,encoding='utf-8',check=True)
    assert 'M404_ENV_CONTROL_SYNTAX_PASS' in tested.stdout
    value=dict(status='PASS_OFFLINE_READONLY_OBSERVER_CONTROL_AND_COLLECTION',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),
               protocol_sha256=PROTOCOL_SHA,actual_exporter_and_saved_collect=True,default_off_and_immutable=True,
               collector_negative_checks=len(bad),actual_transfer_all6_files=True,missing_receipt_refused=True,
               actual_atomic_destination_sync_keys=True,board_run=False,performance_pass=False,
               source_sha256={n:sha(HERE/n) for n in ('m404_environment_workflow.py','m404_environment_control.ps1','m404_environment_support.py')})
    out=BASE/'runs/M404-environment-support-01/RESULT.json';atomic(out,encoded(value),immutable=True);h=sha(out)
    sync('latest_m404_environment_support',dict(status=value['status'],result=out.relative_to(ROOT).as_posix(),sha256=h,manifest_sha256=value['manifest_sha256']),
         f'## M404 只读探针控制/回收检查（2026-10-05）\n\nSHA {h}；实际probe/导出/Collect原字节、default-off/immutable及{len(bad)}回收负例、全部6文件假回执/缺失拒绝、实际保存目标和同步键、PS语法通过；'
         '全部明确CPU环境fixture，无板端能力或性能结论。下一步仅manifest-first900B上传及一次只读环境观察；条件不足不运行模型。')
    print(json.dumps(value|dict(sha256=h)))


if __name__=='__main__':main()
