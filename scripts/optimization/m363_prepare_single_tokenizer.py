"""One diagnostic correction only; leave original production loader unchanged."""
import ast
import json
import shutil
import m351_workflow as w
from m358_prepare_capacity import replace_once

PKG=w.BASE/'candidates/M363-common-load-observer-01'

def main():
    assert not PKG.exists()
    prior=w.BASE/'runs/M362-load-comparison-closure-01/RESULT.json';r=json.loads(prior.read_text(encoding='utf-8'))
    assert r['status']=='BOTH_VARIANTS_REJECT_RESERVE_INVESTIGATE_COMMON_LOAD' and not r['capacity_unlocked']
    for name in ('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'):assert w.sha(prior) in (w.ROOT/name).read_text(encoding='utf-8-sig')
    old=w.BASE/'candidates/M362-common-load-observer-01';PKG.mkdir(parents=True)
    for p in old.iterdir():
        if p.name=='PACKAGE_MANIFEST.json':continue
        target=PKG/p.name.replace('m362','m363')
        if p.suffix in ('.py','.sh'):content=p.read_text(encoding='utf-8').replace('M362','M363').replace('m362','m363').encode('utf-8')
        else:content=p.read_bytes()
        w.atomic(target,content)
    probe=PKG/'m363_load_only_probe.py';before=probe.read_text(encoding='utf-8')
    after=replace_once(before,"        patch(tokenizers,'Tokenizer',tokenizer_proxy(original_tokenizer,observed_from_file))","        from m363_tokenizer_once import ValidatedTokenizerOnce\n        tokenizer_once=ValidatedTokenizerOnce(observed_from_file)\n        patch(tokenizers,'Tokenizer',tokenizer_proxy(original_tokenizer,tokenizer_once.from_file))")
    after=replace_once(after,"        mark('after-tokenizer-asset-preconstruction')","        mark('after-tokenizer-preconstruction-retained-for-original-loader')")
    anchor="        loaded = mark('complete-runtime-loaded-retained')"
    assert anchor in after
    after=replace_once(after,anchor,"        result['tokenizer_single_parse_reused']=bool(tokenizer_once.parse_count==1 and tokenizer_once.reuse_count==1 and tokenizer_once.cached is None and id(engine.tokenizer)==tokenizer_once.object_identity)\n        if not result['tokenizer_single_parse_reused']: raise RuntimeError('Original loader tokenizer identity differs')\n"+anchor)
    assert 'tokenizer_once.from_file' in after and 'observed_from_file=observe_call(original_tokenizer.from_file' in after
    ast.parse(after,feature_version=(3,10));w.atomic(probe,after.encode('utf-8'))
    shutil.copyfile(w.HERE/'m363_assemble.py',PKG/'m363_assemble.py')
    shutil.copyfile(w.HERE/'m363_tokenizer_once.py',PKG/'m363_tokenizer_once.py')
    rows=[dict(path=p.name,bytes=p.stat().st_size,sha256=w.sha(p)) for p in sorted(PKG.iterdir())]
    w.atomic(PKG/'PACKAGE_MANIFEST.json',w.encoded(dict(schema='m363-one-diagnostic-tokenizer-correction',files=rows,file_count=len(rows),total_bytes=sum(x['bytes'] for x in rows))))
    for name in ('m362_collect_load_comparison.py','m362_control.ps1','m362_verify_support.py'):
        text=(w.HERE/name).read_text(encoding='utf-8').replace('M362','M363').replace('m362','m363')
        if name=='m362_collect_load_comparison.py':
            text=text.replace("if x['name']=='tokenizer.from_file'])==2","if x['name']=='tokenizer.from_file'])==1").replace("[dict(name='tokenizer.from_file')]*2","[dict(name='tokenizer.from_file')]*1")
        if name=='m362_control.ps1':
            # Upload only new bytes; old dependencies are copied by the versioned hash-checked assembler.
            text=text.replace(" foreach($taskName in (@('PACKAGE_MANIFEST.json')+@($taskManifest.files|ForEach-Object path))){"," $taskOldManifest=Get-Content -LiteralPath (Join-Path $taskRoot 'deployment/mage_vl4b/optimization_v1/candidates/M362-common-load-observer-01/PACKAGE_MANIFEST.json') -Raw -Encoding UTF8|ConvertFrom-Json\n $taskOldHashes=@($taskOldManifest.files|ForEach-Object sha256)\n $taskDelta=@($taskManifest.files|Where-Object {$_.sha256 -notin $taskOldHashes}|ForEach-Object path)\n foreach($taskName in (@('PACKAGE_MANIFEST.json')+$taskDelta)){")
            text=text.replace(" & $taskUart -Command \"sudo -n bash -n $taskRemote/run_m363_load_only.sh\" -LogPath 'tmp/m363_board/root_syntax.log'", " & $taskUart -Command \"sudo -n /usr/local/share/pynq-venv/bin/python -B $taskRemote/m363_assemble.py $taskDigest\" -LogPath 'tmp/m363_board/assembly.log' -TimeoutSeconds 30 -MarkerPrefix '__M363_ASSEMBLY_RC_'\n & $taskUart -Command \"sudo -n bash -n $taskRemote/run_m363_load_only.sh\" -LogPath 'tmp/m363_board/root_syntax.log'")
        if name=='m362_verify_support.py':
            text=text.replace("assert 'Duplicate original-buffer free refused' not in src", "assert 'tokenizer_once.from_file' in src\n    assert 'after-tokenizer-preconstruction-retained-for-original-loader' in src\n    assert 'Duplicate original-buffer free refused' not in src")
            text=text.replace("ordered_cases=['A1','B1','B2','A2'],no_cache_eviction=True", "ordered_cases=['A1','B1'],single_change='Reuse pre-Overlay validated tokenizer in original M243 load; one parse and original object identity',no_cache_eviction=True")
            text=text.replace('按A-B-B-A逐例只加载','仅A1/B1逐例只加载').replace('稳定/候选仅bit路径变化，原35项完整SHA及构造政策保持','诊断仅消除额外tokenizer重复构造：前置解析对象供原M243复用，身份变化拒绝；稳定/候选仅bit路径变化，原35项完整SHA保持')
        w.atomic(w.HERE/name.replace('m362','m363'),text.encode('utf-8'))
    for name in ('m362_observers.py','m362_package_identity.py'):shutil.copyfile(w.HERE/name,w.HERE/name.replace('m362','m363'))
    result=dict(status='PREPARED_ONE_DIAGNOSTIC_CORRECTION_PENDING_SUPPORT',prior_closure_sha256=w.sha(prior),manifest_sha256=w.sha(PKG/'PACKAGE_MANIFEST.json'),files=len(rows),bytes=sum(x['bytes'] for x in rows),production_source_changed=False,original_35_full_asset_hashes_preserved=True,pre_overlay_tokenizer_parse_preserved=True,original_runtime_receives_same_validated_tokenizer=True,extra_temporary_tokenizer_omitted=True,capacity_proven=False,performance_pass=False,board_executed=False,planned_cases=['A1','B1'],note='Correct diagnostic duplicate construction, not a proven production optimization or CMA repair; stop expansion if actual retained capacity still fails')
    out=w.BASE/'runs/M363-single-tokenizer-preparation-01/RESULT.json';w.atomic(out,w.encoded(result),immutable=True);print(json.dumps(result))

if __name__=='__main__':main()
