"""Bounded COM3 result export; no inference or device access."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import zlib

parser=argparse.ArgumentParser()
parser.add_argument('--self-sha256',required=True)
parser.add_argument('--result-sha256',required=True)
parser.add_argument('--revision',type=int,choices=(1,2,5),default=2)
args=parser.parse_args()
def digest(data):return hashlib.sha256(data).hexdigest()
if digest(Path(__file__).read_bytes())!=args.self_sha256:raise RuntimeError('Exporter changed')
path=Path(f'/home/ubuntu/tellme_m120_m89x2_20260901/optimization_v1/results/sys{args.revision:02d}.json')
if not 1<=path.stat().st_size<=16*1024*1024:raise RuntimeError('Result size outside bound')
raw=path.read_bytes()
if digest(raw)!=args.result_sha256:raise RuntimeError('Result changed')
data=json.loads(raw)
if data['status'] not in ('FAIL','PROVISIONAL'):raise RuntimeError('Not a completed result')
packed=zlib.compress(raw,9);encoded=base64.b64encode(packed).decode()
print('OP01_RESULT_META '+json.dumps(dict(raw_bytes=len(raw),raw_sha256=digest(raw),
    compressed_bytes=len(packed),compressed_sha256=digest(packed))),flush=True)
for i,offset in enumerate(range(0,len(encoded),1600)):
    print(f'OP01_RESULT_CHUNK {i} '+encoded[offset:offset+1600],flush=True)
print('OP01_RESULT_EXPORT_END',flush=True)
