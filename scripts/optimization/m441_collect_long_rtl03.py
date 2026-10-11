"""Saved-only complete-chain RTL adjudication with exact formal evidence."""
import hashlib
import json
import re
import sys
from m351_workflow import ROOT, BASE, atomic, encoded, sha, sync
from m356_collect_rtl import read_tv
from m357_uvm_log_evidence import evaluate


def main():
    variant,family,mode,revision=sys.argv[1:]
    assert variant in ('A','B') and family in ('gate_up','mlp_down','q') and mode in ('compile','zero','random') and revision == '03'
    out=ROOT/f'tmp/m441_long_{variant}_{family}_{revision}';sim=out/'verilog'
    prep=BASE/f'runs/M441-long-{variant}-{family}-RTL-preparation-{revision}/RESULT.json'
    p=json.loads(prep.read_bytes())
    for row in p['files']:assert sha(ROOT/row['path'])==row['sha256'],row['path']
    checks={};errors=[];done=None;metrics=[];queues=[];hist={}
    if mode=='compile':
        rc=json.loads((sim/'compile_exit.json').read_bytes())['compile_rc']
        log_path=sim/'compile_console.log';log=log_path.read_text(encoding='utf-8-sig',errors='replace')
        checks=dict(rc=rc==0,snapshot='Built simulation snapshot m441_trace' in log,no_error='ERROR:' not in log)
    else:
        assert revision=='03' and p['ARLEN_histogram_recorded']
        rc=json.loads((sim/(mode+'_exit.json')).read_bytes())['simulation_rc']
        log_path=sim/(mode+'.log');log=log_path.read_text(encoding='utf-8-sig',errors='replace')
        data=sim/(mode+'_result');prefix='rtl.m89x_runtime_kernel.autotvout_'
        def read(name):
            try:return read_tv(data/(prefix+name+'.dat'))
            except Exception as exc:errors.append(name+':'+repr(exc));return []
        expected=p['expected'];n=expected['output_words']
        payload=b''.join(x.to_bytes(8,'little') for x in read('rx_V_data_V'))
        checks=dict(rc=rc==0,full_output=payload==(out/'golden.bin').read_bytes(),
                    Build=read('ap_return')==[int(p['build_id'],16)],TLAST=read('rx_V_last_V')==[0]*(n-1)+[1])
        for field in ('keep','strb'):checks[field]=read('rx_V_'+field+'_V')==[255]*n
        clean,uvm=evaluate(sim,log);checks['uvm_clean']=clean
        checks['completed']='RTL Simulation : 1 / 1' in log and not re.search(r'ERROR:|Fatal:|M441 .*fatal|failed to start|necessary license',log)
        ds=re.findall(r'^M441_DONE cycles=(\d+) output=(\d+) tlast=(\d+)\s*$',log,re.M)
        checks['done_once']=len(ds)==1 and 0<int(ds[0][0])<=p['cycle_budget'] and ds[0][1:]==(str(n),'1')
        if len(ds)==1:done=dict(cycles=int(ds[0][0]),output_words=int(ds[0][1]),TLAST=int(ds[0][2]))
        def rows(prefix):return [{k:int(v) for k,v in re.findall(r'(\w+)=(\d+)',line)} for line in re.findall(r'^'+prefix+r'[^\r\n]+',log,re.M)]
        metrics=rows('M441_METRIC');queues=rows('M441_QUEUE')
        checks['four_shards']=len(metrics)==len(queues)==4 and sorted(r['shard'] for r in metrics)==sorted(r['shard'] for r in queues)==list(range(4))
        checks['MAC']=len(metrics)==4 and all(r['mac_calls']==expected['mac_calls_per_shard'] and r['iterations']==expected['iterations_per_shard'] for r in metrics)
        checks['reads']=len(metrics)==4 and all(r['R']==expected['weight_beats_per_shard'] and r['pending']==r['bad_RLAST']==r['bad_RRESP']==0 for r in metrics)
        checks['coverage']=len(queues)==4 and all(r['covered']==expected['weight_beats_per_shard'] for r in queues)
        h=rows('M441_ARLEN')
        for shard in range(4):
            hs=[r for r in h if r['shard']==shard];hist[str(shard)]={str(r['beats']):r['requests'] for r in hs}
        checks['ARLEN_histogram']=len(metrics)==4 and all(sum(hist[str(r['shard'])].values())==r['AR'] and sum(int(k)*v for k,v in hist[str(r['shard'])].items())==r['R'] and len(hist[str(r['shard'])])==len([hrow for hrow in h if hrow['shard']==r['shard']]) for r in metrics)
        if variant=='B':checks['bounded_queue_and_overlap']=len(queues)==4 and all(r['writes']==r['reads']==expected['weight_beats_per_shard'] and r['high']==34 and r['full_cycles']>0 and r['final']==0 and r['R_accepted_MAC']>0 for r in queues)
        output_sha=hashlib.sha256(payload).hexdigest()
    if mode!='compile':
        from m441_progress03 import validate_progress
        progress_proof=validate_progress(log,p,variant)
        checks.update(progress_proof['checks'])
    ok=all(checks.values()) and not errors
    r=dict(status=('PASS_M441_COMPLETE_RTL_COMPILED' if mode=='compile' else 'PASS_M441_COMPLETE_CHAIN_RTL_NUMERIC_AND_PROTOCOL') if ok else 'FAIL_M441_LONG_CHAIN_RTL',
           variant=variant,family=family,mode=mode,revision=revision,build_id=p['build_id'],original_rc=rc,checks=checks,errors=errors,
           preparation_sha256=sha(prep),log_sha256=sha(log_path),done=done,metrics=metrics,queues=queues,ARLEN_histograms=hist,
           RTL_run=mode!='compile',board=False,performance=False,promoted=False,run_authorized=ok and revision=='02')
    if mode!='compile':r.update(progress_proof=progress_proof,gate_rc=json.loads((sim/(mode+'_exit.json')).read_bytes()).get('gate_rc'),output_sha256=output_sha,reference_sha256=sha(out/'golden.bin'),uvm_evidence=uvm,
               evidence=[dict(path=q.relative_to(ROOT).as_posix(),sha256=sha(q)) for q in [sim/(mode+'.log'),sim/(mode+'_exit.json'),sim/(mode+'.args'),*sorted(data.glob('*.dat'))]])
    ev=BASE/f'runs/M441-long-{variant}-{family}-{mode}-{revision}/RESULT.json';atomic(ev,encoded(r),immutable=True)
    sync('latest_m441_long_'+variant+'_'+family+'_'+mode+revision,dict(status=r['status'],result=ev.relative_to(ROOT).as_posix(),sha256=sha(ev),build_id=r['build_id'],board=False),
         f'## M441 {variant}/{family}/{mode}/{revision} RTL证据闭合（2026-10-07）\n\nSHA {sha(ev)}；{r["status"]}，原rc{rc}；完整形状/真实权重，只按实际门禁证据范围裁决。03补周期/失败末态及延迟抽样，固定80M与全局停滞规则；原02 FAIL不改。0板端/新请求收益/晋级，M439FAIL不改。失败停本级，不通过不得开后级。')
    print(r['status'],sha(ev),checks)
    if not ok:raise SystemExit(1)
    if revision=='03':atomic(sim/(mode+'_validated.json'),encoded(dict(status=r['status'],sha256=sha(ev))),immutable=True)


if __name__=='__main__':main()
