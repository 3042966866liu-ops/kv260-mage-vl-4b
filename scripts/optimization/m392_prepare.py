"""Freeze one isolated layer; only the SiLU/down borrowed-result scope changes."""
import ast
import json
import shutil
import sys
import symtable
from m351_workflow import ROOT,HERE,BASE,sha,atomic,encoded,sync
from m377_prepare import once
OLD=BASE/'candidates/M385-ps-layer-02';PKG=BASE/'candidates/M392-silu-layer-02'
OLD_SHA='8855475f0a6c87b6c469cdf40c46f514b9e43e6fcc017e8dedc7d0d74456f412'
RAW='377ac2cf8b082eadbffad43c440ff32fcb24d377280a96e6e56f9d07f2efb5b4'

def main():
    if PKG.exists():raise RuntimeError('Immutable candidate exists')
    board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_text(encoding='utf-8'));prior=board['latest_m391_silu_closure']
    assert prior['status']=='PASS_SILU_COMPONENT_ONLY_INTEGRATION_NOT_PROVEN' and sha(ROOT/prior['result'])==prior['sha256']
    assert all(prior['sha256'] in (ROOT/n).read_text(encoding='utf-8') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    assert sha(OLD/'PACKAGE_MANIFEST.json')==OLD_SHA
    manifest=json.loads((OLD/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))
    assert all(sha(OLD/r['path'])==r['sha256'] for r in manifest['files'])
    s=(OLD/'m385_ps_layer_gate.py').read_text(encoding='utf-8').replace('M385','M392').replace('m385','m392')
    s=s.replace('from m392_layer_ps_read import LayerPSReadSession','from m392_silu_scope import SiluLayerScope,RetainedSiluOwnerError')
    s=s.replace('from ps_read_ahead import RetainedPSResourcesError\n','').replace('from m382_ps_slot import RetainedSlotError\n','')
    s=s.replace('/home/ubuntu/m392_ps_layer_01','/home/ubuntu/m392_silu_layer_01').replace('enable-ps-layer','enable-silu-layer').replace('enable_ps_layer','enable_silu_layer')
    s=s.replace('sealed-DMA-PS-single-layer-numerical','sealed-DMA-SiLU-workspace-single-layer-numerical')
    s=s.replace('ps_session','silu_scope')
    s=s.replace('Original complete runtime/seven DMA, original one parser; five-window PS slot within existing layer budget; production policy unchanged','Original complete runtime/seven DMA/original staging and one parser; one5.900390625MiB ordinary workspace borrowed through original mlp_down, no PS prefetch; production policy unchanged')
    a=s.index("        chain_path=Path(");z=s.index('        if os.geteuid()',a)
    s=s[:a]+f"        component_path=Path('/home/ubuntu/m391_silu_component_01/RESULT.json')\n        component=json.loads(component_path.read_text(encoding='utf-8'))\n        if sha256(component_path)!='{RAW}' or component['status']!='PASS_M391_CPU_MEASUREMENTS' or not component['numerical_pass'] or not component['component_performance_pass'] or not component['workspace_object_and_buffer_released']:raise RuntimeError('Actual CPU component prerequisite differs')\n        result['component_prerequisite_sha256']=sha256(component_path)\n"+s[z:]
    s=once(s,"        one_layer=bind(sys.modules['m241_video_language_runtime'],(HERE/'frozen_one_layer.py').read_text(encoding='utf-8'))", "        frozen_layer=(HERE/'frozen_one_layer.py').read_text(encoding='utf-8')")
    a=s.index('        plan=[(');z=s.index("        policy.capture('after-layer0'",a)
    s=s[:a]+"""        silu_scope=SiluLayerScope(model,policy,resident,enabled=True)
        scope_ref=weakref.ref(silu_scope)
        one_layer=silu_scope.bind(sys.modules['m241_video_language_runtime'],frozen_layer)
        output,kv=one_layer(model,hidden.copy())
        silu_scope.close()
        result['silu_scope']=silu_scope.report()
        del one_layer
        silu_scope=None
        if scope_ref() is not None:raise RetainedSiluOwnerError('Closed SiLU scope still retained')
        result['scope_weakref_dead']=True
        result['ps_prefetch_enabled']=False
        result['worker_started']=False
        result['silu_workspace_enabled']=True
        result['original_parser_workers']=1
        result['extra_pynq_allocations']=len(allocations)-7
"""+s[z:]
    s=s.replace('except (RetainedPSResourcesError,RetainedSlotError) as exc:','except RetainedSiluOwnerError as exc:')
    s=s.replace('PASS_M392_PS_LAYER_NUMERICAL','PASS_M392_SILU_LAYER_NUMERICAL')
    s=s.replace('Single-layer PS numerical/lifecycle closure and triad; only then prepare fixed-text PS plan; stop expansion on capacity/lifecycle issue','Single-layer SiLU numerical/lifetime closure and triad; only then original fixed30 text, fixed159 video and lightweight full-request comparison')
    assert 'LayerPSReadSession' not in s and 'RetainedPSResourcesError' not in s and 'ps_session' not in s
    PKG.mkdir(parents=True)
    skip={'m385_ps_layer_gate.py','m385_layer_ps_read.py','m385_assemble.py','m385_export_result.py','run_m385_ps_layer.sh','ps_read_ahead.py','m383_sealed_ps_read.py','m382_ps_slot.py','SHA256SUMS'}
    for r in manifest['files']:
        if r['path'] not in skip:shutil.copyfile(OLD/r['path'],PKG/r['path'])
    atomic(PKG/'m392_silu_layer_gate.py',s.encode('utf-8'))
    for n in ['m392_silu_scope.py','m389_silu_workspace.py']:shutil.copyfile(HERE/n,PKG/n)
    for src,dst in [('m385_export_result.py','m392_export_result.py'),('run_m385_ps_layer.sh','run_m392_silu_layer.sh')]:
        text=(OLD/src).read_text(encoding='utf-8').replace('M385','M392').replace('m385','m392').replace('m392_ps_layer','m392_silu_layer')
        text=text.replace('ENABLE_PS_LAYER','ENABLE_SILU_LAYER').replace('enable-ps-layer','enable-silu-layer').replace('sealed-DMA-PS-single-layer-numerical','sealed-DMA-SiLU-workspace-single-layer-numerical')
        atomic(PKG/dst,text.encode('utf-8'))
    actual_control=(HERE/'m385_control.ps1').read_text(encoding='utf-8-sig')
    assert "$remote='/home/ubuntu/m385_ps_layer_candidate_01'" in actual_control
    assembly=(BASE/'candidates/M390-gate-up-capture-01/m390_assemble.py').read_text(encoding='utf-8').replace('M390','M392').replace('/home/ubuntu/m387_ps_video_candidate_01','/home/ubuntu/m385_ps_layer_candidate_01').replace('2613ed813ca8d873076b0a6443309242f9c0594e655e57dcfe4d1859839f4fbb',OLD_SHA)
    atomic(PKG/'m392_assemble.py',assembly.encode('utf-8'))
    trees={p.stem:ast.parse(p.read_text(encoding='utf-8'),feature_version=(3,10)) for p in PKG.glob('*.py')}
    allowed=set(sys.stdlib_module_names)|set(json.loads((PKG/'SOURCE_CLOSURE.json').read_text(encoding='utf-8'))['modules'])|{'numpy','pynq','tokenizers'}
    missing=[]
    for mod,tree in trees.items():
        for n in ast.walk(tree):
            names=[x.name.split('.')[0] for x in n.names] if isinstance(n,ast.Import) else ([(n.module or '').split('.')[0]] if isinstance(n,ast.ImportFrom) else [])
            missing.extend((mod,name) for name in names if name and name not in trees and name not in allowed)
    assert not missing,missing
    symbols=next(t for t in symtable.symtable(s,'gate','exec').get_children() if t.get_name()=='main')
    assert next(t for t in symbols.get_children() if t.get_name()=='tracked_allocate').lookup('SHAPES').is_global()
    for r in json.loads((PKG/'HARDWARE_CLOSURE.json').read_text(encoding='utf-8'))['prerequisites']:assert sha(ROOT/r['path'])==r['sha256']
    rows=[dict(path=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(PKG.iterdir())]
    atomic(PKG/'SHA256SUMS',''.join(r['sha256']+'  '+r['path']+'\n' for r in rows).encode('ascii'))
    rows.append(dict(path='SHA256SUMS',bytes=(PKG/'SHA256SUMS').stat().st_size,sha256=sha(PKG/'SHA256SUMS')))
    atomic(PKG/'PACKAGE_MANIFEST.json',encoded(dict(schema='M392-isolated-SiLU-layer-v1',files=rows,file_count=len(rows),total_bytes=sum(r['bytes'] for r in rows))))
    value=dict(status='PASS_OFFLINE_SILU_LAYER_PREPARATION',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),component_raw_sha256=RAW,component_closure=prior,
               missing=missing,python310_syntax=True,file_count=len(rows),total_bytes=sum(r['bytes'] for r in rows),
               build_id='0x4D333537',PS_prefetch=False,parser_workers=1,workspace_bytes=6187008,extra_DMA_allowed=False,
               diagnostic_total_RSS_growth_bytes=256<<20,ordinary_available_margin_bytes=64<<20,production64MiB_unchanged=True,
               test_support_pending=True,board_run=False,numerical_pass=False,performance_pass=False)
    out=BASE/'runs/M392-silu-layer-preparation-02/RESULT.json';atomic(out,encoded(value),immutable=True);d=sha(out)
    sync('latest_m392_silu_layer_preparation',dict(status=value['status'],sha256=d,result=out.relative_to(ROOT).as_posix(),manifest_sha256=value['manifest_sha256']),
         f'## M392 SiLU工作缓冲单层接入准备（2026-10-04）\n\n组件原SHA {RAW}和闭合后，独立生成原M241单层loop，只将SiLU×up和下一mlp_down置于borrow scope，算法/五family/缩放重试不改。before/after DMA安全与pack/parse退出屏障，故障retain owner/七DMA/process。原256MiB共用停止预算含5.900390625MiB普通工作缓冲、64MiB普通余量/生产准入不改，0新增DMA。包SHA {value["manifest_sha256"]}，准备SHA {d}；missing0/3.10及同SHA硬件证据复用，尚需控制/回收支持，未上传或本级数值/性能。')
    print(json.dumps(value|{'result_sha256':d}))

if __name__=='__main__':main()
