"""Numerically proven binding with cheap order checks; no timed array export."""
from m429_pl_range import PLRangeScope,SavedWireCheck,SELECTED

class LightBatchCheck(SavedWireCheck):
    """Reuse strict saved metadata; complete feature SHA is checked after timer."""
    def __call__(self,index,part,chain,start,shift,packet):
        position=(index,part,start,shift)
        if len(self.seen)>=len(self.expected_position) or position!=self.expected_position[len(self.seen)]:raise ValueError('Frozen batch order differs')
        ref=self.references[str(index)][part][start//32]
        if len(packet)!=ref['input_bytes'] or chain['output_bytes']!=ref['output_bytes']:raise ValueError('Complete wire geometry differs')
        raw=self.submit(index,part,chain,start,shift,packet)
        if len(raw)!=ref['output_bytes']:raise ValueError('Complete output wire length differs')
        self.seen.append(position)
        return raw

class TimedPLRangeScope(PLRangeScope):
    """Same binding, release and hooks; avoid diagnostic tensor conversions."""
    def after(self,index,value):
        if index!=len(self.seen):raise RuntimeError('Boundary order differs')
        if self.active is not None:
            active_index,binding=self.active
            if active_index!=index or binding.calls!={'fc1':1,'fc2':1}:raise RuntimeError('Exactly two selected Linear calls required')
            if any([r['rows'] for r in binding.batches.get(k,[])]!=[32]*12+[8] for k in ('fc1','fc2')):raise RuntimeError('Original392-row T32 partition differs')
            self.release()
        output=value[0] if isinstance(value,tuple) else value
        if tuple(output.shape)!=(1,392,1024) or output.dtype!=self.torch.bfloat16:raise RuntimeError('Complete native BF16 boundary shape differs')
        self.seen.append(index)
        self.checkpoint('layer'+str(index)+':after')
