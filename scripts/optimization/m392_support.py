"""Actual gate-region/layer lifetime, assembly and strict recovery support."""
import base64
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from m351_workflow import ROOT,HERE,BASE,sha,atomic,encoded,sync
from m392_collect import PKG,decode
OLD=BASE/'candidates/M385-ps-layer-02'
PS=Path(r'C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell\pwsh.exe')

def export(r):
    raw=encoded(r);p=[raw[i:i+900] for i in range(0,len(raw),900)]
    return 'M392_RESULT_SHA256='+hashlib.sha256(raw).hexdigest()+'\nM392_SAVED_GATE_RC='+str(r['gate_return_code'])+'\n'+''.join(f'M392_RESULT_CHUNK={i}/{len(p)}:'+base64.b64encode(x).decode('ascii')+'\n' for i,x in enumerate(p))+'M392_DONE case=B1 gate_rc='+str(r['gate_return_code'])+' export_rc=0\n'

def collector_tests():
    r=json.loads((BASE/'runs/M385-ps-layer-board-01/BOARD_RESULT.json').read_text(encoding='utf-8'))
    r.update(status='PASS_M392_SILU_LAYER_NUMERICAL',gate_level='sealed-DMA-SiLU-workspace-single-layer-numerical',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),
             component_prerequisite_sha256='377ac2cf8b082eadbffad43c440ff32fcb24d377280a96e6e56f9d07f2efb5b4',ps_prefetch_enabled=False,worker_started=False,
             scope_weakref_dead=True,silu_workspace_enabled=True,silu_scope=dict(calls=1,closed=True,retained=False,
             events=['before-layer-workspace-scope','before-silu','after-mlp-down-before-reuse','before-workspace-close'],workspace_bytes=6187008,
             workspace_object_released=True,workspace_buffer_released=True,binding_callback_removed=True))
    assert decode(export(r))[2]==r
    f=dict(r,status='FAIL_UNSAFE_RETAINED',gate_return_code=1,errors=['EXPLICIT_FAKE_CONSUMER_ERROR']);assert decode(export(f))[2]==f
    bad=[]
    for k,v in [('manifest_sha256','0'*64),('case','A1'),('build_id','0'),('gate_level','wrong'),('gate_return_code',True),('memory_capacity_proven',True),('performance_pass',True),('formal_promotion_allowed',True),('errors',['error']),('unsafe_buffers_retained',True),('safe_buffers_released',False),('numerical_pass',False),('released_buffers',r['allocated_buffers']),('original_buffer_release_count',6),('model_forward_calls',2),('layer_result',{}),('blocked_inference_attempts',['head']),('transactions',[]),('fpga_transactions',25),('stable_overlay_reloaded',False),('boot_unchanged',False),('patch_registry_cleared',False),('component_prerequisite_sha256','bad'),('ps_prefetch_enabled',True),('worker_started',True),('scope_weakref_dead',False),('silu_workspace_enabled',False),('original_parser_workers',2),('extra_pynq_allocations',1),('silu_scope',{}),('diagnostic_ps_growth_limit_bytes',64<<20),('diagnostic_ps_available_margin_bytes',1),('additional_cma_requests_allowed',True)]:
        q=copy.deepcopy(r);q[k]=v;bad.append(export(q))
    for kind in ('busy','monitor','memory','counter','consumer_count','buffer_retained'):
        q=copy.deepcopy(r)
        if kind=='busy':q['final_snapshot']['mm2s_idle']=False;q['final_snapshot']['mm2s_dmasr']=4096
        elif kind=='monitor':q['sampled_memory']['observer_stopped']=False
        elif kind=='memory':q['stage_memory'][0]['admission']['observed_rss_growth_bytes']=257<<20
        elif kind=='counter':q['stage_memory'][-1]['cma_counts']['reserved:alloc_pages_success']+=1
        elif kind=='consumer_count':q['silu_scope']['calls']=0
        elif kind=='buffer_retained':q['silu_scope']['workspace_buffer_released']=False
        bad.append(export(q))
    text=export(r);chunks=[s for s in text.splitlines(True) if 'RESULT_CHUNK' in s]
    bad.extend([text.replace(chunks[1],''),text+chunks[0],text.replace('RESULT_CHUNK=1/','RESULT_CHUNK=0/'),text.replace('export_rc=0','export_rc=1')])
    for log in bad:
        try:decode(log)
        except (ValueError,KeyError,TypeError):pass
        else:raise AssertionError('Invalid metadata accepted')
    return len(bad)

def assembly_tests():
    spec=importlib.util.spec_from_file_location('actual_m392_assembly',PKG/'m392_assemble.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    assert mod.OLD.as_posix()=='/home/ubuntu/m385_ps_layer_candidate_01' and mod.OLD_SHA==sha(OLD/'PACKAGE_MANIFEST.json')
    assert "$remote='/home/ubuntu/m385_ps_layer_candidate_01'" in (HERE/'m385_control.ps1').read_text(encoding='utf-8-sig')
    m=json.loads((PKG/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'));old={r['path']:r for r in json.loads((OLD/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))['files']}
    delta=[r['path'] for r in m['files'] if old.get(r['path'])!=r]
    root=ROOT/'tmp/m392/assembly-tests';root.mkdir(parents=True,exist_ok=True)
    for kind in ['good','old_manifest','source','missing','extra','count','bytes','traversal']:
        with tempfile.TemporaryDirectory(dir=root) as d:
            base=Path(d).resolve();assert base.parent==root.resolve();prior=base/'old';dest=base/'new';prior.mkdir();dest.mkdir()
            for p in OLD.iterdir():
                if p.is_file():(prior/p.name).write_bytes(p.read_bytes())
            for name in ['PACKAGE_MANIFEST.json']+delta:(dest/name).write_bytes((PKG/name).read_bytes())
            mm=copy.deepcopy(m)
            if kind=='old_manifest':(prior/'PACKAGE_MANIFEST.json').write_bytes(b'bad')
            elif kind=='source':(prior/next(r['path'] for r in m['files'] if r['path'] not in delta)).write_bytes(b'bad')
            elif kind=='missing':(dest/delta[0]).unlink()
            elif kind=='extra':(dest/'extra').write_bytes(b'x')
            elif kind=='count':mm['file_count']+=1
            elif kind=='bytes':mm['total_bytes']+=1
            elif kind=='traversal':mm['files'][0]['path']='../escape'
            if mm!=m:(dest/'PACKAGE_MANIFEST.json').write_bytes(encoded(mm))
            mod.HERE=dest;mod.OLD=prior
            try:mod.main(sha(dest/'PACKAGE_MANIFEST.json'))
            except RuntimeError:
                if kind=='good':raise
            else:
                if kind!='good':raise AssertionError('Assembly accepted '+kind)
    p=subprocess.run([str(PS),'-NoProfile','-File',str(HERE/'m392_control.ps1'),'-Mode','List'],capture_output=True,text=True,encoding='utf-8',check=True)
    assert json.loads(p.stdout)==['PACKAGE_MANIFEST.json']+delta
    return 8

def main():
    assert sha(HERE/'m392_silu_scope.py')==sha(PKG/'m392_silu_scope.py')
    log=ROOT/'tmp/m392/support_tests.log'
    if not log.exists():
        p=subprocess.run([sys.executable,'-X','utf8','-B',str(HERE/'test_m392_silu_scope.py')],capture_output=True,text=True,encoding='utf-8')
        atomic(log,(p.stdout+p.stderr).encode('utf-8'),immutable=True)
        assert p.returncode==0
    content=log.read_text(encoding='utf-8');assert 'Ran 9 tests' in content and content.rstrip().endswith('OK')
    negative=collector_tests();assembly=assembly_tests()
    p=subprocess.run([str(PS),'-NoProfile','-File',str(HERE/'m392_control.ps1'),'-Mode','SelfTest'],capture_output=True,text=True,encoding='utf-8',check=True)
    assert 'M392_CONTROL_SELF_TEST_PASS' in p.stdout
    names=['m392_support.py','m392_control.ps1','m392_collect.py','m392_workflow.py','test_m392_silu_scope.py','m392_silu_scope.py']
    value=dict(status='PASS_OFFLINE_SILU_LAYER_CONTROL_RECOVERY',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),
               actual_layer_gate_lifetime_tests=9,collector_negative_checks=negative,actual_assembly_checks=assembly,actual_PS_list_and_prior_remote=True,
               failed_gate_still_collected=True,source_sha256={n:sha(HERE/n) for n in names},test_log_sha256=sha(log),
               fake_DMA_layer_math_metadata_explicit=True,board_run=False,performance_pass=False,
               rejected_draft_binding='Closed function initially raised NameError after callback removal; entry guard added before any family, tested before freeze',
               rejected_package_01='Wrong remote prior package name, recorded and immutable; repaired02 only, no board command')
    out=BASE/'runs/M392-silu-layer-support-01/RESULT.json';atomic(out,encoded(value),immutable=True);d=sha(out)
    sync('latest_m392_silu_layer_support',dict(status=value['status'],manifest_sha256=value['manifest_sha256'],result=out.relative_to(ROOT).as_posix(),sha256=d),
         f'## M392 SiLU单层实际调用/回收支持（2026-10-04）\n\n9项原loop/实际gate调用及异常retain/stale-entry/weakref检查、{negative}回收负例、8真实assembly与实际旧远程目录/PS选择通过；SHA {d}。数学/DMA/内存元数据明确替身，非本级板端数值。01远程目录拒绝保留，只新02；下一步同COM3 sudo后一次原layer0数值门禁。')
    print(json.dumps(value|{'result_sha256':d}))

if __name__=='__main__':main()
