"""Saved-only exact-output/address coverage/protocol collection."""
import json,re,sys,hashlib,collections
from m351_workflow import ROOT,BASE,atomic,encoded,sha,sync
from m356_collect_rtl import read_tv
from m357_uvm_log_evidence import evaluate

def main():
    tag,mode=sys.argv[1:];assert tag in ('candidate_w2','baseline_w4','candidate_w4') and mode in ('compile','zero','random')
    out=ROOT/('tmp/m439_'+tag+'_01');sim=out/'verilog'
    prep=BASE/f'runs/M439-{tag}-preparation-01/RESULT.json';p=json.loads(prep.read_bytes())
    for f in p['files']:assert sha(ROOT/f['path'])==f['sha256'],f['path']
    checks={};metrics=[];ars=[];done=None
    if mode=='compile':
        rc=json.loads((sim/'compile_exit.json').read_bytes())['compile_rc']
        log=(sim/'compile_console.log').read_text(encoding='utf-8-sig',errors='replace')
        checks=dict(original_rc=rc==0,snapshot='Built simulation snapshot m439_trace' in log,no_compile_error='ERROR:' not in log)
        result=dict(status='PASS_M439_NARROW_RTL_COMPILED' if all(checks.values()) else 'FAIL_M439_NARROW_RTL_COMPILE',checks=checks,original_rc=rc,
          preparation_sha256=sha(prep),tag=tag,build_id=p['build_id'],board=False,log_sha256=sha(sim/'compile_console.log'))
    else:
        rc=json.loads((sim/(mode+'_exit.json')).read_bytes())['simulation_rc'];log=(sim/(mode+'.log')).read_text(encoding='utf-8-sig',errors='replace')
        tvdir=sim/(mode+'_result');prefix='rtl.m89x_runtime_kernel.autotvout_';errors=[]
        def read(name):
            try:return read_tv(tvdir/(prefix+name+'.dat'))
            except Exception as e:errors.append(name+':'+repr(e));return []
        raw=b''.join(x.to_bytes(8,'little') for x in read('rx_V_data_V'));golden=(out/'golden.bin').read_bytes()
        checks=dict(original_rc=rc==0,full_output=len(raw)==4096 and raw==golden,return_value=read('ap_return')==[int(p['build_id'],16)],TLAST=read('rx_V_last_V')==[0]*511+[1])
        for field in ('keep','strb'):checks[field]=read('rx_V_'+field+'_V')==[255]*512
        clean,uvm=evaluate(sim,log);checks['uvm_visible_no_error']=clean
        checks['engine_complete']='RTL Simulation : 1 / 1' in log and not re.search(r'ERROR:|Fatal:|failed to start|necessary license',log)
        ds=re.findall(r'M439_DONE cycles=(\d+) output=(\d+) tlast=(\d+)',log)
        checks['done_once']=len(ds)==1 and 0<int(ds[0][0])<=500000 and ds[0][1:] == ('512','1')
        if len(ds)==1:done=dict(cycles=int(ds[0][0]),output_words=int(ds[0][1]),TLAST=int(ds[0][2]))
        metrics=[{k:int(v) for k,v in re.findall(r'(\w+)=(\d+)',line)} for line in re.findall(r'M439_METRIC[^\r\n]+',log)]
        ars=[dict(shard=int(a),address=int(b,16),length=int(c)+1,size=int(d),burst=int(e)) for a,b,c,d,e in re.findall(r'M439_AR shard=(\d+) address=([0-9a-fA-F]+) len=(\d+) size=(\d+) burst=(\d+)',log)]
        checks['four_shards']=len(metrics)==4 and sorted(x['shard'] for x in metrics)==list(range(4))
        checks['MAC_operations']=all(x['mac_calls']==160 and x['iterations']==2560 for x in metrics)
        checks['read_protocol']=all(x['R']==p['expected']['weight_beats_per_shard'] and x['pending']==x['bad_RLAST']==x['bad_RRESP']==0 for x in metrics)
        coverage=[]
        for i in range(4):
            rows=[x for x in ars if x['shard']==i];good=bool(rows) and len(rows)==next((x['AR'] for x in metrics if x['shard']==i),-1)
            base=rows[0]['address'] if rows else 0;cursor=base;hist=collections.Counter()
            for x in rows:
                good=good and x['address']==cursor and x['size']==4 and x['burst']==1 and 1<=x['length']<=64 and (x['address']&4095)+x['length']*16<=4096
                cursor+=x['length']*16;hist[x['length']]+=1
            good=good and cursor-base==p['expected']['weight_beats_per_shard']*16
            coverage.append(dict(shard=i,base_address=base,bytes=cursor-base,requests=len(rows),burst_histogram=dict(hist),exact_nonoverlapping_coverage=good))
        checks['address_coverage']=all(x['exact_nonoverlapping_coverage'] for x in coverage)
        result=dict(status='PASS_M439_NARROW_RTL_NUMERICAL_AND_PROTOCOL' if all(checks.values()) and not errors else 'FAIL_M439_NARROW_RTL',
          tag=tag,mode=mode,build_id=p['build_id'],original_rc=rc,checks=checks,errors=errors,done=done,metrics=metrics,address_coverage=coverage,addresses=ars,uvm_evidence=uvm,
          output_sha256=hashlib.sha256(raw).hexdigest(),reference_sha256=sha(out/'golden.bin'),preparation_sha256=sha(prep),board=False,performance_proven=False,
          evidence=[dict(path=x.relative_to(ROOT).as_posix(),sha256=sha(x)) for x in [sim/(mode+'.log'),sim/(mode+'_exit.json'),sim/(mode+'.args'),*sorted(tvdir.glob('*.dat'))]])
    ev=BASE/f'runs/M439-{tag}-{mode}-01/RESULT.json';atomic(ev,encoded(result),immutable=True)
    sync('latest_m439_'+tag+'_'+mode,dict(status=result['status'],result=ev.relative_to(ROOT).as_posix(),sha256=sha(ev),build_id=p['build_id'],board=False),
      f'## M439 {tag}/{mode}离线RTL证据（2026-10-07）\n\nSHA {sha(ev)}；{result["status"]}，原退出码{rc}；仅一输出块/真实权重代表输入，完整输出/Build/协议/地址覆盖及MAC计数按RESULT核对；0板端，非DDR实测或新收益。原证据与M437基线保持，失败仅本级分析；通过后先按冻结停止判据比较，不能自动扩大完整模型。')
    print('M439_RTL_SYNC',tag,mode,sha(ev),result['status'])
    print(json.dumps(dict(checks=checks,done=done,metrics=metrics,coverage=result.get('address_coverage')),ensure_ascii=True))
    if not all(checks.values()) or result.get('errors'):raise SystemExit(1)
    atomic(sim/(mode+'_validated.json'),encoded(dict(status=result['status'],raw_sha256=sha(ev))),immutable=True)

if __name__=='__main__':main()
