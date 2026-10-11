"""Saved-only compilation/simulation evidence, exact output and phase counters."""
import argparse,json,re,hashlib
from m351_workflow import ROOT,BASE,atomic,encoded,sha,sync
from m356_collect_rtl import read_tv
from m357_uvm_log_evidence import evaluate
DIR=ROOT/'tmp/m438_weight_wait_03';SIM=DIR/'verilog'

def frozen():
    prep=BASE/'runs/M438-weight-wait-preparation-01/RESULT.json'
    r=json.loads(prep.read_bytes())
    for row in r['files']:assert sha(ROOT/row['path'])==row['sha256'],row['path']
    return prep,r

def store(tag,r):
    p=BASE/f'runs/M438-weight-wait-{tag}-01/RESULT.json';atomic(p,encoded(r),immutable=True)
    sync('latest_m438_weight_wait_'+tag,dict(status=r['status'],result=p.relative_to(ROOT).as_posix(),sha256=sha(p),build_id='0x4D333537',board=False),
         f'## M438 权重等待{tag}离线证据（2026-10-07）\n\nSHA {sha(p)}；{r["status"]}，不变Build0x4D333537、小片段全部输出与阶段/有效迭代核对。0板端，非DDR实测或新提速；原M437收益保持。'+(' 下一步固定零额外延迟模型，不追加随机样本。' if tag=='random' and r['status'].startswith('PASS') else ''))
    print('M438_SYNC',tag,sha(p),r['status']);return p

def main():
    ap=argparse.ArgumentParser();ap.add_argument('mode',choices=['compile','random','zero','close']);a=ap.parse_args()
    prep,pr=frozen()
    if a.mode=='compile':
        rc=json.loads((SIM/'m438_compile_exit.json').read_bytes())['compile_rc'];log=(SIM/'m438_compile_console.log').read_text(encoding='utf-8-sig',errors='replace')
        ok=rc==0 and 'Built simulation snapshot m438_wait' in log and 'ERROR:' not in log
        r=dict(status='PASS_M438_OBSERVER_COMPILED' if ok else 'FAIL_M438_OBSERVER_COMPILE',board=False,compile_rc=rc,preparation_sha256=sha(prep),source_snapshot_sha256=sha(SIM/'m438.prj'),log_sha256=sha(SIM/'m438_compile_console.log'))
        store('compile',r)
        if not ok:raise SystemExit(1)
        return
    if a.mode=='close':
        rows=[json.loads((BASE/f'runs/M438-weight-wait-{mode}-01/RESULT.json').read_bytes()) for mode in ('random','zero')]
        assert all(r['status']=='PASS_M438_UNCHANGED_RTL_WEIGHT_WAIT_OBSERVED' for r in rows)
        r=dict(status='PASS_M438_TWO_MODEL_OBSERVATION_CLOSED',build_id='0x4D333537',board=False,dut_changed=False,
          modes={x['mode']:dict(total_cycles=x['done']['cycles'],shards=x['metrics']) for x in rows},source_raw_sha256={n:sha(BASE/f'runs/M438-weight-wait-{n}-01/RESULT.json') for n in ('random','zero')},
          limitation='One output block, W2 G40 original deterministic M355 activation and real Q weights. VIP delay is not KV260 DDR. Per-shard phases are concurrent and cannot be summed into wall latency. MAC phase includes pipeline fill/drain; accepted iteration count is not a DSP utilization percentage.',
          next_step='Use this evidence to choose a bounded weight-read/compute decoupling candidate; keep accumulation order, complete output, original seven DMA and stable rollback. No automatic board or production promotion.')
        for x in rows:
            for m in x['metrics']:
                m['explicit_weight_wait_percent_of_active']=100*(m['address_wait']+m['data_wait'])/m['active']
                m['MAC_phase_percent_of_active']=100*m['mac_phase']/m['active']
        p=store('closure',r)
        report='# M438 权重读等待与计算阶段窄RTL观察\n\n不改变Build `0x4D333537` 的核；真实Q W2首输出块、40组、32 token，使用原M355确定性代表输入，非实际视频激活。四shard并行；每个模型只一次，全部512输出与原Q参考首块逐位一致。\n\n'
        report+='| 模型 | 核总周期 | shard | 活动周期 | 等地址阻塞 | 等返回阻塞 | MAC阶段周期 | MAC调用/有效token-pair迭代 | 单拍请求/返回 | MAC期间请求/返回 |\n|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|\n'
        for x in rows:
            for m in x['metrics']:
                report+=f'| {x["mode"]} | {x["done"]["cycles"]} | {m["shard"]} | {m["active"]} | {m["address_wait"]} | {m["data_wait"]} | {m["mac_phase"]} | {m["mac_calls"]}/{m["iterations"]} | {m["AR"]}/{m["R"]} | {m["AR_during_MAC"]}/{m["R_during_MAC"]} |\n'
        report+='\n状态机严格区分：地址阶段11/21/22/31/32，返回阶段19/29/30/39/40，MAC子过程等待阶段54。返回阶段RVALID=0时父FSM停留，同时尚未开始该权重的MAC；54必须等MAC完成才回到20准备下一pair。源代码的DATAFLOW只并行四shard与merge，未把每shard读取/计算拆成独立producer/consumer。\n\n'
        report+='MAC阶段包含50-cycle过程的填充、16次II=1迭代和排空，不是逐周期所有DSP都在工作。parent相位分割总和核对；`RSTALL=0`是返回背压而非等待权重统计。原随机VIP 0–256延迟与零额外VIP延迟只回答调度是否暴露等待，不能估算真实DDR等待占比或将仿真周期差直接换算板端收益。\n\n'
        report+='原Q参考与权重选择、所有源SHA、模拟退出码、完整输出/keep/strb/TLAST/Build、500000周期预算、UVM错误可见性及四组迭代/请求计数均见两份RESULT。原01/02观察器准备错误保留；没有重跑原完整Q仿真或任何板端请求，服务/稳定回滚未变。\n'
        atomic(p.parent/'REPORT.md',report.encode('utf-8'),immutable=True);print(report);return
    tag=a.mode;stem='m438_'+tag
    compile_ev=BASE/'runs/M438-weight-wait-compile-01/RESULT.json';assert json.loads(compile_ev.read_bytes())['status']=='PASS_M438_OBSERVER_COMPILED'
    rc=json.loads((SIM/(stem+'_exit.json')).read_bytes())['simulation_rc'];log=(SIM/(stem+'_xsim.log')).read_text(encoding='utf-8-sig',errors='replace');tvdir=SIM/(stem+'_result')
    prefix='rtl.m89x_runtime_kernel.autotvout_';checks={};errors=[]
    def read(name):
        try:return read_tv(tvdir/(prefix+name+'.dat'))
        except Exception as e:errors.append(name+': '+repr(e));return []
    data=read('rx_V_data_V');raw=b''.join(x.to_bytes(8,'little') for x in data)
    checks['full_output']=raw==(DIR/'golden.bin').read_bytes() and len(raw)==4096
    for f in ('keep','strb'):
        q=read('rx_V_'+f+'_V');checks[f]=len(q)==512 and all(x==255 for x in q)
    q=read('rx_V_last_V');checks['TLAST']=q==[0]*511+[1];checks['return']=read('ap_return')==[0x4d333537]
    clean,uvm=evaluate(SIM,log);checks['uvm_no_error']=clean
    checks['engine_finished']=rc==0 and 'RTL Simulation : 1 / 1' in log and not re.search(r'ERROR:|Fatal:|necessary license|failed to start',log)
    ds=re.findall(r'M438_DONE cycles=(\d+) output=(\d+) tlast=(\d+) return=([0-9a-fA-F]+)',log)
    checks['done_once']=len(ds)==1 and int(ds[0][1])==512 and int(ds[0][2])==1 and int(ds[0][0])<=500000 and int(ds[0][3],16)==0x4d333537
    metric=[]
    for line in re.findall(r'M438_METRIC[^\r\n]+',log):metric.append({k:int(v) for k,v in re.findall(r'(\w+)=(\d+)',line)})
    checks['four_shards']=len(metric)==4 and sorted(x['shard'] for x in metric)==list(range(4))
    checks['phase_partition']=all(x['active']==sum(x[k] for k in ('address_phase','data_phase','mac_phase','other')) and x['data_phase']>=x['data_wait']>=0 and x['address_phase']>=x['address_wait']>=0 for x in metric)
    checks['actual_MAC_iterations']=all(x['mac_calls']==160 and x['iterations']==2560 and x['mac_phase']>0 for x in metric)
    checks['weight_words']=all(x['AR']==x['R']==360 and x['multi_beat']==0 for x in metric)
    ok=all(checks.values()) and not errors
    r=dict(status='PASS_M438_UNCHANGED_RTL_WEIGHT_WAIT_OBSERVED' if ok else 'FAIL_M438_WEIGHT_WAIT_OBSERVATION',board=False,dut_changed=False,mode=tag,build_id='0x4D333537',checks=checks,errors=errors,simulation_rc=rc,metrics=metric,
      done=dict(cycles=int(ds[0][0]),output_words=int(ds[0][1])) if len(ds)==1 else None,
      output_sha256=hashlib.sha256(raw).hexdigest(),reference_sha256=sha(DIR/'golden.bin'),preparation_sha256=sha(prep),uvm_evidence=uvm,
      evidence=[dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p)) for p in [SIM/(stem+'_exit.json'),SIM/(stem+'_xsim.log'),SIM/(stem+'.args'),*sorted(tvdir.glob('*.dat'))]])
    p=store(tag,r);print(json.dumps(dict(checks=checks,metrics=metric,done=r['done']),ensure_ascii=False))
    if not ok:raise SystemExit(1)
    atomic(SIM/(stem+'_validated.json'),encoded(dict(raw_sha256=sha(p),status=r['status'])),immutable=True)
if __name__=='__main__':main()
