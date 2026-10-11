"""Predetermined small-chain host-observed comparison, not pure PL cycles."""
import statistics

def derive_comparison(transactions,loads,names):
    measured=[r for r in transactions if r.get('measured')]
    results={}
    for name in names:
        medians=[]
        for block,variant in enumerate('ABBABAAB'):
            rows=[r for r in measured if r['case']==name and r['block']==block]
            if len(rows)!=8 or sorted(r['repeat'] for r in rows)!=list(range(8)) or any(r['variant']!=variant for r in rows):raise ValueError('Fixed measurements incomplete')
            values=[r['wait_ns'] for r in rows]
            if any(type(x) is not int or x<=0 for x in values):raise ValueError('Invalid measured time')
            medians.append(dict(block=block,variant=variant,median_ns=statistics.median(values),samples_ns=values,spread_ns=max(values)-min(values)))
        a=[r['median_ns'] for r in medians if r['variant']=='A'];b=[r['median_ns'] for r in medians if r['variant']=='B']
        blocks=[]
        for start in (0,4):
            av=statistics.median(r['median_ns'] for r in medians[start:start+4] if r['variant']=='A');bv=statistics.median(r['median_ns'] for r in medians[start:start+4] if r['variant']=='B')
            blocks.append(dict(original_ns=av,candidate_ns=bv,gain_fraction=(av-bv)/av))
        av,bv=statistics.median(a),statistics.median(b)
        results[name]=dict(block_medians=medians,balanced_blocks=blocks,original_median_ns=av,candidate_median_ns=bv,gain_fraction=(av-bv)/av,separated=max(b)<min(a),pass_=max(b)<min(a) and all(r['gain_fraction']>0 for r in blocks))
    clocks=[r['clocks_mhz'] for r in loads if r['variant'] in ('A','B')]
    same=len(clocks)==8 and all(c==clocks[0] for c in clocks)
    return dict(cases=results,same_observed_ps_clocks=same,all_cases_pass=same and all(r['pass_'] for r in results.values()),pure_compute=False,boundary='S2MM submit through latched AP_DONE and both DMA idle. Packing/staging/output sync/hash excluded.',policy='Eight predefined A-B-B-A/B-A-A-B blocks, one primer and eight measured requests per shape/block. No dropping samples or repeated attempts until PASS.')
