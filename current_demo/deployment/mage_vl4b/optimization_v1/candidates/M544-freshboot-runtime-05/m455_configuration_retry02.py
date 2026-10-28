"""Actual M455 configuration observer; no credit without complete same-PID/PFN proof."""
import hashlib,json,os,platform,time
from pathlib import Path
from m455_cma_retry_contract02 import validate
from m455_cma_trace01 import Trace

BIT='e1b5b9e6cb84325820e1150528d1e4117d30e924e777246576a35acb5332e4b8'
SHELL='a61392fbef5f37448bad776a4434ba164906fbb9965269a19bdc8981f691e0cb'
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read_counts():
    root=Path('/sys/kernel/mm/cma');result={}
    if not root.is_dir():raise RuntimeError('CMA counters unavailable')
    for area in sorted(root.iterdir()):
        if not area.is_dir():continue
        for name in ('alloc_pages_success','alloc_pages_fail'):
            value=int((area/name).read_text(encoding='ascii').strip())
            if value<0:raise RuntimeError('Invalid cumulative counter')
            result[area.name+':'+name]=value
    if not result:raise RuntimeError('No cumulative CMA counters')
    return result

def validate_application(application):
    expected=dict(status='PROPOSED_M455_CONFIGURATION_APPLICATION_NOT_BOARD_VERIFIED',build_id='0x4D343535',
        bit_sha256=BIT,bit_bytes=7797914,pages=1904,page_size=4096,kernel='5.15.0-1027-xilinx-zynqmp',
        same_PID=True,same_PFN_release_required=True,exact_counter_delta={'reserved:alloc_pages_success':1904,'reserved:alloc_pages_fail':0},
        trace_limit_bytes=1<<20,trace_budget_s=30,unknown_or_failed_allocations_rejected=True,
        original_baseline_reset_allowed=False,seven_owner_policy_unchanged=True,PS_budget_unchanged=True,
        old_CMA15_whitelist_modified=False,actual_configuration_proof_required_before_credit=True,
        credits_granted=0,board=False)
    if application!=expected:raise RuntimeError('Frozen exact-bit application differs')
    return expected

def validate_record(record,application_sha,manifest_sha):
    if record['application_sha256']!=application_sha or record['manifest_sha256']!=manifest_sha or record['shell_closure_sha256']!=SHELL:
        raise RuntimeError('Configuration provenance differs')
    if record['observation_kind']!='same-process-kernel-CMA-trace' or record['overlay_returned'] is not True:
        raise RuntimeError('No completed actual configuration observation')
    if record['configuration_credits_granted']!=0:raise RuntimeError('Lower gate cannot grant resident policy credit')
    return validate(record)

class Configuration:
    """Unknown programming ownership retains this object and its Overlay."""
    def __init__(self,application_path,manifest_sha,evidence,*,counters=read_counts,trace_factory=Trace,
                 kernel=platform.release,page_size=lambda:os.sysconf('SC_PAGE_SIZE'),pid=os.getpid):
        p=Path(application_path);validate_application(json.loads(p.read_bytes()))
        self.application_sha=sha(p);self.manifest_sha=manifest_sha;self.evidence=Path(evidence)
        self.counters=counters;self.trace_factory=trace_factory;self.kernel=kernel;self.page_size=page_size;self.pid=pid
        self.overlay=None;self.unknown=False;self.record=None
    def load(self,bit,loader):
        bit=Path(bit)
        if sha(bit)!=BIT or bit.stat().st_size!=7797914:raise RuntimeError('Exact candidate bit required before programming')
        if self.unknown or self.record is not None:raise RuntimeError('Configuration attempt already exists')
        record=dict(bit_sha256=sha(bit),bit_bytes=bit.stat().st_size,pages=1904,kernel=self.kernel(),
            page_size=self.page_size(),pid=self.pid(),application_sha256=self.application_sha,
            manifest_sha256=self.manifest_sha,shell_closure_sha256=SHELL,observation_kind='same-process-kernel-CMA-trace',
            configuration_credits_granted=0,overlay_returned=False)
        self.record=record
        # Validate prerequisites without programming, never infer them from a rerun.
        if record['kernel']!='5.15.0-1027-xilinx-zynqmp' or record['page_size']!=4096:
            raise RuntimeError('Original kernel/page-size contract differs')
        trace=self.trace_factory(self.evidence)
        prepared=False;started=False
        try:
            trace.prepare();prepared=True
            record['before']=self.counters()
            trace.started=time.monotonic();trace.start();started=True
            # Set before calling the actual programming API: any exception preserves ownership.
            self.unknown=True
            self.overlay=loader(str(bit),download=True)
            record['overlay_returned']=True
        finally:
            if prepared or getattr(trace,'created',False):
                if not started:trace.started=time.monotonic()
                record['trace']=trace.stop()
            if self.unknown:record['after']=self.counters()
        validate_record(record,self.application_sha,self.manifest_sha)
        self.unknown=False
        return self.overlay
