"""Resume support only on the byte-verified unpublished route packet; no repackaging."""
from m436_route_prepare import *

def main():
    for folder in (OLD,PKG):
        manifest=json.loads((folder/'PACKAGE_MANIFEST.json').read_bytes())
        assert {p.name for p in folder.iterdir()}=={r['path'] for r in manifest['files']}|{'PACKAGE_MANIFEST.json'}
        for row in manifest['files']:
            assert (folder/row['path']).stat().st_size==row['bytes'] and sha(folder/row['path'])==row['sha256']
    rows=json.loads((PKG/'PACKAGE_MANIFEST.json').read_bytes())['files']
    manifest_sha=sha(PKG/'PACKAGE_MANIFEST.json')
    deps=json.loads((PKG/'DEPENDENCY_CLOSURE.json').read_bytes())
    assembly=(PKG/'m435_assemble.py').read_text(encoding='utf-8')
    control=(HERE/'m436_control06.ps1').read_text(encoding='utf-8')
    receipt=json.loads((ROOT/'tmp/m43602/bash_syntax_receipt.json').read_bytes())
    # Extract actual routes, not a hand-created route fixture.
    gate_ast=ast.parse((PKG/'m435_gate.py').read_text(encoding='utf-8'))
    main_fn=next(n for n in gate_ast.body if isinstance(n,ast.FunctionDef) and n.name=='main')
    assignments=[n for n in main_fn.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='EVIDENCE' for t in n.targets)]
    assert len(assignments)==1 and ast.literal_eval(assignments[0].value.args[0])==EVIDENCE
    export_ast=ast.parse((PKG/'m435_export.py').read_text(encoding='utf-8'))
    exp=next(n for n in export_ast.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='OUTPUT' for t in n.targets))
    assert ast.literal_eval(exp.value.args[0])==EVIDENCE+'/BOARD_RESULT.json'
    runner=(PKG/'run_m435.sh').read_text(encoding='utf-8')
    assert f'[[ ! -e {EVIDENCE} ]] || exit 67' in runner
    assert REMOTE!=EVIDENCE and not Path(EVIDENCE).is_relative_to(Path(REMOTE)) and not Path(REMOTE).is_relative_to(Path(EVIDENCE))
    assert f"$remote='{REMOTE}'" in control and OLD_REMOTE not in control
    assert f'OLD=Path({OLD_REMOTE!r})' in assembly
    assert sha(PKG/'m435_trials.py')==sha(OLD/'m435_trials.py')
    assert sha(PKG/'m435_io_observer.py')==sha(OLD/'m435_io_observer.py')
    assert receipt['exit_code']==0 and receipt['runner_sha256']==sha(PKG/'run_m435.sh')

    w=load_module('m436_route_workflow',HERE/'m436_workflow02.py')
    r=json.loads((ROOT/'tmp/m43501/export_fixture03/collected/BOARD_RESULT.json').read_bytes())
    r['manifest_sha256']=manifest_sha
    for sample in r['samples']:
        sample['before_cache']=dict(cache_entries=26,cache_bytes=66699264,cache_within_budget=True)
        sample['after_cache']=dict(cache_entries=25,cache_bytes=60000000,cache_within_budget=True)
    assert w.check(r)==r
    checks=[]
    for key,value in [('cache_entries',27),('cache_entries',-1),('cache_entries',True),('cache_bytes',66699265),('cache_within_budget',False)]:
        bad=copy.deepcopy(r);bad['samples'][0]['after_cache'][key]=value
        try:w.check(bad)
        except ValueError:checks.append(key+':'+repr(value))
        else:raise AssertionError('Bad cache accepted')
    fixture=ROOT/'tmp/m43602/route_support'
    fixture.mkdir(parents=True,exist_ok=False)
    exporter=load_module('m436_route_exporter',PKG/'m435_export.py')
    exporter.OUTPUT=fixture/'producer.json'
    def export(value):
        exporter.OUTPUT.write_bytes(encoded(value));out=io.StringIO()
        with patch.object(exporter.os,'geteuid',lambda:0,create=True),patch.object(exporter.time,'sleep',lambda *_:None),contextlib.redirect_stdout(out):exporter.emit_saved()
        return out.getvalue()+f'M435_DONE gate_rc={value["gate_return_code"]} export_rc=0\n'
    good=export(r);assert w.decode(good)[2]==r
    log=fixture/'run.log';log.write_text(good,encoding='utf-8');notes=[];dest=fixture/'collected/BOARD_RESULT.json'
    with patch.object(w,'OUT',dest),patch.object(w,'sync',lambda *args:notes.append(args)),contextlib.redirect_stdout(io.StringIO()):w.collect(log)
    assert dest.read_bytes()==encoded(r) and notes[0][0]=='latest_m436_IO_board'
    assert w.OUT==BASE/'runs/M436-IO-observation-board-02/BOARD_RESULT.json'
    fail=dict(r,status='FAIL',gate_return_code=1,errors=['Explicit synthetic early failure'])
    assert w.decode(export(fail))[2]==fail
    for label,text in [('missing',good[:good.index('M435_RESULT_CHUNK=1/')]),('duplicate',good+good),('unordered',good.replace('M435_RESULT_CHUNK=1/','M435_RESULT_CHUNK=0/')),('SHA',good.replace(hashlib.sha256(encoded(r)).hexdigest(),'0'*64))]:
        try:w.decode(text)
        except ValueError:checks.append(label)
        else:raise AssertionError('Corrupt export accepted')

    with tempfile.TemporaryDirectory(prefix='m436-route-assembly-',dir=ROOT/'tmp') as temp:
        src=Path(temp)/'old';dst=Path(temp)/'new';shutil.copytree(OLD,src);dst.mkdir()
        for name in w.upload_names():shutil.copyfile(PKG/name,dst/name)
        actual=assembly.replace('OLD=Path('+repr(OLD_REMOTE)+')','OLD=Path('+repr(src.as_posix())+')')
        with patch.object(sys,'argv',[str(dst/'m435_assemble.py'),manifest_sha]),contextlib.redirect_stdout(io.StringIO()):exec(compile(actual,str(PKG/'m435_assemble.py'),'exec'),dict(__file__=str(dst/'m435_assemble.py')))
        assert {p.name:sha(p) for p in dst.iterdir()}=={p.name:sha(p) for p in PKG.iterdir()}
    receipt_root=fixture/'transfer_fixture';receipt_base=receipt_root/'deployment/mage_vl4b/optimization_v1'
    (receipt_base/'candidates/M435-weight-read-observation-02').mkdir(parents=True)
    shutil.copyfile(OLD/'PACKAGE_MANIFEST.json',receipt_base/'candidates/M435-weight-read-observation-02/PACKAGE_MANIFEST.json')
    folder=receipt_root/'tmp/m43602/board';folder.mkdir(parents=True)
    for name in w.upload_names():
        size=(PKG/name).stat().st_size;count=(size+899)//900;prefix='upload_'+name.replace('.','_')
        (folder/(prefix+'_final.log')).write_text('M212_CHUNKED_FILE_PASS '+sha(PKG/name),encoding='utf-8')
        for i in range(1,count+1):(folder/(prefix+f'_chunk_{i:03d}.log')).write_text(f'M212_CHUNK_PASS {i} {count} {min(i*900,size)} ',encoding='utf-8')
    (folder/'assembly.log').write_text(f'M435_ASSEMBLY_PASS {manifest_sha} {len(rows)} {sum(x["bytes"] for x in rows)}',encoding='utf-8')
    (folder/'syntax.log').write_text('__M435_SYNTAX_RC_0__',encoding='utf-8')
    transfer_notes=[]
    with patch.object(w,'ROOT',receipt_root),patch.object(w,'BASE',receipt_base),patch.object(w,'sync',lambda *args:transfer_notes.append(args)),contextlib.redirect_stdout(io.StringIO()):w.transfer()
    assert transfer_notes[0][0]=='latest_m436_route_transfer'
    saved=receipt_base/'runs/M436-route-transfer-01/RESULT.json';assert saved.exists()
    # Recorded module closure binds every local source after route repair.
    assert all(deps['files'][p.stem]==sha(p) for p in PKG.glob('*.py'))
    record=dict(status='PASS_M436_ROUTE_ISOLATION_AND_HOST_SUPPORT_ONLY',manifest_sha256=manifest_sha,
                candidate_remote=REMOTE,evidence_remote=EVIDENCE,assembly_source_remote=OLD_REMOTE,
                assembly_source_manifest_sha256=sha(OLD/'PACKAGE_MANIFEST.json'),
                original_packet_rejected_before_hardware='Control packet/evidence path collision; no Run is allowed for the uploaded packet02',
                original_control_sha256=sha(HERE/'m436_control_resume05.ps1'),
                host_sources={name:sha(HERE/name) for name in ('m436_control06.ps1','m436_workflow02.py')},
                actual_route_AST=True,actual_export_collect_PASS_FAIL=True,collector_negative_checks=checks,
                actual_same_SHA_assembly=True,actual_transfer_receipt_function=True,bash_n=True,local_closure_hashes=True,
                inherited_recursive_missing=deps['missing'],file_count=len(rows),total_bytes=sum(x['bytes'] for x in rows),
                fixtures_explicitly_synthetic=True,model_or_PL_changed=False,board_run=False,performance_pass=False,temperature_measurement_enabled=False)
    out=BASE/'runs/M436-route-support-01/RESULT.json';atomic(out,encoded(record),immutable=True)
    sync('latest_m436_route_support',dict(status=record['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out),manifest_sha256=manifest_sha),
         f'## M436 执行前目录碰撞拒绝与独立路径修正（2026-10-07）\n\nSHA {sha(out)}，新packet03 manifest {manifest_sha}。旧控制把候选根与不可变结果根都设为{OLD_REMOTE}，因此执行前拒绝旧packet02，不启动Run/Overlay/模型/DMA。新候选根{REMOTE}、结果根{EVIDENCE}严格分离；原packet02/日志保留，仅从完整同SHA传输源按白名单复用。实际gate/export/runner/control路径AST、原export→collector PASS/FAIL及9负例、实际assembly/transfer回执函数、bash-n、所有local依赖SHA及控制自测通过；fixture明确synthetic，原模型/双B/数值/缓存上限/生命周期不改。旧packet02完整传输并三记录同步后才上传新packet03；不测温、不作性能或晋级。')
    print('M436_ROUTE_SUPPORT_SYNC',sha(out),manifest_sha)


if __name__=='__main__':main()
