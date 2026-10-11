"""Exercise video acceptance against saved M339 events; no inference/board access."""
import ast
import copy
import hashlib
import json
from pathlib import Path
import sys
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def main():
    source_path = HERE / 'm345_fixed_video_gate.py'
    source = source_path.read_text(encoding='utf-8')
    namespace = {}
    for node in ast.parse(source).body:
        if isinstance(node,ast.FunctionDef) and node.name == 'validate_stream':
            exec(ast.get_source_segment(source,node),namespace)
    path = ROOT / 'deployment/mage_vl4b/optimization_v1/runs/M339-profile-04-results/m277_fixed_video.json'
    saved = json.loads(path.read_text(encoding='utf-8'))
    events = [(i['event'],i['payload']) for i in saved['events']]
    decoder = saved['decoder_evidence']
    validate = namespace['validate_stream']; accepted = validate(events,decoder)
    rejected = []
    edits = [('cpu_fallback','complete','proof','language_cpu_linear_fallback',True),
        ('call_count','complete','proof','pl_logical_chain_calls',777),
        ('selected_frame','complete',None,'selected_frame_indices',[2]),
        ('decode_added','complete',None,'decode_calls',1),
        ('wrong_token','token',None,'token_id',16)]
    for name,event,nested,key,value in edits:
        changed = copy.deepcopy(events)
        payload = next(p for n,p in changed if n == event)
        if nested: payload = payload[nested]
        payload[key] = value
        try: validate(changed,decoder)
        except RuntimeError: rejected.append(name)
        else: raise AssertionError('Invalid stream accepted: '+name)
    bad_cache = dict(decoder,cache_bytes=66699265)
    try: validate(events,bad_cache)
    except RuntimeError: rejected.append('cache_overflow')
    else: raise AssertionError('Invalid cache accepted')
    run = ROOT / 'deployment/mage_vl4b/optimization_v1/runs/M345-stream-contract-offline-01'
    run.mkdir(parents=True,exist_ok=False)
    result = dict(status='PASS_OFFLINE_STREAM_ACCEPTANCE_CHECK',evidence_level='L0',hardware_gate_run=False,performance_pass=False,
        source_sha256=hashlib.sha256(source_path.read_bytes()).hexdigest(),saved_event_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        original_saved_events_accepted=True,rejected=rejected,semantic=accepted)
    (run/'RESULT.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(result))


if __name__ == '__main__': main()
