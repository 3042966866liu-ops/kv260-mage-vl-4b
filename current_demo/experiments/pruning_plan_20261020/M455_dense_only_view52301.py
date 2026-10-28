"""Read-only M455 ABI facade for the original visual provider.

The historical ResidentOutputABI starts at Build M443 and mutates parser/
contract globals. This facade exposes only the already constructed M455 path.
"""
from types import SimpleNamespace
SIZES=(6963200,)*4+(389152,2621440,2621440)
class DenseOnlyView:
    @property
    def variant(self):return 'B'
    def __init__(self,factory,runtime,ledger,idle):
        if not callable(idle):raise ValueError('Actual original owner idle predicate required')
        idle();ledger.verify_full(runtime)
        self.factory,self.runtime,self.ledger,self.idle=factory,runtime,ledger,idle
        self.base=factory['base'];self.contract=factory['contract']
        if self.base.BUILD_ID!=0x4D343535:raise ValueError('Actual M455 factory required')
        self.buffers=tuple(runtime.staged_buffers)+(runtime.input_buffer,runtime.output_buffer,runtime.output_buffer_alt)
        if tuple(b.nbytes for b in self.buffers)!=SIZES:raise ValueError('Actual original seven owners required')
        self.ids=tuple(map(id,self.buffers));self.addresses=tuple(self.base.physical_address(b) for b in self.buffers)
        for table in (runtime.language_contract,runtime.head_contract):
            if any(c.get('expected_build_id')!=0x4D343535 for c in table.chains):raise ValueError('Original constructor must already return dense M455 tables')
    def check_chain(self,chain):
        if self.base.BUILD_ID!=0x4D343535 or chain.get('expected_build_id')!=0x4D343535 or chain.get('output_abi')!='m455-dense-fp16-block-token-shard-pair-v1':raise ValueError('Exact current M455 dense ABI required')
        if sum(d['output_bytes'] for d in chain['descriptors'])!=chain['output_bytes']:raise ValueError('Complete current output geometry required')
    def pack(self,chain,*a,**kw):
        self.check_chain(chain);return self.contract.pack_chain_input(chain,*a,**kw)
    def parse(self,chain,*a,**kw):
        self.check_chain(chain);return self.contract.parse_chain_output(chain,*a,**kw)
    def visual_host(self):return SimpleNamespace(pack_chain_input=self.pack,parse_chain_output=self.parse)
    def require_current(self):
        self.idle();self.ledger.verify_full(self.runtime)
        current=tuple(self.runtime.staged_buffers)+(self.runtime.input_buffer,self.runtime.output_buffer,self.runtime.output_buffer_alt)
        if tuple(map(id,current))!=self.ids or tuple(self.base.physical_address(b) for b in current)!=self.addresses:raise RuntimeError('Original owner identity/address drift')
