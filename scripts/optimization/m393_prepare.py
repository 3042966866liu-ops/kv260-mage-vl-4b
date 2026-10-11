"""Prepare full fixed30 text only after the new single-layer closure."""
import ast
import json
import shutil
import sys
import symtable
from m351_workflow import ROOT,HERE,BASE,sha,atomic,encoded,sync
from m377_prepare import once
OLD=BASE/'candidates/M386-ps-text-01';PKG=BASE/'candidates/M393-silu-text-01'

def main():
    if PKG.exists():raise RuntimeError('Immutable preparation exists')
    board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_text(encoding='utf-8'));prior=board['latest_m392_silu_layer_closure'];raw=board['latest_m392_silu_layer_board']['sha256']
    assert prior['status']=='PASS_SINGLE_LAYER_SILU_SCOPE_ONLY'
    for e in (prior,board['latest_m392_silu_layer_board']):
        assert sha(ROOT/e['result'])==e['sha256'] and all(e['sha256'] in (ROOT/n).read_text(encoding='utf-8') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    manifest=json.loads((OLD/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'));assert all(sha(OLD/r['path'])==r['sha256'] for r in manifest['files'])
    s=(OLD/'m386_ps_text_gate.py').read_text(encoding='utf-8').replace('M386','M393').replace('m386','m393')
    s=s.replace('from m393_text_ps_read import TextPSReadSession','from m393_silu_scope import SiluLayerScope,RetainedSiluOwnerError').replace('from ps_read_ahead import RetainedPSResourcesError\n','').replace('from m382_ps_slot import RetainedSlotError\n','')
    s=s.replace('ps_session','silu_scope').replace('/home/ubuntu/m393_ps_text_01','/home/ubuntu/m393_silu_text_01').replace('enable-ps-text','enable-silu-text').replace('enable_ps_text','enable_silu_text').replace('sealed-DMA-PS-fixed-text-numerical','sealed-DMA-SiLU-workspace-fixed-text-numerical')
    s=s.replace('except (RetainedPSResourcesError,RetainedSlotError) as exc:','except RetainedSiluOwnerError as exc:').replace('PASS_M393_PS_TEXT_NUMERICAL','PASS_M393_SILU_TEXT_NUMERICAL')
    a=s.index("        layer_path=Path('/home/ubuntu/m385_");z=s.index('        if os.geteuid()',a)
    s=s[:a]+f"        layer_path=Path('/home/ubuntu/m392_silu_layer_01/B1/load-memory.json')\n        layer=json.loads(layer_path.read_text(encoding='utf-8'))\n        if sha256(layer_path)!='{raw}' or layer['status']!='PASS_M392_SILU_LAYER_NUMERICAL' or not layer['scope_weakref_dead']:raise RuntimeError('Actual SiLU layer prerequisite differs')\n        result['silu_layer_prerequisite_sha256']=sha256(layer_path)\n"+s[z:]
    a=s.index('        plan=[(');z=s.index("        policy.capture('after-fixed-text'",a)
    s=s[:a]+"""        silu_scope=SiluLayerScope(model,policy,resident,enabled=True)
        scope_ref=weakref.ref(silu_scope)
        prefill_function=silu_scope.bind(sys.modules['m241_video_language_runtime'])
        token,logits,kv=prefill_function(model,hidden.copy())
        silu_scope.close()
        result['silu_scope']=silu_scope.report()
        del prefill_function
        silu_scope=None
        if scope_ref() is not None:raise RetainedSiluOwnerError('Closed fixed-text SiLU scope retained')
        result['scope_weakref_dead']=True
        result['ps_prefetch_enabled']=False
        result['worker_started']=False
        result['silu_workspace_enabled']=True
        result['original_parser_workers']=1
        result['extra_pynq_allocations']=len(allocations)-7
"""+s[z:]
    s=s.replace('one ordinary PS slot, no extra CMA or visual forward','one ordinary SiLU workspace borrowed through mlp_down, original staging and one parser, no PS prefetch/extra CMA/visual forward')
    s=s.replace('Fixed-text PS numerical and lifecycle closure; only then independently budget fixed159 video; stop expansion on capacity/lifecycle issue','Fixed-text SiLU numerical/lifetime closure, then same original fixed159 video and lightweight full-request timing')
    assert 'TextPSReadSession' not in s and 'RetainedPSResourcesError' not in s
    PKG.mkdir(parents=True)
    skip={'m386_ps_text_gate.py','m386_text_ps_read.py','m386_export_result.py','m386_assemble.py','run_m386_ps_text.sh','ps_read_ahead.py','m383_sealed_ps_read.py','m382_ps_slot.py','SHA256SUMS'}
    for r in manifest['files']:
        if r['path'] not in skip:shutil.copyfile(OLD/r['path'],PKG/r['path'])
    atomic(PKG/'m393_silu_text_gate.py',s.encode('utf-8'))
    for n in ('m393_silu_scope.py','m393_silu_workspace.py'):shutil.copyfile(HERE/n,PKG/n)
    for src,dst in [('m386_export_result.py','m393_export_result.py'),('run_m386_ps_text.sh','run_m393_silu_text.sh')]:
        t=(OLD/src).read_text(encoding='utf-8').replace('M386','M393').replace('m386','m393').replace('m393_ps_text','m393_silu_text').replace('ENABLE_PS_TEXT','ENABLE_SILU_TEXT').replace('enable-ps-text','enable-silu-text').replace('sealed-DMA-PS-fixed-text-numerical','sealed-DMA-SiLU-workspace-fixed-text-numerical')
        atomic(PKG/dst,t.encode('utf-8'))
    old_remote='/home/ubuntu/m386_ps_text_candidate_01'
    assert "$remote='"+old_remote+"'" in (HERE/'m386_control.ps1').read_text(encoding='utf-8-sig')
    t=(BASE/'candidates/M392-silu-layer-02/m392_assemble.py').read_text(encoding='utf-8').replace('M392','M393').replace('/home/ubuntu/m385_ps_layer_candidate_01',old_remote).replace('8855475f0a6c87b6c469cdf40c46f514b9e43e6fcc017e8dedc7d0d74456f412',sha(OLD/'PACKAGE_MANIFEST.json'))
    atomic(PKG/'m393_assemble.py',t.encode('utf-8'))
    trees={p.stem:ast.parse(p.read_text(encoding='utf-8'),feature_version=(3,10)) for p in PKG.glob('*.py')};allowed=set(sys.stdlib_module_names)|set(json.loads((PKG/'SOURCE_CLOSURE.json').read_text(encoding='utf-8'))['modules'])|{'numpy','pynq','tokenizers'};missing=[]
    for mod,tree in trees.items():
        for n in ast.walk(tree):
            names=[x.name.split('.')[0] for x in n.names] if isinstance(n,ast.Import) else ([(n.module or '').split('.')[0]] if isinstance(n,ast.ImportFrom) else [])
            missing.extend((mod,n) for n in names if n and n not in trees and n not in allowed)
    assert not missing,missing
    table=next(x for x in symtable.symtable(s,'gate','exec').get_children() if x.get_name()=='main');assert next(x for x in table.get_children() if x.get_name()=='tracked_allocate').lookup('SHAPES').is_global()
    for r in json.loads((PKG/'HARDWARE_CLOSURE.json').read_text(encoding='utf-8'))['prerequisites']:assert sha(ROOT/r['path'])==r['sha256']
    rows=[dict(path=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(PKG.iterdir())];atomic(PKG/'SHA256SUMS',''.join(r['sha256']+'  '+r['path']+'\n' for r in rows).encode('ascii'));rows.append(dict(path='SHA256SUMS',bytes=(PKG/'SHA256SUMS').stat().st_size,sha256=sha(PKG/'SHA256SUMS')))
    atomic(PKG/'PACKAGE_MANIFEST.json',encoded(dict(schema='M393-isolated-SiLU-fixed-text-v1',files=rows,file_count=len(rows),total_bytes=sum(r['bytes'] for r in rows))))
    value=dict(status='PASS_OFFLINE_SILU_FIXED_TEXT_PREPARATION',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),prior=prior,layer_raw_sha256=raw,
               recursive_missing=missing,python310_syntax=True,shape=[30,9728],workspace_bytes=30*9728*4,file_count=len(rows),total_bytes=sum(r['bytes'] for r in rows),
               original_parser_workers=1,PS_prefetch=False,extra_DMA_allowed=False,diagnostic_growth_budget_bytes=256<<20,ordinary_margin_bytes=64<<20,
               actual_head_observer_unchanged=True,production_policy_unchanged=True,board_run=False,performance_pass=False,test_support_pending=True)
    out=BASE/'runs/M393-silu-text-preparation-01/RESULT.json';atomic(out,encoded(value),immutable=True);d=sha(out)
    sync('latest_m393_silu_text_preparation',dict(status=value['status'],manifest_sha256=value['manifest_sha256'],sha256=d,result=out.relative_to(ROOT).as_posix()),
         f'## M393 SiLU固定30文本接入准备（2026-10-04）\n\n新单层原SHA {raw}闭合后，原36层Prefill/完整head、154family/151936logits/72KV与重试参考保持，只SiLU借用scope，30×9728工作缓冲1167360B。原单parser/暂存、0新DMA，256MiB普通停止上限/64MiB普通余量/生产准入不改；同SHA真实head物理观察与硬件证据复用。SHA {d}，missing0/3.10，尚需控制/回收支持，未上板或新文本/视频/完整请求收益。')
    print(json.dumps(value|{'result_sha256':d}))

if __name__=='__main__':main()
