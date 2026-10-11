"""Only two instance Linear forwards; original native MLP/GELU/bias preserved."""
import numpy as np
def stage_windows(owner,part,rows,root):
    import stat,time
    tick=time.perf_counter_ns();read=0
    for b,row in zip(owner.buffers[:4],rows):
        p=root/row['relative_file']
        def identity():
            s=p.lstat()
            if not stat.S_ISREG(s.st_mode) or s.st_nlink!=1:raise RuntimeError('Plain original weight file required')
            return (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_mode,s.st_nlink)
        before=identity()
        if before[2]!=row['file_bytes']:raise RuntimeError('Original staged file size differs')
        with p.open('rb') as f:f.seek(row['offset']);raw=f.read(row['bytes'])
        if len(raw)!=row['bytes'] or identity()!=before:raise RuntimeError('Staging short read/file identity changed')
        b[:len(raw)]=np.frombuffer(raw,np.uint8);b.sync_to_device();read+=len(raw)
    return dict(part=part,bytes=read,elapsed_ns=time.perf_counter_ns()-tick)
class PLMLPBinding:
    def __init__(self,torch,mlp,chains,initial,host,stage,submit,expected=None):
        self.torch,self.mlp,self.chains,self.initial,self.host=torch,mlp,chains,initial,host
        self.stage,self.submit,self.expected=stage,submit,expected;self.previous=[];self.calls={};self.batches={};self.restored=False
    def bind(self,part):
        module=getattr(self.mlp,part)
        if module.output_dtype!=self.torch.float32 or module.bias is None:raise RuntimeError('Original FP32/bias required')
        owned='forward' in module.__dict__;old=module.__dict__.get('forward');self.previous.append((module,owned,old))
        def forward(values):
            self.calls[part]=self.calls.get(part,0)+1
            if self.calls[part]!=1:raise RuntimeError('One bounded isolated MLP only')
            arr=values.detach().cpu().numpy();native=arr.ndim==3 and arr.shape[0]==1
            if native:arr=arr[0]
            c=self.chains[part]
            if arr.dtype!=np.float32 or arr.ndim!=2 or arr.shape!=(392,c['groups']*64) or not np.isfinite(arr).all():raise ValueError('Actual finite single-batch392 FP32 input required')
            self.stage(part,c)
            width=max(d['row_start']+d['valid_rows'] for d in c['descriptors']);answer=np.empty((392,width),np.float32);rows=[]
            for start in range(0,392,32):
                block=arr[start:start+32];first=self.initial(block);attempts=[]
                if type(first) is not int or not 0<=first<=6:raise RuntimeError('Original initial shift differs')
                for shift in range(first,-1,-1):
                    attempts.append(shift);packet=self.host.pack_chain_input(c,block,c['stage_base_words'],activation_scale_shift=shift)
                    raw=self.submit(part,c,start,shift,packet)
                    if self.expected is not None:
                        saved=self.expected[(part,start,shift)]
                        if packet!=saved[0] or raw!=saved[1]:raise RuntimeError('Full saved packet/wire mismatch before performance')
                    try:
                        outputs=self.host.parse_chain_output(c,raw,output_scale_shift=shift)
                    except FloatingPointError:continue
                    value=outputs[c['module']]
                    if value.shape!=(32,width):raise RuntimeError('Complete original output geometry differs')
                    if not np.isfinite(value).all():continue
                    answer[start:start+len(block)]=value[:len(block)]
                    rows.append(dict(start=start,rows=len(block),initial_shift=first,attempted_shifts=attempts,selected_shift=shift,physical_calls=len(attempts)))
                    break
                else:raise FloatingPointError('Original finite retries exhausted; no clipping/fallback')
            self.batches[part]=rows
            result=self.torch.from_numpy(answer)+module.bias.to(self.torch.float32)
            return result.unsqueeze(0) if native else result
        module.forward=forward
    def __enter__(self):
        try:self.bind('fc1');self.bind('fc2')
        except BaseException:self.__exit__(None,None,None);raise
        return self
    def __exit__(self,*unused):
        for module,owned,old in reversed(self.previous):
            if owned:module.forward=old
            else:del module.__dict__['forward']
        self.restored=all(('forward' in m.__dict__)==owned and (not owned or m.__dict__['forward'] is old) for m,owned,old in self.previous);self.previous.clear()
        if not self.restored:raise RuntimeError('Instance forwards not restored')
        return False

def decision(samples):
    import statistics
    if len(samples)!=8 or ''.join(x['variant'] for x in samples)!='ABBABAAB':raise ValueError('Predeclared eight-segment order required')
    groups=[]
    for part in (samples[:4],samples[4:]):
        a=[x['elapsed_ns'] for x in part if x['variant']=='A'];b=[x['elapsed_ns'] for x in part if x['variant']=='B']
        saved=statistics.mean(a)-statistics.mean(b);noise=max(max(a)-min(a),max(b)-min(b))
        groups.append(dict(order=''.join(x['variant'] for x in part),cpu_ns=a,pl_ns=b,mean_saved_ns=saved,within_variant_range_ns=noise,positive_and_exceeds_range=saved>0 and saved>noise))
    a=[x['elapsed_ns'] for x in samples if x['variant']=='A'];b=[x['elapsed_ns'] for x in samples if x['variant']=='B']
    gain=1-statistics.mean(b)/statistics.mean(a)
    return dict(groups=groups,cpu_mean_ns=statistics.mean(a),pl_mean_ns=statistics.mean(b),mean_gain=gain,minimum_gain=.05,
        performance_pass=all(x['positive_and_exceeds_range'] for x in groups) and gain>=.05,extra_sampling_allowed=False)
