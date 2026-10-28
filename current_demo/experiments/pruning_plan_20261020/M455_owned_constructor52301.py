"""Attach the exact full M455 constructor to real configuration/owner guards.

No import-time hardware action. Call only from the admitted same-TTY runner.
Partial construction retains the instance, patched bindings and every owner.
"""
from pathlib import Path
from M455_dense_capacity52301 import DenseOriginalCapacity

class OwnedConstructor:
    def __init__(self,factory,pynq,np,ledger,state,configuration,clocks,result,admit_before_overlay):
        self.factory=factory;self.pynq=pynq;self.np=np;self.ledger=ledger;self.state=state
        self.configuration=configuration;self.clocks=clocks;self.result=result
        self.admit_before_overlay=admit_before_overlay
        self.runtime=None;self.patches=[];self.called=False;self.returned=False
    def patch(self,name,value):
        self.patches.append((name,getattr(self.pynq,name)));setattr(self.pynq,name,value)
    def construct(self,bit,language_root,head_root,language_contract,head_contract):
        if self.called or self.state.programmed or self.state.programming or self.ledger.buffers:
            raise RuntimeError('Fresh unprogrammed zero-owner constructor only')
        self.called=True;bit=Path(bit).resolve();original=self.pynq.Overlay;loads=[]
        def overlay(path,*args,**kwargs):
            if Path(path).resolve()!=bit or args or kwargs!={'download':True} or loads:
                raise RuntimeError('One exact original constructor Overlay call required')
            self.admit_before_overlay();self.state.programming=True
            answer=self.configuration.load(bit,original)
            # If load throws, programming remains unknown and the scope retains.
            self.state.programmed=True;self.state.programming=False;loads.append(1)
            self.clocks.normalize();self.result['constructor_actual_Overlay_calls']=len(loads)
            self.result['configuration_record']=self.configuration.record
            return answer
        allocator=DenseOriginalCapacity(self.ledger,self.np.uint8,self.result)
        self.patch('Overlay',overlay);self.patch('allocate',allocator)
        cls=self.factory['runtime_class'];self.runtime=cls.__new__(cls)
        cls.__init__(self.runtime,bit,Path(language_root),Path(head_root),Path(language_contract),Path(head_contract),
            weight_mode='staged-low-cma')
        self.returned=True;self.result['original_full_constructor_returned']=True
        self.state.admit_seven(self.ledger,self.runtime)
        if len(loads)!=1 or self.runtime.host_calls or self.runtime.logical_calls:
            raise RuntimeError('Constructor scope submitted work or configuration call differs')
        return self.runtime
    def restore_patches(self,check_safe):
        # Never restore a partial construction's bindings as an escape path.
        if not self.returned or self.state.unsafe() or self.ledger.allocating_unknown:
            raise RuntimeError('Partial constructor bindings retained')
        check_safe()
        for name,value in reversed(self.patches):setattr(self.pynq,name,value)
        self.patches=[]
