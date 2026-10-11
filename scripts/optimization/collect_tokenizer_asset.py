import json
import re
from pathlib import Path
from measurement import sha256,write_json,exclusive_lock
root=Path(__file__).resolve().parents[2]
base=root/'deployment/mage_vl4b/optimization_v1'
log=root/'tmp/op01_tokenizer01/run.log'
text=log.read_text(encoding='utf-8-sig')
assert '__OP01_ASSET_RC_0__' in text
data=json.loads(re.search(r'^OP01_TOKENIZER_ASSET (.+)$',text,re.M).group(1))
assert data['status']=='PASS' and not data['old_path_exists'] and not data['overlay_loaded']
with exclusive_lock(base/'control.lock'):
    out=base/'gates/G01-tokenizer-asset/attempt_01/result.json'
    assert not out.exists()
    write_json(out,dict(status='PASS',scope='Tokenizer asset only; no inference',board=data,log_sha256=sha256(log)))
    path=root/'deployment/mage_vl4b/BOARD_GATE_RESULT.json'
    index=json.loads(path.read_text(encoding='utf-8-sig'))
    index['latest_optimization_v1_tokenizer_asset']=dict(status='PASS',result=str(out.relative_to(root)),sha256=sha256(out))
    write_json(path,index)
    path=base/'STATE.json';state=json.loads(path.read_text())
    state['results']['tokenizer_asset']=str(out.relative_to(root))
    state['next_action']='Freeze SYS02 with tokenizer asset loading before overlay; recheck revised import gate then SYS2. SYS01 FAIL retained.'
    write_json(path,state)
print(json.dumps(data))
