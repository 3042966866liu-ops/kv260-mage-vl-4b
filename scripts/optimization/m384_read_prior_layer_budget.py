"""Read prior actual layer memory only; no new forward or higher gate."""
import json
from m351_workflow import BASE,sha
p=BASE/'runs/M378-gate-up-layer-board-01/BOARD_RESULT.json'
assert sha(p)=='3925e3c38fb839bc68c1760e2ffc53eebf6400bf042a7890b0fa6ca2657f7483'
r=json.loads(p.read_text(encoding='utf-8'));baseline=r['stage_memory'][0]['memory']['process_bytes']['VmRSS']
for x in r['stage_memory']:
    if x['label']=='diagnostic-admission-after-seven-real-buffers':baseline=x['memory']['process_bytes']['VmRSS']
print(json.dumps(dict(prior_layer_only=True,prior_has_two_parser_workers=True,baseline_RSS_MiB=baseline/(1<<20),max_observed_layer_RSS_MiB=r['sampled_memory']['extrema']['max_rss']/(1<<20),observed_growth_MiB=(r['sampled_memory']['extrema']['max_rss']-baseline)/(1<<20),not_PS_read_layer_peak_proof=True)))
