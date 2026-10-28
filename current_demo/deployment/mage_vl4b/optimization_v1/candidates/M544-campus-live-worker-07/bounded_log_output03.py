"""Bounded persistent result saves, delegating unchanged original atomic writer."""
import json,os
from pathlib import Path
class LogBudget:
    def __init__(self,root,original,record,*,limit=48<<20,reserve=64<<20):
        self.root=Path(root).resolve();self.original=original;self.record=record;self.limit=limit;self.reserve=reserve;self.used=0;self.count=0
        assert self.root.stat().st_dev!=Path('/dev/shm').stat().st_dev
    def save(self,path,value):
        path=Path(path);assert path.resolve().is_relative_to(self.root)
        raw=(json.dumps(value,sort_keys=True,indent=2)+'\n').encode()
        assert len(raw)<=8<<20 and self.used+len(raw)<=self.limit,'Frozen48MiB per-run diagnostic bound reached'
        fs=os.statvfs(str(self.root));assert fs.f_bavail*fs.f_frsize>=len(raw)+self.reserve,'Persistent64MiB reserve unavailable'
        self.original(path,value)
        assert path.stat().st_size==len(raw)
        self.used+=len(raw);self.count+=1
        self.record['persistent_log_budget']=dict(limit_bytes=self.limit,reserve_bytes=self.reserve,written_bytes=self.used,files=self.count,TTFT_interval_excluded=True,serialization_and_original_atomic_writer_unchanged=True)
