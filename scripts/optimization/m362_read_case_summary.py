"""Read one validated saved case; compact diagnostic summary, no mutations."""
import json
import sys
import m351_workflow as w
import m362_collect_load_comparison as c

def summary(case):
    p=w.BASE/f'runs/M362-load-{case}-board-01/BOARD_RESULT.json';r=json.loads(p.read_text(encoding='utf-8'));assert c.validate(r)
    stages=[]
    for x in r['stages']:
        if x['name'] in ('initial-before-source-and-runtime-imports','after-release-asset-hashes','after-tokenizer-asset-preconstruction','after-original-M238-and-all-DMA-buffer-allocations','after-original-PS-vision-constructor','after-original-M241-embedding-and-norm-constructor','complete-runtime-loaded-retained','complete-runtime-retained-plus-2s','after-safe-close-and-PS-object-disposal'):
            stages.append(dict(name=x['name'],cma_mib=x['memory']['system_bytes']['CmaFree']/(1<<20),rss_mib=x['memory']['process_bytes']['VmRSS']/(1<<20),available_mib=x['memory']['system_bytes']['MemAvailable']/(1<<20)))
    events=[]
    for x in r['io_events']:
        events.append(dict(name=x['name'],path=x['first_path'],cma_delta_mib=(x['after']['system_bytes']['CmaFree']-x['before']['system_bytes']['CmaFree'])/(1<<20),cached_delta_mib=(x['after']['system_bytes']['Cached']-x['before']['system_bytes']['Cached'])/(1<<20),rss_delta_mib=(x['after']['process_bytes']['VmRSS']-x['before']['process_bytes']['VmRSS'])/(1<<20)))
    inv=r['retained_inventory']
    compact=dict(embedding=inv['embedding'],norm_count=len(inv['norms']),norm_total_bytes=sum(x['nbytes'] for x in inv['norms'].values()),buffers=inv['buffers'],classes=inv['classes'])
    print(json.dumps(dict(case=case,sha256=w.sha(p),status=r['status'],stages=stages,largest_cma_decreases=sorted(events,key=lambda x:x['cma_delta_mib'])[:5],tokenizers=[x for x in events if x['name']=='tokenizer.from_file'],inventory=compact,top_process_mappings=r['retained_mappings']['mappings'][:5]),ensure_ascii=True))

if __name__=='__main__':summary(sys.argv[1])
