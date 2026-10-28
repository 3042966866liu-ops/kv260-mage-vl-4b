"""M455-only observed dispatch and family worker boundary; no hardware imports.

Use original AST observer insertion, without mutating the stable BUILD global.
The supplied owner/configuration/MMIO predicates remain mandatory and real.
"""
import copy,threading
from b0_transaction_guard523 import TransactionGuard
BUILD=0x4D343535

def completed(snapshot):
    if any(snapshot.get(k)!='' for k in ('kernel_read_error','return_read_error','dma_read_error')):return False
    if any(type(snapshot.get(k)) is not int or snapshot[k]<0 for k in ('ap_ctrl','ap_return','mm2s_dmasr','s2mm_dmasr')):return False
    if snapshot['ap_return']!=BUILD or not snapshot['ap_ctrl']&4:return False
    for channel in ('mm2s','s2mm'):
        status=snapshot[channel+'_dmasr']
        if snapshot.get(channel+'_error') is not False or not status&3 or status&0x770:return False
    return True

class M455TransactionGuard(TransactionGuard):
    def __init__(self,chains,snapshot_reader,check_before,result,physical_budget):
        if type(physical_budget) is not int or not 1<=physical_budget<=42:raise ValueError('Finite local dispatch budget')
        super().__init__(chains,snapshot_reader,check_before,result)
        self.physical_budget=physical_budget
    def safe(self):
        if self.active:return False
        s=self.snapshot_reader()
        if self.ever:return self.complete and completed(s)
        return (all(s.get(k)=='' for k in ('kernel_read_error','return_read_error','dma_read_error'))
            and s.get('ap_ctrl')==4 and s.get('ap_return')==0
            and s.get('mm2s_dmasr')==s.get('s2mm_dmasr')==0
            and s.get('mm2s_error') is False and s.get('s2mm_error') is False)
    def before(self,method,chain,input_bytes,output_bytes):
        if len(self.result.get('transactions',[]))>=self.physical_budget:raise RuntimeError('Local physical budget exhausted')
        return super().before(method,chain,input_bytes,output_bytes)
    def after(self,snapshot):
        if not self.active or self.current is None or not completed(snapshot):
            raise RuntimeError('Actual M455 completion unproven; retain owners')
        self.current.update(completed=True,completed_boundary_ns=self.clock(),snapshot=copy.deepcopy(snapshot))
        self.active=False;self.complete=True;self.current=None

def workers():
    return tuple(t for t in threading.enumerate() if t.name.startswith(('m238-pack','m238-parse')))

class FamilyBoundary:
    """Track entry through original joined ThreadPoolExecutor family methods."""
    def __init__(self,guard,check_resources,result):
        self.guard=guard;self.check_resources=check_resources;self.result=result
        self.active=False;self.latched=False
    def idle(self):
        if self.active or self.latched or workers() or not self.guard.safe():
            raise RuntimeError('Family/worker/DMA ownership unresolved')
        self.check_resources()
    def call(self,runtime,layer,family,values):
        self.idle();self.active=True
        row=dict(layer=layer,family=family,returned=False,workers_joined=False)
        self.result.setdefault('family_boundaries',[]).append(row)
        try:
            answer=runtime.language_family_many(layer,family,values)
            row['returned']=True
            return answer
        finally:
            row['workers_joined']=not workers()
            self.active=False
            if not row['workers_joined'] or not self.guard.safe():self.latched=True
