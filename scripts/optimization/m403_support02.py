"""Supplement: actual host transfer receipts and paired early-failure exporter."""
import ast
import base64
from contextlib import redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
from m351_workflow import ROOT,HERE,BASE,sha,atomic,encoded,sync
from m403_prepare import PKG,OLD,SCOPE

PS=Path(r'C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell\pwsh.exe')


def transfer_checks():
    import m403_workflow as workflow
    assert workflow.OLD==OLD and workflow.PKG==PKG
    actual=json.loads((PKG/'PACKAGE_MANIFEST.json').read_bytes())
    prior={r['path']:r for r in json.loads((OLD/'PACKAGE_MANIFEST.json').read_bytes())['files']}
    names=['PACKAGE_MANIFEST.json']+[r['path'] for r in actual['files'] if prior.get(r['path'])!=r]
    saved=(workflow.ROOT,workflow.BASE,workflow.atomic,workflow.sync)
    try:
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp/m403') as d:
            root=Path(d);logs=root/'tmp/m403';logs.mkdir(parents=True)
            for name in names:
                size=(PKG/name).stat().st_size;count=(size+899)//900;prefix='upload_'+name.replace('.','_')
                (logs/(prefix+'_final.log')).write_text('M212_CHUNKED_FILE_PASS '+sha(PKG/name),encoding='utf-8')
                for i in range(1,count+1):
                    (logs/(prefix+f'_chunk_{i:05d}.log')).write_text(f'M212_CHUNK_PASS {i} {count} {min(i*900,size)} explicit-fake\n',encoding='utf-8')
            (logs/'assembly_uart.log').write_text('M403_ASSEMBLY_SHA_PASS '+sha(PKG/'PACKAGE_MANIFEST.json')+'\n__M403_ASSEMBLY_RC_0__\n',encoding='utf-8')
            (logs/'root_syntax_uart.log').write_text('__M403_SYNTAX_RC_0__\n',encoding='utf-8')
            workflow.ROOT=root;workflow.BASE=root/'base';actions=[]
            def saved_atomic(p,raw,**kw):
                assert p.resolve().is_relative_to(root.resolve())
                actions.append(('atomic',p.relative_to(workflow.BASE).as_posix(),json.loads(raw),kw))
                saved[2](p,raw,**kw)
            workflow.atomic=saved_atomic
            workflow.sync=lambda key,*args:actions.append(('sync',key))
            with redirect_stdout(io.StringIO()):workflow.transfer()
            assert actions[0][0:2]==('atomic','runs/M403-tail-performance-transfer-01/RESULT.json') and actions[0][3]['immutable']
            assert actions[0][2]['old_manifest_sha256']==sha(OLD/'PACKAGE_MANIFEST.json')
            assert len(actions[0][2]['new_files'])==len(names)
            assert actions[1]==('sync','latest_m403_tail_performance_transfer')
            missing=logs/('upload_'+names[1].replace('.','_')+'_final.log');missing.unlink()
            try:workflow.transfer()
            except OSError:pass
            else:raise AssertionError('Missing transfer receipt accepted')
            assert len(actions)==2
    finally:workflow.ROOT,workflow.BASE,workflow.atomic,workflow.sync=saved
    return len(names)


def exporter_checks():
    import m403_collect
    spec=importlib.util.spec_from_file_location('m403_actual_export',PKG/'m403_export_result.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    early=dict(status='FAIL',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),case='B1',gate_level=SCOPE,gate_return_code=1,errors=['explicit-fake-early-source-failure'],memory_capacity_proven=False,performance_pass=False,formal_promotion_allowed=False)
    with tempfile.TemporaryDirectory(dir=ROOT/'tmp/m403') as d:
        root=Path(d);(root/'load-memory.json').write_bytes(encoded(early))
        mod.os=SimpleNamespace(geteuid=lambda:0);mod.time=SimpleNamespace(sleep=lambda _:None)
        def mapped(path):
            assert path=='/home/ubuntu/m403_tail_performance_01'
            return root
        mod.Path=mapped;captured=io.StringIO()
        with redirect_stdout(captured):mod.emit_saved('B1')
        assert m403_collect.decode(captured.getvalue())[2]==early
    # Every simple HERE/filename consumer is in the actual new manifest.
    names={r['path'] for r in json.loads((PKG/'PACKAGE_MANIFEST.json').read_bytes())['files']}
    checked=[]
    for name in ('m403_light_video_gate.py','m403_trials.py','m403_video_entry.py'):
        tree=ast.parse((PKG/name).read_bytes())
        for n in ast.walk(tree):
            if isinstance(n,ast.BinOp) and isinstance(n.op,ast.Div) and isinstance(n.left,ast.Name) and n.left.id in ('HERE','here') and isinstance(n.right,ast.Constant) and isinstance(n.right.value,str):
                assert n.right.value in names or n.right.value=='PACKAGE_MANIFEST.json',(name,n.right.value)
                checked.append((name,n.right.value))
    return checked


def main():
    count=transfer_checks();consumers=exporter_checks()
    c=(HERE/'m403_control.ps1').read_text(encoding='utf-8')
    c=c.replace("'latest_m403_tail_performance_support'","'latest_m403_tail_performance_support02'").replace('$board.latest_m403_tail_performance_support.result','$board.latest_m403_tail_performance_support02.result')
    atomic(HERE/'m403_control02.ps1',c.encode('utf-8'),immutable=True)
    p=subprocess.run([str(PS),'-NoProfile','-File',str(HERE/'m403_control02.ps1'),'-Mode','SelfTest'],capture_output=True,text=True,encoding='utf-8',check=True)
    assert 'M403_CONTROL_SELF_TEST_PASS' in p.stdout
    previous=BASE/'runs/M403-tail-performance-support-01/RESULT.json';value=json.loads(previous.read_bytes())
    value.update(status='PASS_OFFLINE_TAIL_BALANCED_CONTROL_RECOVERY02',previous_support_sha256=sha(previous),actual_workflow_transfer_fake_receipts_checked=count,missing_receipt_refused=True,early_FAIL_actual_exporter_collector=True,actual_HERE_consumers=consumers)
    value['source_sha256'].update({n:sha(HERE/n) for n in ('m403_support02.py','m403_control02.ps1')})
    out=BASE/'runs/M403-tail-performance-support-02/RESULT.json';atomic(out,encoded(value),immutable=True);h=sha(out)
    sync('latest_m403_tail_performance_support02',dict(status=value['status'],result=out.relative_to(ROOT).as_posix(),sha256=h,manifest_sha256=value['manifest_sha256']),f'## M403 实际传输/早期导出配套支持02（2026-10-04）\n\nSHA {h}；原39载荷包与已过7计数/8请求替身/29回收负例保持。实际workflow全部{count}增量文件/900B分块假回执、精确M395旧manifest/原子目标/BOARD键及缺失拒绝通过；真实导出器early FAIL到严格collector、所有HERE文件消费者核对。只使用control02，离线支持，没有上传/FPGA/新性能。下一步同COM3授权后一次轻量ABBABAAB。')
    print(json.dumps(dict(status=value['status'],sha256=h,transfer_files=count,consumers=consumers)))


if __name__=='__main__':main()
