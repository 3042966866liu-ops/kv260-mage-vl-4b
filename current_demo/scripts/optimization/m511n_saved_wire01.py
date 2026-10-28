"""Strict saved JSON transport decoder; not a hardware gate checker."""
import base64,hashlib,json,re

def decode(text,check):
    if not callable(check):raise ValueError('An explicit complete gate validator is required')
    hashes=re.findall(r'(?m)^M511N_RAW_SHA256=([0-9a-f]{64})\r?$',text)
    if len(hashes)!=1:raise ValueError('Exactly one raw SHA required')
    entries=re.findall(r'(?m)^M511N_RAW_CHUNK=(\d+)/(\d+):([A-Za-z0-9+/=]+)\r?$',text)
    if not entries or len(entries)>4661:raise ValueError('Saved chunk count bound')
    total=int(entries[0][1]);parts={}
    if not 1<=total<=4661:raise ValueError('Invalid declared chunk count')
    for idx,count,b64 in entries:
        i=int(idx)
        if int(count)!=total or not 0<=i<total or i in parts:raise ValueError('Duplicate/inconsistent saved chunk')
        raw=base64.b64decode(b64,validate=True)
        if not 1<=len(raw)<=900 or i<total-1 and len(raw)!=900:raise ValueError('Saved part size differs')
        parts[i]=raw
    if set(parts)!=set(range(total)):raise ValueError('Incomplete saved result')
    raw=b''.join(parts[i] for i in range(total))
    if not 0<len(raw)<=4<<20 or hashlib.sha256(raw).hexdigest()!=hashes[0]:raise ValueError('Saved raw byte identity differs')
    result=json.loads(raw);check(result)
    return result,raw
