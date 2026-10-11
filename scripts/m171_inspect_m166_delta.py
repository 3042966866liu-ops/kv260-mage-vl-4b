#!/usr/bin/env python3
import hashlib,json,sys
from pathlib import Path
r=Path('/home/ubuntu/tellme_m120_m89x2_20260901/m166_delta_01').resolve();me=sys.argv[1]
H=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
if H(Path(__file__))!=me:raise RuntimeError('M171 self hash mismatch')
files=[]
for p in sorted(r.rglob('*')):
 if p.is_file():files.append({'path':p.relative_to(r).as_posix(),'bytes':p.stat().st_size,'sha256':H(p)})
print('__M171_DELTA_INSPECTION_BEGIN__');print(json.dumps({'status':'MEASURED','root':str(r),'files':files},separators=(',',':')));print('__M171_DELTA_INSPECTION_END__');print('M171_M166_DELTA_INSPECTION_PASS')
