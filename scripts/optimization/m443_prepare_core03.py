"""Same-constraint implementation is disabled until all new RTL cases close."""
import ast,json
from m351_workflow import ROOT,BASE,HERE,encoded,sha,sync
from m441_host_io08 import atomic

def main():
    rtl=BASE/'runs/M443-W2-W4-pair-pipeline-RTL-04/RESULT.json';r=json.loads(rtl.read_bytes())
    assert r['status'].startswith('PASS_') and [x['case'] for x in r['results']]==['W2_max','timeout','W4_max','q','gate_up','mlp_down']
    for n in ('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'):assert sha(rtl) in (ROOT/n).read_text(encoding='utf-8-sig')
    for row in r['results']:
        p=rtl.parent/(row['case']+'_RESULT.json');c=json.loads(p.read_bytes());assert sha(p)==row['sha256'] and c['status'].startswith('PASS_') and all(c['checks'].values())
        if row['case']!='timeout':
            assert c['build_id']=='0x4D343433' and c['original_rc']==0 and c['gate_rc']==0
        else:
            assert c['original_rc']==0 and c['gate_rc']==1 and c['snapshot_sha256']==sha(rtl.parent/'COMPILE.json')
        assert c['preparation_sha256']==sha(rtl.parent/'PREPARATION.json')
        for item in c['evidence']:assert sha(ROOT/item['path'])==item['sha256']
        for n in ('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'):assert sha(p) in (ROOT/n).read_text(encoding='utf-8-sig')
    numeric=BASE/'runs/M443-full-numeric-csim-03/RESULT.json';c=json.loads(numeric.read_bytes());assert c['status']=='PASS_M443_FULL_REAL_WEIGHT_CHAIN_CSIM03' and all(c['checks'].values())
    hpath=BASE/'runs/M443-pair-pipeline-preparation-03/RESULT.json';h=json.loads(hpath.read_bytes())
    for row in h['files']:assert sha(ROOT/row['path'])==row['sha256']
    out=ROOT/'tmp/m443_core_ooc_03';assert not out.exists();out.mkdir()
    project=ROOT/'tmp/m443_hls_project_03'
    assert not any(p.suffix in ('.rpt','.xml','.zip','.xpr','.dcp') for p in (project/'hls/impl').rglob('*') if p.is_file())
    tcl=out/'run_core_ooc.tcl';atomic(tcl,('open_project {'+project.as_posix()+'}\nopen_solution hls\nexport_design -rtl verilog -format ip_catalog -flow impl\nexit\n').encode('utf-8'),immutable=True)
    original=json.loads((BASE/'runs/M441-record-pipeline-core-OOC-preparation-01/RESULT.json').read_bytes())
    baseline=json.loads((BASE/'runs/M441-record-pipeline-core-OOC-closure-01/RESULT.json').read_bytes());assert baseline['status']=='PASS_M441_SAME_CONSTRAINT_CORE_ROUTED_TIMING'
    paths=[p for folder in (project/'hls/impl',project/'hls/syn') for p in sorted(folder.rglob('*')) if p.is_file()]+[tcl]
    pr=dict(status='PREPARED_M443_SAME_CONSTRAINT_CORE_OOC',build_id='0x4D343433',files=[dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p)) for p in paths],RTL_closed_sha256=sha(rtl),full_numerical_sha256=sha(numeric),header_source_sha256=sha(hpath),target_period_ns=4.8,original_constraint=original['original_constraint'],original_routed_resources=baseline['resources'],original_achieved_period_ns=baseline['timing']['CP_FINAL'],original_WNS_ns=baseline['timing_summary']['WNS_ns'],baseline_M441_sha256=sha(BASE/'runs/M441-record-pipeline-core-OOC-closure-01/RESULT.json'),wall_budget_s=28800,board=False)
    prep=BASE/'runs/M443-pair-pipeline-core-OOC-preparation-03/RESULT.json'
    controller=(HERE/'m441_core_ooc07.py').read_text(encoding='utf-8-sig')
    begin=controller.index('def ready():');end=controller.index('\n\ndef main():',begin)
    controller=controller[:begin]+'''def ready():
    path=BASE/'runs/M443-W2-W4-pair-pipeline-RTL-04/RESULT.json'
    r=json.loads(path.read_bytes());assert r['status'].startswith('PASS_') and len(r['results'])==6
    for name in ('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'):assert sha(path) in (ROOT/name).read_text(encoding='utf-8-sig')
    return path
'''+controller[end:]
    begin=controller.index("    policy=BASE/'runs/M441-core-admission07");end=controller.index('    p=synchronized(PREP',begin);controller=controller[:begin]+controller[end:]
    for a,b in [('tmp/m441_record_pipeline_02','tmp/m443_core_ooc_03'),('tmp/m441_hls_project_02','tmp/m443_hls_project_03'),('M441-record-pipeline-core-OOC-preparation-01','M443-pair-pipeline-core-OOC-preparation-03'),('PREPARED_M441_SAME_CONSTRAINT_CORE_OOC','PREPARED_M443_SAME_CONSTRAINT_CORE_OOC'),('latest_m441_core_OOC_preparation','latest_m443_core_OOC_preparation03'),('m441_core_ooc','m443_core_ooc'),('M441_CORE','M443_CORE')]:controller=controller.replace(a,b)
    controller=controller.replace("    raise SystemExit(rc)","    from m443_collect_core03 import main as collect\n    collect()\n    raise SystemExit(rc)")
    atomic(HERE/'m443_core_ooc03.py',controller.encode('utf-8'),immutable=True)
    collector=(HERE/'m441_collect_core_ooc07.py').read_text(encoding='utf-8-sig')
    for a,b in [('M441-record-pipeline-core-OOC-preparation-01','M443-pair-pipeline-core-OOC-preparation-03'),('tmp/m441_record_pipeline_02','tmp/m443_core_ooc_03'),('tmp/m441_hls_project_02','tmp/m443_hls_project_03'),('M441-record-pipeline-core-OOC-closure-01','M443-pair-pipeline-core-OOC-closure-03'),('latest_m441_record_pipeline_core_OOC','latest_m443_pair_pipeline_core_OOC03'),('0x4D343431','0x4D343433'),('PASS_M441_SAME_CONSTRAINT_CORE_ROUTED_TIMING','PASS_M443_SAME_CONSTRAINT_CORE_ROUTED_TIMING'),('CLOSED_M441_CORE_IMPLEMENTATION_FAILURE','CLOSED_M443_CORE_IMPLEMENTATION_FAILURE'),('original_M357','original_M441'),('原M357','原M441'),('M441 核心','M443 核心')]:collector=collector.replace(a,b)
    atomic(HERE/'m443_collect_core03.py',collector.encode('utf-8'),immutable=True)
    for name in ('m443_core_ooc03.py','m443_collect_core03.py'):ast.parse((HERE/name).read_bytes(),feature_version=(3,10))
    pr['files'] += [dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p)) for p in (HERE/'m443_core_ooc03.py',HERE/'m443_collect_core03.py',HERE/'m443_prepare_core03.py')]
    atomic(prep,encoded(pr),immutable=True)
    sync('latest_m443_core_OOC_preparation03',dict(status=pr['status'],result=prep.relative_to(ROOT).as_posix(),sha256=sha(prep),board=False),'## M443同约束核心布局布线准备03（2026-10-10）\n\nSHA '+sha(prep)+'；新完整RTL六项/完整417792数值/原递归源SHA通过，实际HLS03实现输入和原4.8ns XDC冻结，原M441资源作基线。8h有限、不kill，需一次明确Run后原时序/route/setup/hold/pulse全PASS才整壳；未上板或评价请求收益。')
    print(pr['status'],sha(prep))
if __name__=='__main__':main()
