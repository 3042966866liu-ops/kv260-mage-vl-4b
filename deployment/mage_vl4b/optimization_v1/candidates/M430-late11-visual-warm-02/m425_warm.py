"""Fixed M424 sequence and prespecified statistics, no adaptive sample counts."""
import math,statistics,time
from m425_environment import environment_issues,configuration

ORDER='ABBAABBABAAB'
PAIRS=((1,2),(4,3),(6,5),(7,8))


class WarmConditionsNotEstablished(RuntimeError):pass

def paired_conditions(samples):
    if len(samples)!=8:return ['formal eight requests incomplete']
    return [f'pair {a}/{b}: read mismatch' for a,b in PAIRS if abs(samples[a-1]['io_delta']['read_bytes']-samples[b-1]['io_delta']['read_bytes'])>1048576]

class WarmSequence:
    def __init__(self,result,reference,clock=time.monotonic,*,protocol_sha=''):
        self.result,self.reference,self.clock=result,reference,clock
        self.started=clock();self.recorded=0
        result.update(warm_protocol_sha256=protocol_sha,warm_sequence=ORDER,warm_conditions_established=False,
                      warmup_samples=[],formal_samples=[],temperature_measurement_enabled=False)
    def stop(self,issues):
        self.result['experiment_stop']=dict(status='WARM_CONDITIONS_NOT_ESTABLISHED',issues=issues)
        raise WarmConditionsNotEstablished('; '.join(issues))
    def before(self,index):
        if index!=self.recorded or index>=12:self.stop(['sequence position invalid'])
        if self.clock()-self.started>=1800:self.stop(['sequence budget exhausted'])
        if index==4 and not self.result['warm_conditions_established']:self.stop(['fixed warmups not established'])
    def record(self,sample):
        i=self.recorded
        if sample['index']!=i+1 or sample['variant']!=ORDER[i]:self.stop(['sample identity/order differs'])
        sample['phase']='warmup' if i<4 else 'formal';sample['phase_index']=i+1 if i<4 else i-3
        self.result['warmup_samples' if i<4 else 'formal_samples'].append(sample);self.recorded+=1
        issues=[]
        for side in ('before_environment','after_environment'):
            env=sample.get(side,{})
            issues.extend(side+': '+s for s in environment_issues(env))
            if configuration(env)!=configuration(self.reference):issues.append(side+': configuration changed')
        expected=dict(cache_entries=26,cache_bytes=66699264,cache_misses=26,cache_within_budget=True)
        for side in ('before_cache','after_cache'):
            cache=sample.get(side,{})
            if i<2 and side=='before_cache':
                if (type(cache.get('cache_entries')) is not int or not 0<=cache['cache_entries']<=26 or
                    type(cache.get('cache_bytes')) is not int or not 0<=cache['cache_bytes']<=66699264 or
                    cache.get('cache_within_budget') is not True):issues.append(side+': initial cache outside budget')
            elif any(cache.get(k)!=v for k,v in expected.items()):issues.append(side+': bounded visual cache differs')
        if i>=2:
            b=sample.get('io_delta',{}).get('read_bytes')
            if type(b) is not int or not 0<=b<=1048576:issues.append('warm read_bytes limit')
            if sample.get('major_fault_delta')!=0:issues.append('warm major fault limit')
        t=sample.get('timing',{}).get('total_ms')
        if type(t) not in (int,float) or not math.isfinite(t) or not 0<t<=180000:issues.append('request budget/invalid timer')
        if i>=5 and i%2:
            x,y=self.result['formal_samples'][-2:]
            if abs(x['io_delta']['read_bytes']-y['io_delta']['read_bytes'])>1048576:issues.append('adjacent pair read mismatch')
        if self.clock()-self.started>1800:issues.append('sequence budget exhausted')
        if issues:self.stop(issues)
        if i==3:self.result['warm_conditions_established']=True


def adjudicate(samples):
    if len(samples)!=8 or ''.join(s['variant'] for s in samples)!='ABBABAAB':raise ValueError('Frozen eight formal samples required')
    if paired_conditions(samples):raise ValueError('Paired read conditions differ')
    times=[s['timing']['total_ms'] for s in samples]
    if any(not math.isfinite(t) or t<=0 for t in times):raise ValueError('Invalid total time')
    deltas=[times[a-1]-times[b-1] for a,b in PAIRS]
    mean=statistics.mean(deltas);se=statistics.stdev(deltas)/2
    interval=[mean-3.182446305*se,mean+3.182446305*se]
    blocks=[]
    for name,rows in (('ABBA',samples[:4]),('BAAB',samples[4:])):
        a=[s['timing']['total_ms'] for s in rows if s['variant']=='A'];b=[s['timing']['total_ms'] for s in rows if s['variant']=='B']
        am,bm=statistics.mean(a),statistics.mean(b)
        blocks.append(dict(order=name,A_ms=a,B_ms=b,A_mean_ms=am,B_mean_ms=bm,
                           gain_ms=am-bm,gain_percent=(am-bm)/am*100,
                           A_range_ms=max(a)-min(a),B_range_ms=max(b)-min(b)))
    a=[s['timing']['total_ms'] for s in samples if s['variant']=='A'];b=[s['timing']['total_ms'] for s in samples if s['variant']=='B']
    passed=all(x['gain_ms']>0 for x in blocks) and interval[0]>0
    return dict(status='PASS_CONTROLLED_WARM_FULL_REQUEST_BENEFIT' if passed else 'NET_BENEFIT_NOT_RELIABLY_MEASURED_CLOSE_VARIANT',
                performance_pass=passed,temperature_measurement_enabled=False,blocks=blocks,paired_deltas_ms=deltas,
                paired_mean_gain_ms=mean,paired_95percent_CI_ms=interval,paired_df=3,
                A_mean_ms=statistics.mean(a),B_mean_ms=statistics.mean(b),
                A_median_ms=statistics.median(a),B_median_ms=statistics.median(b),
                gain_percent=(statistics.mean(a)-statistics.mean(b))/statistics.mean(a)*100,
                threshold_fitted_after_measurement=False,additional_samples_allowed=False,
                scope='This fixed-input controlled warm experiment only; no production promotion.')
