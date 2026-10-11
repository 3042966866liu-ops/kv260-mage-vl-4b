"""Collect one saved local protocol result; never starts a simulator."""
import argparse
import json
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
from m441_protocol_evidence import clean_engine
from m441_boundary_evidence06 import validate_boundary as validate_max,validate_boundary_timeout as validate_timeout
from m441_boundary_control06 import PREP,OUT,NEG,verified_prep,RUNTIME_NAMES,require_validation,verify_compiled_snapshot


def main():
    ap=argparse.ArgumentParser();ap.add_argument('mode',choices=('compile','max','timeout'));a=ap.parse_args()
    p=verified_prep();sim=(NEG if a.mode=='timeout' else OUT)/'verilog'
    receipt_path=sim/(a.mode+'_exit.json');receipt=json.loads(receipt_path.read_bytes())
    policy=BASE/'runs/M441-boundary-control-preparation-06/RESULT.json';pol=json.loads(policy.read_bytes())
    assert sha(policy)==receipt['control_preparation_sha256'] and receipt['preparation_sha256']==sha(PREP)
    for row in pol['files']:assert sha(ROOT/row['path'])==row['sha256']
    log_path=sim/(a.mode+'_console.log' if a.mode=='compile' else a.mode+'.log')
    log=log_path.read_text(encoding='utf-8-sig',errors='replace');errors=[]
    try:
        if a.mode=='compile':
            checks=dict(original_rc=receipt['original_rc']==0 and receipt['gate_rc']==0,
                        no_wall_budget=not receipt['software_wall_budget_exceeded'],snapshot='Built simulation snapshot m441_max_trace' in log,
                        no_error=clean_engine(log));v=dict(checks=checks,accepted=all(checks.values()),details={})
            rows=receipt.get('snapshot_files',[])
            checks['compiled_artifacts']=bool(rows) and any(x['path'].endswith('/xsimk.exe') and not x['runtime_bookkeeping'] for x in rows)
            for row in rows:
                assert row['runtime_bookkeeping']==((ROOT/row['path']).name in RUNTIME_NAMES)
                if not row['runtime_bookkeeping']:assert sha(ROOT/row['path'])==row['sha256']
            v['accepted']=all(checks.values());v['details']['snapshot_files']=rows
            good='PASS_M441_BOUNDARY_COMPILED'
        elif a.mode=='timeout':
            pre=json.loads((NEG/'PREREQUISITE.json').read_bytes())
            maximum=require_validation('max');verify_compiled_snapshot()
            same=pre['same_compiled_candidate_snapshot'] and pre['source_preparation_sha256']==sha(PREP) and bool(pre['snapshot_files'])
            same=same and pre['max_result_sha256']==sha(maximum)
            same=same and any(x['copy'].endswith('/xsimk.exe') and not x['runtime_bookkeeping'] for x in pre['snapshot_files'])
            for row in pre['snapshot_files']:
                assert row['runtime_bookkeeping']==((ROOT/row['copy']).name in RUNTIME_NAMES)
                if not row['runtime_bookkeeping'] and (sha(ROOT/row['copy'])!=row['sha256'] or sha(ROOT/row['source'])!=row['sha256']):same=False
            v=validate_timeout(receipt,log,same);v['details']=dict(prerequisite=pre)
            good='PASS_M441_BOUNDARY_EXPECTED_TIMEOUT'
        else:
            verify_compiled_snapshot()
            v=validate_max(p,receipt,log,sim/'max_result',(OUT/'golden.bin').read_bytes(),OUT/'verilog')
            good='PASS_M441_BOUNDARY_RTL'
    except (KeyError,ValueError,OSError,OverflowError,AssertionError) as exc:
        v=dict(checks=dict(complete_saved_evidence=False),accepted=False,details={});errors.append(repr(exc))
    result=dict(status=good if v['accepted'] and not errors else 'FAIL_M441_PROTOCOL_'+a.mode.upper(),mode=a.mode,build_id=p['build_id'],
                original_rc=receipt['original_rc'],gate_rc=receipt['gate_rc'],checks=v['checks'],errors=errors,details=v['details'],
                preparation_sha256=sha(PREP),control_preparation_sha256=sha(policy),board=False,full_model=False,performance=False,promoted=False,
                scope='Maximum protocol fixture or expected watchdog failure only; zero scales are not model-quality or timing benefit evidence',
                evidence=[dict(path=path.relative_to(ROOT).as_posix(),sha256=sha(path)) for path in [receipt_path,log_path,sim/(a.mode+'_console.log'),sim/(a.mode+'.args')] if path.is_file()])
    if a.mode=='max':result['evidence'] += [dict(path=path.relative_to(ROOT).as_posix(),sha256=sha(path)) for path in sorted((sim/'max_result').glob('*.dat'))]
    names={'compile':'M441-boundary-compile-06','max':'M441-boundary-rtl-06','timeout':'M441-boundary-timeout-06'}
    ev=BASE/'runs'/names[a.mode]/'RESULT.json';atomic(ev,encoded(result),immutable=True)
    sync('latest_m441_boundary06_'+a.mode,dict(status=result['status'],result=ev.relative_to(ROOT).as_posix(),sha256=sha(ev),board=False),
         f'## M441 最大协议{a.mode}闭合（2026-10-07）\n\nSHA {sha(ev)}；{result["status"]}，原rc{receipt["original_rc"]}/gate{receipt["gate_rc"]}；原结果仅收集，不重跑。0板端/完整模型/性能；失败停本级，最大协议与timeout均未闭合不得整壳。')
    print(result['status'],sha(ev),v['checks'])
    if not v['accepted'] or errors:raise SystemExit(1)


if __name__=='__main__':main()
