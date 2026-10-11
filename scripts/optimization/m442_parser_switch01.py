"""Select only the parser at an idle request boundary; no hardware calls."""
import threading
from board_safety import safe_to_release
from m442_runtime_adapter02 import make_candidate_runtime_class

ORIGINAL_SHA='d8061b561fe4d2a089523fde0d3860684244e76bca9646f255f03134fb50be56'
CANDIDATE_SHA='3069230b6ce2d1c06f9a2229f70922f0e7b9b5ab86e37985f8195b5deec88256'
class ParserSwitch:
    def __init__(self,runtime,policy,base,result,accepted_class,patch,*,enabled=False):
        if enabled is not True:raise RuntimeError('Parser comparison default disabled')
        self.runtime,self.policy,self.base,self.result=runtime,policy,base,result
        candidate=make_candidate_runtime_class(accepted_class)
        self.functions={'A':accepted_class._parse_into_and_check,'B':candidate._parse_into_and_check}
        self.buffers=tuple(runtime.staged_buffers)+(runtime.input_buffer,runtime.output_buffer,runtime.output_buffer_alt)
        self.ids=tuple(id(b) for b in self.buffers);self.addresses=tuple(base.physical_address(b) for b in self.buffers)
        if runtime._parse_into_and_check is not self.functions['A']:raise RuntimeError('Baseline parser binding differs')
        patch(runtime,'_parse_into_and_check',self.functions['A'])
        result.update(parser_selections=[],kernel_transitions=[],kernel_switch_environment=[],kernel_switch_minimal_attempts=0,parser_original_sha256=ORIGINAL_SHA,parser_candidate_sha256=CANDIDATE_SHA)
    def select(self,variant,index):
        if variant not in self.functions or index!=len(self.result['parser_selections'])+1:raise RuntimeError('Parser sequence differs')
        current=tuple(self.runtime.staged_buffers)+(self.runtime.input_buffer,self.runtime.output_buffer,self.runtime.output_buffer_alt)
        if tuple(id(b) for b in current)!=self.ids or tuple(self.base.physical_address(b) for b in current)!=self.addresses:raise RuntimeError('Original seven owners changed')
        if tuple(b.nbytes for b in current)!=(6963200,)*4+(389152,2621440,2621440):raise RuntimeError('Original geometry differs')
        if not self.policy.sealed or not self.policy.ever or not self.policy.completed or self.policy.active or not self.policy.safe() or self.policy.build!=0x4d343431:raise RuntimeError('Completed same M441 owner required')
        if self.result.get('language_scope_active') or self.result.get('vision_request_active') or self.result['released_buffers']:raise RuntimeError('Active/released request scope')
        if self.policy.thread is not None and self.policy.thread.is_alive():raise RuntimeError('Observer retained at parser boundary')
        if any(t.name.startswith(('m238-parse','m238-pack')) for t in threading.enumerate()):raise RuntimeError('Request worker retained')
        snapshot=self.base.transaction_snapshot(self.runtime.kernel,self.runtime.dma)
        if not safe_to_release(snapshot) or snapshot['ap_return']!=0x4d343431:raise RuntimeError('Completed Build proof required')
        self.policy.capture('before-untimed-parser-selection:'+str(index),True)
        self.runtime._parse_into_and_check=self.functions[variant]
        if self.runtime._parse_into_and_check is not self.functions[variant]:raise RuntimeError('Explicit parser binding failed')
        self.result['parser_selections'].append(dict(index=index,variant=variant,parser_sha256=ORIGINAL_SHA if variant=='A' else CANDIDATE_SHA,completed=True,original_buffer_identities_preserved=True,buffer_ids=list(self.ids),buffer_addresses=list(self.addresses),completed_snapshot=snapshot,outside_request_timer=True,extra_DMA=0,overlay_loads=0,fpga_transactions=0,parser_workers=1))
        return True
