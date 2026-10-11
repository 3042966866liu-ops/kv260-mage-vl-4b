"""Read the single saved PS observation; never issue board or model commands."""
import json
from collections import defaultdict
from m351_workflow import ROOT, BASE, atomic, encoded, sha

def analyze():
    b=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    e=b['latest_m406_vision_cost_board']
    p=ROOT/e['result'];assert sha(p)==e['sha256']
    assert all(e['sha256'] in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    r=json.loads(p.read_bytes())
    if r['status']!='PASS_PS_VISUAL_COST_OBSERVATION':raise RuntimeError('No complete cost observation to interpret')
    categories=defaultdict(int);groups=defaultdict(lambda:defaultdict(int))
    for row in r['costs']['rows']:
        categories[row['category']]+=row['exclusive_ns']
        if row['category'].startswith('linear_'):
            name=row['name']
            group='QKV' if name.endswith('.qkv') else 'projection' if name.endswith('.proj') else 'MLP_fc1' if name.endswith('.fc1') else 'MLP_fc2' if name.endswith('.fc2') else 'Merger'
            groups[group][row['category']]+=row['exclusive_ns']
    wall=r['costs']['vision_wall_ns'];assert sum(categories.values())==wall
    windows=r['costs']['gemm_windows']
    gemm_wall=sum(w['end_ns']-w['start_ns'] for w in windows)
    gemm_cpu=sum(w['process_cpu_ns'] for w in windows)
    cpu=r['cpu_observation'];intervals=cpu['intervals']
    cores=defaultdict(lambda:dict(total_ns=0,weighted_busy_ns=0.,gemm_overlap_ns=0,gemm_weighted_busy_ns=0.))
    for x in intervals:
        dt=x['end_ns']-x['start_ns']
        overlap=sum(max(0,min(x['end_ns'],w['end_ns'])-max(x['start_ns'],w['start_ns'])) for w in windows)
        assert 0<=overlap<=dt
        for k,v in x['busy_percent'].items():
            if v is None:continue
            assert 0<=v<=100
            c=cores[k];c['total_ns']+=dt;c['weighted_busy_ns']+=dt*v/100
            c['gemm_overlap_ns']+=overlap;c['gemm_weighted_busy_ns']+=overlap*v/100
    values={k:dict(system_busy_percent=100*v['weighted_busy_ns']/v['total_ns'],
                  approximate_gemm_system_busy_percent=100*v['gemm_weighted_busy_ns']/v['gemm_overlap_ns'],
                  sampled_ns=v['total_ns'],gemm_overlap_ns=v['gemm_overlap_ns']) for k,v in cores.items()}
    tasks=cpu['per_task_persistent_only']
    native=sorted(r['native_cpu_operators'],key=lambda x:x['self_cpu_time_us'],reverse=True)
    out=dict(status='SAVED_PS_VISUAL_COST_TABLE_ONLY',raw_sha256=e['sha256'],raw_path=e['result'],
             visual_wall_s=wall/1e9,exclusive_seconds={k:v/1e9 for k,v in categories.items()},
             exclusive_percent={k:100*v/wall for k,v in categories.items()},
             linear_group_seconds={g:{k:v/1e9 for k,v in d.items()} for g,d in groups.items()},
             gemm_wall_s=gemm_wall/1e9,gemm_process_cpu_s=gemm_cpu/1e9,gemm_cpu_to_wall=gemm_cpu/gemm_wall,
             approximate_system_core_utilization=values,process_threads=tasks,
             attention_implementations=r['attention_implementations'],native_top20=native[:20],
             backend=r['backend_before'],cache_before=r['before_cache'],cache_after=r['after_cache'],
             before_memory=cpu['before']['memory'],after_memory=cpu['after']['memory'],
             observed_read_bytes=cpu['after']['io']['read_bytes']-cpu['before']['io']['read_bytes'],
             normal_request_performance_pass=False,core_samples_system_wide_and_100ms_interpolation=True,
             native_cpu_times_not_additive_wall=True,bindings_restored=r['bindings_restored'],owner_closed=r['visual_owner_closed'])
    return out

if __name__=='__main__':
    value=analyze()
    atomic(BASE/'runs/M406-vision-cost-board-02/COST_TABLE.json',encoded(value),immutable=True)
    print(json.dumps(value,ensure_ascii=False,indent=2))
