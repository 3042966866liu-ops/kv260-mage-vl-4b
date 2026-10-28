"""Observed original dispatch shared with the real borrowed visual owner.

No device API. Every transition requires the original lifecycle and real caller
snapshot/resource predicates; no constant-safe or invented completion state.
"""
import copy,math
from b0_transaction_guard523 import TransactionGuard
from M455_adaptive_guard52301 import M455TransactionGuard,completed,workers
def physical_bound(prompt_tokens,output_tokens,*,visual):
    if type(prompt_tokens)is not int or not 1<=prompt_tokens<=160 or type(output_tokens)is not int or not 1<=output_tokens<=32 or type(visual)is not bool:raise ValueError('Explicit bounded native workload required')
    # At most all154 registered language chains per T32 prompt/decode block,
    # eight original head chains per output and seven original shift attempts.
    bound=7*(154*(math.ceil(prompt_tokens/32)+output_tokens-1)+8*output_tokens+(286 if visual else 0))
    if not 1<=bound<=71000:raise ValueError('Native32-token physical bound exceeded')
    return bound
class RequestTransactionGuard(M455TransactionGuard):
    def __init__(self,chains,snapshot_reader,check_before,result,state):
        TransactionGuard.__init__(self,chains,snapshot_reader,check_before,result)
        self.state=state;self.request=None
    def safe(self):return not self.state.unsafe() and M455TransactionGuard.safe(self)
    def set_chains(self,chains):
        if self.request is not None or workers() or not self.safe():raise RuntimeError('Chain selection requires proven idle original owner')
        if not isinstance(chains,list) or not chains:raise ValueError('Actual active chain table required')
        self.chains=copy.deepcopy(chains)
    def begin(self,label,budget):
        if self.request is not None or workers() or not self.safe():raise RuntimeError('Previous request ownership unresolved')
        if not isinstance(label,str) or not label or type(budget)is not int or not 1<=budget<=71000:raise ValueError('Explicit finite request budget required')
        self.check_before();self.request=dict(label=label,first_transaction=len(self.result.get('transactions',[])),physical_budget=budget,returned=False)
        self.result.setdefault('request_boundaries',[]).append(self.request)
    def before(self,method,chain,input_bytes,output_bytes):
        if self.request is None:raise RuntimeError('Physical dispatch outside explicit request')
        if len(self.result.get('transactions',[]))-self.request['first_transaction']>=self.request['physical_budget']:raise RuntimeError('Current finite request budget exhausted before submit')
        TransactionGuard.before(self,method,chain,input_bytes,output_bytes)
        self.state.before_submit()
    def after(self,snapshot):
        M455TransactionGuard.after(self,snapshot)
        self.state.after_submit(snapshot,completed)
    def end(self):
        if self.request is None or workers() or not self.safe():raise RuntimeError('Request DMA/worker completion unproven')
        self.check_before();self.request.update(returned=True,physical_calls=len(self.result.get('transactions',[]))-self.request['first_transaction']);self.request=None
class BorrowedPolicyBridge:
    """Alias the original BorrowedVisual policy interface to shared real state."""
    build=0x4D343535
    def __init__(self,guard,ledger,runtime,check_resources):
        self.guard,self.ledger,self.runtime,self.check_resources=guard,ledger,runtime,check_resources
        ledger.verify_full(runtime)
    @property
    def sealed(self):return self.ledger.sealed and self.guard.state.initialized and not self.ledger.allocating_unknown
    @property
    def buffer_bytes(self):return tuple(int(b.nbytes) for b in self.ledger.buffers)
    @property
    def active(self):return self.guard.active
    @active.setter
    def active(self,value):
        if type(value)is not bool or self.guard.current is not None:raise RuntimeError('Borrowed manual transition overlaps original dispatch')
        if value and self.guard.request is None:raise RuntimeError('Borrowed submit outside explicit request')
        self.guard.active=value;self.guard.state.active=value
    @property
    def ever(self):return self.guard.ever
    @ever.setter
    def ever(self,value):
        if value is not True:raise RuntimeError('Original submission history cannot be erased')
        self.guard.ever=True;self.guard.state.ever=True
    @property
    def completed(self):return self.guard.complete
    @completed.setter
    def completed(self,value):
        if type(value)is not bool:raise ValueError('Actual original completion flag required')
        if value and (self.guard.active or not completed(self.guard.snapshot_reader())):raise RuntimeError('Borrowed completion requires actual M455 snapshot')
        self.guard.complete=value;self.guard.state.completed=value
    def safe(self):return not self.ledger.allocating_unknown and self.guard.safe()
    def capture(self,label,required):
        if required is not True or not self.safe():raise RuntimeError('Actual shared borrowed owner idle unproven')
        self.check_resources()
