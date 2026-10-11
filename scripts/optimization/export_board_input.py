"""Export exact board-decoded RGB over UART; no inference, no cache for SYS."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import sys
import zlib

ROOT=Path('/home/ubuntu/tellme_m120_m89x2_20260901')
BASE=ROOT/'optimization_v1'
parser=argparse.ArgumentParser()
parser.add_argument('--self-sha256',required=True)
args=parser.parse_args()
if hashlib.sha256(Path(__file__).read_bytes()).hexdigest()!=args.self_sha256:
    raise RuntimeError('Export script changed')
sys.dont_write_bytecode=True
sys.path[:0]=[str(ROOT/'m190_mage_runtime'),str(BASE/'dependencies/opencv411_arm64_v1/site'),
             str(BASE/'OP00-import-decode-01')]
from sys_video_input import decode_raw_video
frames,evidence=decode_raw_video(BASE/'OP00-import-decode-01/dev-0001.mp4',
    'a859467a06d77a075f54d02bb3a612b404e660abfc0592971116abe3edfa7333')
payload=frames.tobytes()
digest=hashlib.sha256(payload).hexdigest()
if digest!='a84c1b93cfad93327da304d22aeb5de5a9752b8adc9b2205a3c09ed1be349fd4':
    raise RuntimeError('Repeated board decoder output differs')
compressed=zlib.compress(payload,9)
encoded=base64.b64encode(compressed).decode('ascii')
metadata=dict(status='PASS',scope='board RGB reference export only',shape=list(frames.shape),
    dtype=str(frames.dtype),raw_bytes=len(payload),raw_sha256=digest,compressed_bytes=len(compressed),
    compressed_sha256=hashlib.sha256(compressed).hexdigest(),encoding='zlib+base64',decode=evidence,
    model_inference=False,self_sha256=args.self_sha256)
print('OP01_RGB_METADATA_BEGIN',flush=True)
print(json.dumps(metadata),flush=True)
print('OP01_RGB_METADATA_END',flush=True)
for offset in range(0,len(encoded),1024):
    print('OP01_RGB_CHUNK '+str(offset//1024)+' '+encoded[offset:offset+1024],flush=True)
print('OP01_RGB_EXPORT_END',flush=True)
