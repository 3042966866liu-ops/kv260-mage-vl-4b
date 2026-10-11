import json
import re
from pathlib import Path
from measurement import exclusive_lock, sha256, write_json

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'deployment/mage_vl4b/optimization_v1'
log = ROOT / 'tmp/op00_decoder_dependency01/run.log'
text = log.read_text(encoding='utf-8-sig')
raw = json.loads(text.split('OP00_DECODER_JSON_BEGIN',1)[1].split('OP00_DECODER_JSON_END',1)[0])
rc = int(re.search(r'__OP00_DECODER_RC_(\d+)__',text)[1])
with exclusive_lock(BASE/'control.lock'):
    output=BASE/'gates/G00-decoder-dependency/attempt_01/result.json'
    if output.exists():raise RuntimeError('Immutable result exists')
    decode=raw.get('probe',{}).get('raw_video_decode',{})
    host=json.loads((BASE/'datasets/dev_bootstrap_v1/decode_validation.json').read_text())['records'][0]
    result=dict(status=raw['status'],raw_process_exit_code=rc,board_result=raw,
        evidence_files=[dict(path=str(log),sha256=sha256(log))],model_inference=False,
        cross_platform_rgb_exact=host['decoded_rgb_sha256']==decode.get('rgb_sha256'),
        cross_platform_note='WSL OpenCV5 versus ARM OpenCV4.11 RGB differ; bind identical board-decoded RGB for numerical comparison, not assume byte equality')
    write_json(output,result)
    index_path=ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json'
    index=json.loads(index_path.read_text(encoding='utf-8-sig'))
    index['latest_optimization_v1_decoder_dependency']=dict(status=raw['status'],result=str(output.relative_to(ROOT)),
        sha256=sha256(output),raw_process_exit_code=rc,decode_s=decode.get('decode_s'),
        temporary_address_cleanup_exit=raw.get('temporary_address_cleanup_exit'),model_inference=False)
    write_json(index_path,index)
    state_path=BASE/'STATE.json'
    state=json.loads(state_path.read_text())
    state['results']['decoder_dependency']=str(output)
    state['next_action']='Bind board-decoded RGB to software reference, then real SYS and causal2/8/32; no model timings yet'
    write_json(state_path,state)
print(json.dumps(dict(status=raw['status'],decode_s=decode.get('decode_s'),
    cross_platform_rgb_exact=result['cross_platform_rgb_exact'],result=str(output))))
