"""Reuse exact saved M355 complete references and real weight windows."""
import importlib.util
import json
import struct
import sys
from m351_workflow import ROOT, BASE, HERE, atomic, encoded, sha, sync
from m355_reference import activation, digest

OUT=ROOT/'tmp/m441_full_numeric_01'
PROJECT=ROOT/'tmp/m441_full_csim_project_01'


def identity(p):
    s=p.stat();return (s.st_size,s.st_mtime_ns,s.st_ctime_ns)


def main():
    assert not OUT.exists() and not PROJECT.exists()
    board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    hls=BASE/'runs/M441-record-pipeline-hls-02/RESULT.json'
    hr=json.loads(hls.read_bytes());assert hr['status']=='PASS_M441_HLS_RESOURCE_AND_MAC_GUARD'
    assert board['latest_m441_record_pipeline_hls']['sha256']==sha(hls)
    assert all(sha(hls) in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    prior=BASE/'candidates/M355-device-phase-01/CASE_CONTRACT.json'
    spec=json.loads(prior.read_bytes())
    saved=BASE/'runs/M355-device-phase-board-01/BOARD_RESULT.json'
    br=json.loads(saved.read_bytes())
    assert br['status']=='PASS_STABLE_CHAIN_DEVICE_PHASE_DIAGNOSTIC' and br['contract_sha256']==sha(prior)
    release=ROOT/'release_staging/kv260-mage-vl-4b-prebuilt-install-20260926-v7'
    layout_path=release/spec['layout_path'];assert sha(layout_path)==spec['layout_sha256']
    layout=json.loads(layout_path.read_bytes())
    manifest_files={r['path']:r for r in layout['files']}
    cp=ROOT/spec['stable_sources']['runtime/contract_runtime.py']['path']
    assert sha(cp)==spec['stable_sources']['runtime/contract_runtime.py']['sha256']
    module_spec=importlib.util.spec_from_file_location('m441_frozen_contract',cp)
    module=importlib.util.module_from_spec(module_spec);sys.modules[module_spec.name]=module;module_spec.loader.exec_module(module)
    prep=BASE/'runs/M441-record-pipeline-preparation-02/RESULT.json';p=json.loads(prep.read_bytes())
    chain_contract=ROOT/'deployment/mage_vl4b/m175_m120_fixed_text_candidate/contracts/M126_LANGUAGE_RUNTIME_CONTRACT_RESULT.json'
    all_chains=json.loads(chain_contract.read_bytes())['chains']
    cases=[]
    for ordinal, family in enumerate(('gate_up','mlp_down','q')):
        case=next(c for c in spec['cases'] if c['chain']['layer']==0 and c['chain']['family']==family)
        chain=case['chain'];assert chain==all_chains[chain['chain_index']]
        assert any(c['chain']==chain for c in p['plan']['cases'])
        canonical=digest(json.dumps(chain,sort_keys=True,separators=(',',':')).encode())
        assert canonical==case['chain_sha256']
        tx=next(t for t in br['transactions'] if t['chain_index']==chain['chain_index'])
        assert tx['full_output_exact'] and tx['output_sha256']==case['expected_ftz_sha256']
        packet=module.pack_chain_input(chain,activation(chain['groups']),case['base_words'],0)
        assert len(packet)==chain['input_bytes'] and digest(packet)==case['packet_sha256']
        golden_path=BASE/f'runs/M355-device-phase-preparation-01/golden/{chain["chain_index"]}.bin'
        golden=golden_path.read_bytes()
        assert len(golden)==chain['output_bytes'] and digest(golden)==case['expected_ftz_sha256']
        windows=[];sources=[]
        for row in case['windows']:
            path=layout_path.parent/row['file'];before=identity(path)
            assert before[0]==row['file_bytes']==manifest_files[row['file']]['bytes']
            with path.open('rb') as stream:
                stream.seek(case['base_words']*16);raw=stream.read(case['window_bytes_per_port'])
            assert identity(path)==before and len(raw)==case['window_bytes_per_port'] and digest(raw)==row['sha256']
            windows.append(raw);sources.append(dict(path=path.relative_to(ROOT).as_posix(),identity_before_after=before,window_sha256=digest(raw),whole_file_sha_rehashed_now=False))
        raw=b'M441FUL1'+struct.pack('<5I',int(chain['config_u32'],16),chain['descriptor_count'],len(packet),len(golden),len(windows[0]))+packet+b''.join(windows)+golden
        dest=OUT/f'case{ordinal}.bin';atomic(dest,raw,immutable=True)
        cases.append(dict(ordinal=ordinal,family=family,chain=chain,fixture_path=dest.relative_to(ROOT).as_posix(),fixture_sha256=sha(dest),
                          packet_sha256=digest(packet),golden_sha256=digest(golden),saved_board_transaction=tx['label'],sources=sources,
                          original_real_weight_windows=True,full_size_rows=True,synthetic_or_tiled_weights=False,
                          deterministic_input=True,model_quality_input=False))
        print('M441_FROZEN_FULL_CASE',family,chain['output_bytes'],flush=True)
    source_root=ROOT/'tmp/m441_record_pipeline_02'
    for row in p['files']:
        src=ROOT/row['path'];assert sha(src)==row['sha256']
        if src.suffix in ('.cpp','.hpp','.h'): atomic(OUT/'source'/src.relative_to(source_root),src.read_bytes(),immutable=True)
    tb=HERE/'m441_full_chain_tb.cpp';atomic(OUT/'m441_full_chain_tb.cpp',tb.read_bytes(),immutable=True)
    tcl=f'''set root {{{OUT.as_posix()}}}
set project {{{PROJECT.as_posix()}}}
if {{[file exists $project]}} {{error "Existing full CSim: collect only"}}
set ::env(M441_FULL_FIXTURE_ROOT) $root
open_project $project
set_top m89x_runtime_kernel
add_files [file join $root source hls mage_prefill_m89x_runtime mage_prefill_m89x_runtime.cpp]
add_files -tb [file join $root m441_full_chain_tb.cpp] -cflags "-I[file join $root source hls mage_prefill_m89x_runtime]"
open_solution hls -flow_target vivado
set_part {{xck26-sfvc784-2LV-c}}
create_clock -period 4.8 -name default
set_clock_uncertainty 1.3
config_compile -pipeline_loops 0
csim_design -clean -O
exit
'''
    atomic(OUT/'run_m441_full_csim.tcl',tcl.encode('utf-8'),immutable=True)
    r=dict(status='PREPARED_M441_FULL_REAL_WEIGHT_CSIM',build_id=p['build_id'],hls_sha256=sha(hls),source_preparation_sha256=sha(prep),
           prior_contract_sha256=sha(prior),saved_reference_board_sha256=sha(saved),layout_sha256=sha(layout_path),cases=cases,
           golden_recomputed=False,weight_windows_sha_exact=True,whole_weights_not_rehashed=True,
           optimized_Csim_flag_documentation='https://docs.amd.com/r/en-US/ug1399-vitis-hls/Project-Commands',
           files=[dict(path=q.relative_to(ROOT).as_posix(),sha256=sha(q),bytes=q.stat().st_size) for q in sorted(OUT.rglob('*')) if q.is_file()],
           csim=False,RTL=False,board=False,performance=False,promoted=False)
    ev=BASE/'runs/M441-full-numeric-preparation-01/RESULT.json';atomic(ev,encoded(r),immutable=True)
    sync('latest_m441_full_numeric_preparation',dict(status=r['status'],result=ev.relative_to(ROOT).as_posix(),sha256=sha(ev),build_id=r['build_id'],board=False),
         f'## M441 完整尺寸真实长链数值准备（2026-10-07）\n\nSHA {sha(ev)}；原M355已实板核对的layer0 gate_up W4 G40/D10、down W4 G152/D2、Q W2 G40/D2完整窗口/输出SHA复用，当前M126合同逐项相同，0合成/重复权重或重算参考。输入为固定非零T32而非模型质量样例。3夹具/完整descriptor行数，下一步优化编译C仿真，仍不能证明RTL34字队列/读算重叠/性能。0板端/晋级。')
    print(r['status'],sha(ev))


if __name__=='__main__': main()
