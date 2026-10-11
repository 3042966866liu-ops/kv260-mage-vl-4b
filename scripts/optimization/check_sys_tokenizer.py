"""Read-only asset gate; never load an overlay or execute model inference."""
import hashlib
import json
from pathlib import Path
import sys

root=Path('/home/ubuntu/tellme_m120_m89x2_20260901')
assert hashlib.sha256(Path(__file__).read_bytes()).hexdigest()==sys.argv[1]
config=json.loads((root/'optimization_v1/OP01-SYS-01/sys_config.json').read_text())
sys.path[0:0]=[str(root/p) for p in config['python_path']]
from tokenizers import Tokenizer
package=root/'m181_m120_video_board_candidate'
manifest=package/'PACKAGE_MANIFEST.json'
assert hashlib.sha256(manifest.read_bytes()).hexdigest()==config['package_manifest_hashes'][package.name]
relative='text_auxiliary/tokenizer/tokenizer.json'
entry=next(r for r in json.loads(manifest.read_text())['files'] if r['path']==relative)
path=package/relative
assert hashlib.sha256(path.read_bytes()).hexdigest()==entry['sha256']
tokenizer=Tokenizer.from_file(str(path))
print('OP01_TOKENIZER_ASSET '+json.dumps(dict(status='PASS',path=str(path),sha256=entry['sha256'],
    vocabulary_size=tokenizer.get_vocab_size(),old_path_exists=(package/'text_auxiliary/tokenizer.json').exists(),
    overlay_loaded=False,model_inference=False)))
