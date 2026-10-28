"""Freeze finite training-only search, task and source closure before forwarding."""
from common import *
import re
def main():
    assert not PREP.exists() and not SEARCH.exists() and not QUALITY.exists()
    oldfile=R/'M523-PS-V2-V3-V6-3072-protocol-02/RESULT.json';old=read(oldfile)
    frozen=dict(old['frozen'])
    def add(f):frozen[rel(f)]=sha(f)
    recovery={}
    for name in ['CURRENT_STATE.md','docsMILESTONES.md','DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json']:
        f=ROOT/name;f.read_text(encoding='utf-8-sig');recovery[name]=sha(f)
    add(oldfile)
    for f in H.glob('*.py'):compile(f.read_text(encoding='utf-8'),str(f),'exec');add(f)
    for f in [OLD/'common.py',OLD/'late_oracle.py',OLD/'quality03.py',OPT/'candidates/M523-PS3072-ttft01/TASK_CONTRACT.json']:add(f)
    fit=R/'M523-PS-V2-V3-V6-3072-fit-02'
    for row in read(fit/'RESULT.json')['files']:
        f=fit/row['path'];assert sha(f)==row['sha256'];add(f)
    task=read(OPT/'candidates/M523-PS3072-ttft01/TASK_CONTRACT.json')
    ids=task['token_ids'];assert len(ids)==128 and ids.count(151655)==98
    log=ROOT/'tmp/m523_PS3072_RAM_log_trial03/Run.log';add(log)
    sections=re.split(r'PS3072_TTFT_BEGIN\s+(\w+)',log.read_text(encoding='utf-8',errors='replace'))
    measured={}
    for k in range(1,len(sections),2):
        rows=re.findall(r'VISION_LAYER_PASS index=(\d+) layer_ms=([\d.]+)',sections[k+1])
        if sections[k] in ('HOT_B1','HOT_B2'):
            assert len(rows)==24,(sections[k],len(rows));measured[sections[k]]={int(i):float(ms)/1000 for i,ms in rows}
    assert len(measured)==2,measured.keys()
    costs={}
    for i in range(24):
        values=[a[i] for a in measured.values()]
        costs['vision_'+str(i).zfill(2)]=dict(rank_cost_s=sum(values)/2,source='59.67s parent hotB original whole-vision-layer wall interval; includes CPU work and host overhead',samples_s=values)
    times={i:[] for i in range(36)}
    for label in ('HOT_B1','HOT_B2'):
        f=R/('M523-PS-V2-V3-V6-3072-wait-records-01/raw/'+label+'/PHYSICAL_TRANSACTIONS.json');add(f)
        rows=read(f)['instrumented']
        for i in range(36):
            a=[r for r in rows if r['layer']==i]
            assert a and all(r['completed'] for r in a)
            times[i].append(sum((r['completed_boundary_ns']-r['submitted_boundary_ns'])/1e9 for r in a))
    for i,values in times.items():costs['language_'+str(i).zfill(2)]=dict(rank_cost_s=sum(values)/2,source='Saved same128/T32 workload submit-to-complete interval sum; excludes staging/parser gaps; not whole-layer latency or pure FPGA compute',samples_s=values)
    p=dict(status='FROZEN_JOINT_WHOLE_LAYER_TRAINING_SEARCH',original_rc=0,old_protocol=old,token_ids=ids,eos_id=151645,cap=32,
        requests=old['requests'],training_ids=old['training_ids'],frozen=frozen,recovery_full_read=recovery,costs=costs,
        parent='PS3072 demo research on frozen22: hot59.6703845925s, parent feature gate FAIL retained',
        target=dict(vision_retained=12,language_retained=16),protected=dict(vision=[0,1,23],language=[0,35]),
        schedule=[dict(remove_vision=3,remove_language=5)]*4,
        screening='Training8 only: every active block residual norm/output norm divided by saved execution-cost proxy. Initial top2 per branch additionally measured by actual single-block deletion first-token forwards (32). Unmeasured individual task effects remain explicitly unmeasured.',
        selection='Each of4 rounds reranks under selected preceding combination. Compare2 joint batches: top3V/top5L versus swapping their last-ranked member for next. Rank by new training errors vs original parent, new Other tokens, then mean signed correct-direction margin, then proxy damage; deterministic tie by arm index. No reserved-cal selection.',
        search_budget=dict(first_token_sequences=104,full_vision_forwards=88,wall_seconds=14400),
        final_quality='Parent and one frozen target candidate:12cal each, exact128 IDs, full151936FP32 logits,32cap,naturalEOS; new errors/misses/nondecision/contradictions/truncation independently reviewed. No prompt or factor search. Failed aggressive target preserved; no automatic training, board run, or further search.',
        task_change='Exact existing128 board question replaces old160 explanation instruction for both arms. Do not import old10/12 as new quality evidence; common explanation defect and PS3072 feature FAIL retained.',
        physical_removal='Contract actual ModuleLists in original order, remap attention.layer_idx to compact order, config.num_hidden_layers/layer_types and DynamicCache depth match; execution hooks prove removed blocks0 calls and cache entries only retained blocks. Offline only: board scheduler/deployment not modified.',
        no_weight_updates=True,new_R1=False,new_quantization=False,heldout_opened=0,board_commands=0,
        AI_generated_pilot=True,source_group_independence_limited=True,full_release_quality_pass=False,TTFT_under30_pass=False)
    save(PREP/'RESULT.json',p)
    from m455456_workflow02 import synchronized
    h=sha(PREP/'RESULT.json');synchronized('latest_m523_whole_layer_protocol01',dict(status=p['status'],result=rel(PREP/'RESULT.json'),sha256=h,board=False),
        '## M523联合整层删除128输入离线研究冻结\n\nRESULT SHA '+h+'；以当前59.67秒PS3072父为参考，保护V0/V1/V23、L0/L35，训练4组8请求迭代4批，每批删除3视觉+5语言，目标保留12V/16L。最多104首token训练序列，最终两arm各12完整自然回答；128新同任务对照，旧160质量不沿用，PS特征FAIL保持。真实ModuleList缩短/紧凑KV，原码/R1不改；0板/heldout/梯度/新量化，30秒仅目标。')
    print(p['status'],h,flush=True)
if __name__=='__main__':main()
