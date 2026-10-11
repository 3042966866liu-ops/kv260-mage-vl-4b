"""Prepare or explicitly run same-constraint core implementation, never board."""
import argparse
import json
import subprocess
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
from m441_protocol_control import synchronized

OUT=ROOT/'tmp/m441_record_pipeline_02'
PROJECT=ROOT/'tmp/m441_hls_project_02'
PREP=BASE/'runs/M441-record-pipeline-core-OOC-preparation-01/RESULT.json'

def ready():
    path=BASE/'runs/M441-offline-continuation-01/RESULT.json'
    r=synchronized(path,'PASS_M441_COMPLETE_LONG_CHAIN_RTL_COMPARISON','latest_m441_offline_continuation_result')
    assert not r['errors'] and len(r['comparisons'])==6 and all(x['pass_gate'] is True for x in r['comparisons'])
    assert {(x['family'],x['mode']) for x in r['comparisons']}=={(f,m) for f in ('gate_up','mlp_down','q') for m in ('zero','random')}
    return path

def prepare():
    assert not PREP.exists()
    old=BASE/'runs/M357-core-ooc-01/RESULT.json';r=json.loads(old.read_bytes())
    assert r['status']=='PASS_ISOLATED_CORE_ROUTED_TIMING' and r['target_period_ns']==4.8
    for row in r['evidence']:assert sha(ROOT/row['path'])==row['sha256']
    impl=PROJECT/'hls/impl'
    allowed={'.png','.tcl','.v','.vhd','.mdd','.yaml','.txt','.c','.h'}
    files=sorted(p for p in impl.rglob('*') if p.is_file())
    assert files
    for p in files:
        assert p.suffix in allowed or p.name=='Makefile',p
    for p in (PROJECT/'hls/syn/verilog').glob('*.v'):assert sha(p)==sha(impl/'verilog'/p.name)
    assert not (OUT/'core_ooc_console.log').exists()
    tcl=OUT/'run_core_ooc.tcl'
    atomic(tcl,f'open_project {{{PROJECT.as_posix()}}}\nopen_solution hls\nexport_design -rtl verilog -format ip_catalog -flow impl\nexit\n'.encode(),immutable=True)
    # Reuse the saved-only routed-report validator, with explicit candidate
    # identity/path substitutions. No original source or evidence is changed.
    original=HERE/'m439_collect_ooc.py';s=original.read_text(encoding='utf-8')
    assert sha(original)=='1946382d2257dec823495e4bde22963ff18808e6b9db6b9f328c8f7976af2f4e', 'Review original validator SHA before adapting'
    s=s.replace('M439-record-load-core-OOC-preparation-01','M441-record-pipeline-core-OOC-preparation-01')
    s=s.replace('m439_record_load_02','m441_record_pipeline_02').replace('m439_hls_project_02','m441_hls_project_02')
    s=s.replace('M439-record-load-core-OOC-closure-01','M441-record-pipeline-core-OOC-closure-01')
    s=s.replace('latest_m439_record_load_core_OOC_closure','latest_m441_record_pipeline_core_OOC')
    s=s.replace('0x4D343339','0x4D343431').replace('M439','M441')
    s=s.replace('Keep single-record version, no next-record pipeline.','Keep frozen bounded-record pipeline; no extra experiment.')
    collector=HERE/'m441_collect_core_ooc.py';atomic(collector,s.encode('utf-8'),immutable=True)
    files += [PROJECT/'hls.app',PROJECT/'hls/hls.aps',PROJECT/'hls/hls.directive',
              OUT/'hls/mage_prefill_m89x_runtime/mage_prefill_m89x_runtime.cpp',tcl,HERE/'m441_core_ooc.py',collector]
    constraint=ROOT/'tmp/m357_hls_project_02/hls/impl/verilog/m89x_runtime_kernel.xdc'
    v=dict(status='PREPARED_M441_SAME_CONSTRAINT_CORE_OOC',build_id='0x4D343431',
           files=[dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p)) for p in files],
           original_core_sha256=sha(old),original_routed_resources=r['resources'],original_WNS_ns=r['wns_ns'],original_achieved_period_ns=r['achieved_period_ns'],
           original_constraint=dict(path=constraint.relative_to(ROOT).as_posix(),sha256=sha(constraint)),
           reused_validator_sha256=sha(original),target_period_ns=4.8,part='xck26-sfvc784-2LV-c',core_only=True,full_shell=False,board=False,implementation_started=False,
           stop='Long-chain failure blocks execution. Routed resource/timing failure stops candidate without relaxing the clock.')
    assert v['original_constraint']['sha256']=='63ea420c7cd5b85ab6b683b1f04e1509facc1a68929ecc2c9896eeb8b79288b4'
    atomic(PREP,encoded(v),immutable=True)
    sync('latest_m441_core_OOC_preparation',dict(status=v['status'],result=PREP.relative_to(ROOT).as_posix(),sha256=sha(PREP),board=False),
         f'## M441 同约束核级时序准备（2026-10-07）\n\nSHA {sha(PREP)}；生成输入与综合Verilog同SHA，原M357 4.8ns/XDC/part保持。长链全部裁决成功才允许核OOC；仅准备、0实现/整壳/板端。实际资源、setup/hold/pulse与route不通过即关闭，不能放宽时钟。')
    print(v['status'],sha(PREP),flush=True)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('mode',choices=('Prepare','Check','Run'));ap.add_argument('--enable',action='store_true');a=ap.parse_args()
    if a.mode=='Prepare':prepare();return
    if a.mode=='Check':
        try:print('READY',sha(ready()))
        except (AssertionError,RuntimeError,KeyError,OSError) as exc:print('BLOCKED_BEFORE_TOOL',str(exc))
        return
    assert a.enable,'Default disabled: --enable required'
    full=ready()
    p=synchronized(PREP,'PREPARED_M441_SAME_CONSTRAINT_CORE_OOC','latest_m441_core_OOC_preparation')
    for row in p['files']:assert sha(ROOT/row['path'])==row['sha256']
    assert not (OUT/'core_ooc_console.log').exists() and not (OUT/'core_ooc_exit.json').exists(),'Existing attempt: collect only'
    assert not any(x.suffix in {'.rpt','.xml','.zip','.xpr','.dcp'} for x in (PROJECT/'hls/impl').rglob('*') if x.is_file())
    command=['D:/AMDDesignTools/2026.1/Vitis/bin/vitis-run.bat','--mode','hls','--tcl',str(OUT/'run_core_ooc.tcl'),'--log',str(OUT/'m441_core_ooc')]
    atomic(OUT/'core_ooc_start.json',encoded(dict(preparation_sha256=sha(PREP),full_chain_sha256=sha(full))),immutable=True)
    with (OUT/'core_ooc_console.log').open('xb') as stream:
        process=subprocess.Popen(command,cwd=ROOT/'tmp',stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
        print('M441_CORE_OOC_STARTED pid='+str(process.pid),flush=True)
        rc=process.wait()
    atomic(OUT/'core_ooc_exit.json',encoded(dict(hls_rc=rc)),immutable=True)
    print('M441_CORE_OOC_RETURN rc='+str(rc),flush=True)
    raise SystemExit(rc)

if __name__=='__main__':main()
