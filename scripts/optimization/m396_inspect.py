"""Bounded saved-evidence inspection; no board access or model execution."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'deployment/mage_vl4b/optimization_v1'
for relative in ['runs/M371-candidate-profile-board-01/PREFILL_TRACE.json',
                 'runs/M375-video-wait-board-01/WAIT_TRACE.json',
                 'runs/M375-video-wait-board-01/BOARD_RESULT.json',
                 'runs/M394-silu-video-board-01/BOARD_RESULT.json']:
    r = json.loads((BASE / relative).read_text(encoding='utf-8'))
    print(relative, 'keys=', list(r))
    if 'trace' in r:
        es = r['trace']['events']
        print('events', len(es))
        families = [e for e in es if e['name'] == 'language_family' and e['metadata']['layer'] == 35]
        for e in families:
            descendants = []
            ids = {e['id']}
            for child in es:
                if child['parent'] in ids:
                    ids.add(child['id']); descendants.append(child)
            totals = {}
            for child in descendants:
                n = child['name']; totals[n] = totals.get(n, 0) + child['exclusive_ns'] / 1e6
            print('layer35 family', e['metadata'], 'inclusive_ms', e['inclusive_ns']/1e6, 'exclusive children ms', totals)
    elif 'events' in r:
        print('first events', r['events'][:2])
    else:
        for key in ['gate', 'payload', 'runtime', 'result', 'runtime_evidence']:
            if key in r and isinstance(r[key], dict):
                print(key, 'keys', list(r[key]))

def find_records(o, path='root'):
    if isinstance(o, dict):
        for k,v in o.items():
            if k == 'scale_attempts' and isinstance(v,list):
                print(path+'.'+k, 'count', len(v), 'layer35', [x for x in v if x.get('layer')==35], 'retries', [x for x in v if len(x.get('attempted_shifts',[]))>1])
            elif k in ('families','family_outputs','family_trace'):
                print(path+'.'+k, str(v)[:400])
            else: find_records(v, path+'.'+k)
    elif isinstance(o,list):
        for i,v in enumerate(o):
            if isinstance(v,(dict,list)): find_records(v, path+f'[{i}]')
r=json.loads((BASE/'runs/M394-silu-video-board-01/BOARD_RESULT.json').read_text(encoding='utf-8'))
find_records(r)
print('layer35 transactions', [x for x in r['transactions'] if x.get('layer')==35])
w=json.loads((BASE/'runs/M375-video-wait-board-01/WAIT_TRACE.json').read_text(encoding='utf-8'))
print('layer35 wait families', [x for x in w['families'] if x.get('layer')==35])
print('first wait record', w['records'][:1])
p=ROOT/'release_staging/kv260-mage-vl-4b-prebuilt-install-20260926-v7/deployment/mage_vl4b/m175_m120_fixed_text_candidate/contracts/M126_LANGUAGE_RUNTIME_CONTRACT_RESULT.json'
c=json.loads(p.read_text(encoding='utf-8'))
print('contractkeys',list(c))
print('tailchains',[x for x in c.get('chains',[]) if x.get('layer')==35])
