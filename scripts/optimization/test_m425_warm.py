"""Synthetic clocks/cache/times only; never a measured performance result."""
import copy,json
from pathlib import Path
from m425_warm import WarmSequence,adjudicate,ORDER,WarmConditionsNotEstablished


def main():
    env=json.loads((Path(__file__).parent/'ENVIRONMENT_FIXTURE.json').read_bytes())['environment']
    env={k:v for k,v in env.items() if k not in ('thermal_zones','cooling_devices','temperature_source','temperature_ABI_source','temperature_channel_mapping_proven')}
    env['missing']=[];env['temperature_measurement_enabled']=False
    cache=dict(cache_entries=26,cache_bytes=66699264,cache_misses=26,cache_within_budget=True)
    def sample(i,v,t=100000):
        return dict(index=i,variant=v,timing=dict(total_ms=t),before_environment=copy.deepcopy(env),after_environment=copy.deepcopy(env),
                    before_cache=copy.deepcopy(cache),after_cache=copy.deepcopy(cache),io_delta=dict(read_bytes=0),major_fault_delta=0)
    result={};sequence=WarmSequence(result,env,clock=lambda:0)
    for i,v in enumerate(ORDER):sequence.before(i);sequence.record(sample(i+1,v,100000 if v=='A' else 99000))
    assert len(result['warmup_samples'])==4 and len(result['formal_samples'])==8 and result['warm_conditions_established']
    assert adjudicate(result['formal_samples'])['performance_pass']
    def reject(index,row):
        q=WarmSequence({},env,clock=lambda:0)
        try:
            for i in range(index):q.before(i);q.record(sample(i+1,ORDER[i]))
            q.before(index);q.record(row)
        except WarmConditionsNotEstablished:return
        raise AssertionError('Bad warm condition accepted')
    bad=sample(3,'B');bad['io_delta']['read_bytes']=1048577;reject(2,bad)
    bad=sample(3,'B');bad['major_fault_delta']=1;reject(2,bad)
    bad=sample(3,'A');reject(2,bad)
    bad=sample(1,'A');bad['before_environment']['cpu_policies']['policy0']['scaling_cur_freq']='1000000';reject(0,bad)
    bad=sample(1,'A');bad['before_cache']['cache_entries']=27;reject(0,bad)
    bad=sample(1,'A');bad['after_environment']['pl_clocks']={};reject(0,bad)
    bad=sample(1,'A',180001);reject(0,bad)
    formal=result['formal_samples'];equal=copy.deepcopy(formal)
    for s in equal:s['timing']['total_ms']=100000
    assert not adjudicate(equal)['performance_pass']
    noisy=copy.deepcopy(formal)
    # Positive mean but one reversed pair with excessive uncertainty must fail.
    for s,t in zip(noisy,[100000,99000,90000,100000,110000,100000,100000,99000]):s['timing']['total_ms']=t
    assert not adjudicate(noisy)['performance_pass']
    try:adjudicate(formal[:-1])
    except ValueError:pass
    else:raise AssertionError('Extra/fewer samples accepted')
    print('M425_SYNTHETIC_WARM_COMPONENT_PASS rejects=10')


if __name__=='__main__':main()
