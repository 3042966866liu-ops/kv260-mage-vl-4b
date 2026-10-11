"""Prepare actual stream/export fixture checks for the new protocol; no board."""
from m351_workflow import ROOT,HERE,atomic
from m427_prepare import once


def main():
    test=(HERE/'test_m433_trials.py').read_text(encoding='utf-8').replace('m433_trials','m437_trials')
    test=once(test,"trials.read_environment=lambda:copy.deepcopy(env);trials.io_snapshot=lambda:{'read_bytes':0}",
              """trials.read_environment=lambda:copy.deepcopy(env)
    fake_io_count=[0]
    def fake_io():
        fake_io_count[0]+=1
        return {'read_bytes':fake_io_count[0]*(777<<20)}
    trials.io_snapshot=fake_io""")
    test=once(test,"result['fake_variant_index']=index", "result['fake_variant_index']=index\n            cache.update(cache_entries=25 if index else 26,cache_bytes=62177280 if index else 66699264)")
    test=once(test,"assert len(result['warmup_samples'])==4", "assert all(s['io_delta']['read_bytes']>1048576 for s in result['samples'])\n        assert result['preconditioning_completed']\n        assert len(result['warmup_samples'])==4")
    atomic(HERE/'test_m437_trials.py',test.encode('utf-8'),immutable=True)
    text=(HERE/'m433_support04.py').read_text(encoding='utf-8').replace('M433','M437').replace('m433','m437')
    text=text.replace('tmp/m43705','tmp/m43701').replace("'m425_warm.py'","'m437_sequence.py'")
    # Existing lightweight memory policy and provider are unchanged, reuse their supported source.
    text=text.replace('m437_light_policy','m433_light_policy')
    text=text.replace("'from test_m425_warm import main as warm',",'')
    text=text.replace("'environment();warm()'", "'environment()'")
    text=text.replace('PASS_M437_CONTROLLED_WARM_MEASUREMENTS_COLLECTED','PASS_M437_NATURAL_IO_MEASUREMENTS_COLLECTED')
    text=text.replace('controlled-warm-complete-request-performance','natural-IO-complete-request-performance')
    text=text.replace('warm_protocol_sha256','natural_IO_protocol_sha256')
    text=text.replace("'cold-read'","'negative-read'").replace("s['io_delta']['read_bytes']=1048577","s['io_delta']['read_bytes']=-1")
    text=once(text,"    for p in w.PKG.glob('*.py'):","""    from m437_sequence import NaturalSequence,adjudicate,ORDER
    fixture_sample=copy.deepcopy(r['samples'][0]);reference=r['warm_environment_reference']
    def accept(rows):
        seq=NaturalSequence({},reference,clock=lambda:0)
        for i,s in enumerate(rows):seq.before(i);seq.record(s)
        return seq.result
    varied=[]
    for i,v in enumerate(ORDER):
        s=copy.deepcopy(fixture_sample);s.update(index=i+1,variant=v,major_fault_delta=i+3)
        s['io_delta']['read_bytes']=(123+i*71)<<20
        for side in ('before_cache','after_cache'):s[side].update(cache_entries=25 if v=='B' else 26,cache_bytes=62177280 if v=='B' else 66699264)
        varied.append(s)
    assert accept(varied)['preconditioning_completed']
    for label,field,value in [('cache-entry-bound','cache_entries',27),('cache-byte-bound','cache_bytes',66699265),('cache-flag','cache_within_budget',False)]:
        rows=copy.deepcopy(varied);rows[4]['after_cache'][field]=value
        reject(label,lambda rows=rows:accept(rows))
    rows=copy.deepcopy(varied);rows[4]['major_fault_delta']=-1;reject('invalid-fault-counter',lambda:accept(rows))
    rows=copy.deepcopy(varied);rows[4]['timing']['total_ms']=240001;reject('request-budget',lambda:accept(rows))
    seq=NaturalSequence({},reference,clock=lambda:0);reject('formal-before-preconditioning',lambda:seq.before(4))
    seq=NaturalSequence({},reference,clock=lambda:0);seq.recorded=12;reject('thirteenth-request',lambda:seq.before(12))
    def stats(a,b):
        rows=copy.deepcopy(varied[4:])
        for s in rows:s['timing']['total_ms']=a if s['variant']=='A' else b
        return adjudicate(rows)
    assert stats(100000,90000)['performance_pass'] is True
    assert stats(100000,100000)['performance_pass'] is False
    assert stats(100000,110000)['performance_pass'] is False
    for p in w.PKG.glob('*.py'):""")
    text=text.replace("('m437_workflow.py','m437_control.ps1','m437_support04.py')", "('m437_workflow.py','m437_control.ps1','m437_support.py','m437_sequence.py','test_m437_trials.py')")
    text=text.replace('M437-performance-support-04','M437-natural-IO-support-01').replace('latest_m437_performance_support','latest_m437_support')
    text=text.replace("source_sha256={n:sha(HERE/n)","host_sources={n:sha(HERE/n)")
    text=once(text,"board_run=False,performance_pass=False)", "candidate_remote='/home/ubuntu/m437_natural_IO_candidate_01',evidence_remote='/home/ubuntu/m437_natural_IO_result_01',board_run=False,performance_pass=False)")
    text=text.replace('PASS_M437_OFFLINE_TIMED_PROVIDER_STREAM_RECOVERY','PASS_M437_ACTUAL_STREAM_NATURAL_IO_HOST_SUPPORT_ONLY')
    atomic(HERE/'m437_support.py',text.encode('utf-8'),immutable=True)
    print('M437_SUPPORT_PREPARED')


if __name__=='__main__':main()
