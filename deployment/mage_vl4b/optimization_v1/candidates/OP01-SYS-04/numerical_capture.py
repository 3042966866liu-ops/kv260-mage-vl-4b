"""Opt-in diagnostic proxy, NOT a performance benchmark or numerical acceptance.

Records genuine synchronized model returns without replacing model arithmetic,
tokens, or KV. Never attach to a formal timing run: I/O is deliberately visible.
"""
import os
from pathlib import Path
import time
import numpy as np
from measurement import sha256,write_json


class NumericalCapture:
    def __init__(self,model,directory,*,identity,max_steps=128):
        if isinstance(max_steps,bool) or not isinstance(max_steps,int) or not 1<=max_steps<=128:
            raise ValueError('Diagnostic step bound must be1..128')
        self.model=model;self.root=Path(directory);self.root.mkdir(parents=True,exist_ok=False)
        self.max_steps=max_steps;self.prefilled=False;self.cache=None
        self.report=dict(status='RECORDING',scope='Diagnostic only; timing invalid for performance gates',
                         numerical_acceptance=False,identity=identity,steps=[],arrays={})
        self._persist()

    def _persist(self):write_json(self.root/'manifest.json',self.report)

    def _array(self,name,value):
        a=np.asarray(value)
        if a.dtype.kind not in 'fiu' or not np.isfinite(a).all():raise ValueError('Invalid numeric tensor: '+name)
        path=self.root/(name+'.npy')
        if path.exists():raise RuntimeError('Capture path already exists')
        temporary=path.with_suffix('.partial')
        with temporary.open('xb') as stream:
            np.save(stream,a,allow_pickle=False);stream.flush();os.fsync(stream.fileno())
        os.replace(temporary,path)
        self.report['arrays'][name]=dict(file=path.name,shape=list(a.shape),dtype=str(a.dtype),sha256=sha256(path))

    def _capture(self,token,logits,cache,*,phase,input_token):
        index=len(self.report['steps']);started=time.perf_counter()
        prefix=f'step{index:03d}'
        self._array(prefix+'_logits',logits)
        lengths=[]
        if len(cache.keys)!=len(cache.values) or not cache.keys:raise ValueError('Invalid KV layers')
        for key,value in zip(cache.keys,cache.values):
            if key.shape!=value.shape or key.ndim!=3 or not key.shape[0]:raise ValueError('Invalid KV geometry')
            lengths.append(key.shape[0])
        if len(set(lengths))!=1:raise ValueError('Unequal layer KV lengths')
        # Last-token per-layer slices support boundary diagnostics without
        # allocating/storing the entire growing cache again at every step.
        self._array(prefix+'_last_keys',np.stack([k[-1] for k in cache.keys]))
        self._array(prefix+'_last_values',np.stack([v[-1] for v in cache.values]))
        self.report['steps'].append(dict(index=index,phase=phase,input_token=input_token,
            output_token=int(token),kv_length=lengths[0],capture_seconds=time.perf_counter()-started))
        self._persist()

    def _failed(self,exc):
        self.report.update(status='FAIL',error=f'{type(exc).__name__}: {exc}');self._persist()

    def prefill(self,hidden):
        if self.prefilled:raise RuntimeError('One prefill per diagnostic request')
        self.prefilled=True
        try:
            self._array('prefill_hidden',hidden)
            result=self.model.prefill(hidden)
            token,logits,self.cache=result
            self._capture(token,logits,self.cache,phase='prefill',input_token=None)
            return result
        except Exception as exc:self._failed(exc);raise

    def decode(self,token,cache):
        if not self.prefilled or cache is not self.cache:raise RuntimeError('Wrong request cache')
        if len(self.report['steps'])>=self.max_steps:raise RuntimeError('Diagnostic step bound reached')
        try:
            result=self.model.decode(token,cache)
            self._capture(*result,cache,phase='decode',input_token=int(token))
            return result
        except Exception as exc:self._failed(exc);raise

    def finish(self,reason):
        if self.report['status']=='FAIL':return
        if reason not in ('eos','length') or not self.report['steps']:raise ValueError('Incomplete diagnostic')
        self.report.update(status='RECORDED',finish_reason=reason);self._persist()

    def __getattr__(self,name):return getattr(self.model,name)
