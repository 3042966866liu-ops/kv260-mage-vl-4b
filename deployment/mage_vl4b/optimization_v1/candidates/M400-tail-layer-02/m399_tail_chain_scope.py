"""Default-off last31 chain checks. Original packing, staging and parsing stay intact."""
import hashlib
import json
from pathlib import Path
import stat
import threading
import numpy as np
from m368_video_contract import tensor
from m398_reference_capture import SHAPES

class RetainedChainOwnerError(RuntimeError):pass

PLAN=(('attention_out','attention_out_input_tail',{'self_attn.o_proj':'attention_out_output_tail'}),
      ('gate_up','gate_up_input_tail',{'mlp.gate_proj':'gate_tail','mlp.up_proj':'up_tail'}),
      ('mlp_down','mlp_down_input_tail',{'mlp.down_proj':'mlp_down_output_tail'}))

def identity(path):
    s=path.lstat()
    if not stat.S_ISREG(s.st_mode) or s.st_nlink!=1:raise RuntimeError('Plain sole-linked reference file required')
    return (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_mode,s.st_nlink)

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        while True:
            b=f.read(1<<20)
            if not b:break
            h.update(b)
    return h.hexdigest()

class TailChainScope:
    def __init__(self,model,policy,resident,reference_path,reference_sha,*,enabled=False):
        if not enabled:raise RuntimeError('M399 disabled by default')
        self.model=model;self.policy=policy;self.resident=resident;self.closed=False;self.retained=False
        self.rows=[];self.maps={};self.identities={};self.reference_path=Path(reference_path)
        self.barrier()
        self.raw_identity=identity(self.reference_path)
        if digest(self.reference_path)!=reference_sha:raise RuntimeError('Recovered original raw SHA differs')
        self.reference_sha=reference_sha;r=json.loads(self.reference_path.read_text(encoding='utf-8'))
        if r['status']!='PASS_M398_ORIGINAL_TAIL_REFERENCE' or r['gate_return_code'] or not r['reference_capture_pass'] or r['tail_candidate_executed'] or r['candidate_numerical_pass']:raise RuntimeError('Original reference-only prerequisite required')
        c=r['reference_capture']
        if not c['closed'] or c['retained'] or not c['binding_callback_removed'] or not c['candidate_tail_not_executed'] or c['file_count']!=12 or set(c['fixtures'])!=set(SHAPES):raise RuntimeError('Original capture lifetime/inventory differs')
        self.fixtures=c['fixtures']
        if identity(self.reference_path)!=self.raw_identity:raise RuntimeError('Original raw changed during read')
    def barrier(self):
        if not self.resident() or not self.policy.safe() or any(t.name.startswith(('m238-pack','m238-parse')) for t in threading.enumerate()):raise RetainedChainOwnerError('Complete runtime/safe DMA/drained workers required')
    def load(self,name):
        if name in self.maps:raise RuntimeError('Unexpected reused reference')
        f=self.fixtures[name];path=self.reference_path.parent/(name+'.npy')
        if f['path']!=str(path) or f['tensor']['shape']!=list(SHAPES[name]) or f['tensor']['dtype']!='float32' or f['original_token_start']!=128:raise RuntimeError('Actual last31 fixture contract differs')
        before=identity(path)
        if before[2]!=f['file_bytes'] or digest(path)!=f['file_sha256']:raise RuntimeError('Fixture file SHA differs')
        a=np.load(path,allow_pickle=False,mmap_mode='r');self.maps[name]=a;self.identities[name]=before
        if a.dtype!=np.float32 or a.shape!=SHAPES[name] or not a.flags.c_contiguous or not np.isfinite(a).all() or tensor(a)!=f['tensor'] or identity(path)!=before:raise RuntimeError('NPY tensor/identity differs')
        return a
    def check_unchanged(self):
        if identity(self.reference_path)!=self.raw_identity or digest(self.reference_path)!=self.reference_sha:raise RuntimeError('Original raw changed')
        for name,a in self.maps.items():
            path=self.reference_path.parent/(name+'.npy');f=self.fixtures[name]
            if identity(path)!=self.identities[name] or digest(path)!=f['file_sha256'] or tensor(a)!=f['tensor']:raise RuntimeError('Reference changed during chain use')
    def run(self):
        if self.closed or self.retained or self.rows:raise RetainedChainOwnerError('Only one live chain sequence allowed')
        try:
            for family,source,goldens in PLAN:
                self.barrier();self.policy.capture('before-last31-chain:'+family,True)
                values=self.load(source);expected={key:self.load(name) for key,name in goldens.items()}
                output=self.model._family(35,family,values)
                self.barrier();self.policy.capture('after-last31-chain:'+family,True)
                prefix='model.language_model.layers.35.'
                if set(output)!={prefix+k for k in goldens}:raise RuntimeError('Chain output keys differ')
                for key,reference in expected.items():
                    actual=output[prefix+key]
                    if actual.dtype!=np.float32 or actual.shape!=reference.shape or not np.array_equal(actual.view(np.uint32),reference.view(np.uint32)):raise RuntimeError('Full last31 chain output differs: '+family)
                self.check_unchanged()
                self.rows.append(dict(layer=35,family=family,original_token_start=128,local_token_start=0,tokens=31,input=tensor(values),output={k:tensor(v) for k,v in output.items()},full_output_bitwise_equal=True))
                del output,expected,values
            self.barrier()
            return list(self.rows)
        except BaseException as exc:
            self.retained=True
            raise RetainedChainOwnerError('Chain failed; retain process, reference maps and original DMA owner') from exc
    def close(self):
        if self.closed:return
        if self.retained:raise RetainedChainOwnerError('Failed chain resources retained')
        try:
            self.barrier();self.check_unchanged()
        except BaseException as exc:
            self.retained=True
            raise RetainedChainOwnerError('Close failed; retain original DMA owner and reference maps') from exc
        for a in self.maps.values():a._mmap.close()
        self.maps.clear();self.model=self.policy=self.resident=None;self.closed=True
    def report(self):
        return dict(closed=self.closed,retained=self.retained,reference_sha256=self.reference_sha,reference_files_checked=len(self.identities),
                    reference_maps_released=not self.maps,chains=list(self.rows),extra_DMA=0,original_parser_workers=1,
                    PS_prefetch=False,SiLU_workspace=False,full_model_candidate_executed=False,performance_pass=False)
