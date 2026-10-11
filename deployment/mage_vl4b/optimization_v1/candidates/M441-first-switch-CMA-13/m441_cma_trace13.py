"""One first-switch diagnostic. Never relax the original CMA admission policy."""
import hashlib
import json
import os
from pathlib import Path
import re
import time
import traceback

TRACE_NAME='m441_first_switch_cma13'
EVENTS=('cma_alloc_start','cma_alloc_finish','cma_alloc_busy_retry','cma_release')
MAX_TRACE_BYTES=1024*1024
DETAILS={}

def digest(raw):return hashlib.sha256(raw).hexdigest()

def save(path,value):
    raw=(json.dumps(value,ensure_ascii=True,separators=(',',':'),allow_nan=False)+'\n').encode()
    temp=path.with_name(path.name+'.partial')
    with temp.open('wb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
    os.replace(temp,path)

class Trace:
    def __init__(self,evidence):
        self.path=Path('/sys/kernel/tracing/instances')/TRACE_NAME
        self.evidence=evidence;self.created=False;self.enabled=[]
        self.details=dict(instance=str(self.path),pid=os.getpid(),owned_instance_only=True,shared_root_configuration_changed=False)

    def put(self,relative,text):(self.path/relative).write_text(str(text),encoding='ascii')

    def start(self):
        self.path.mkdir(exist_ok=False);self.created=True
        self.put('tracing_on','0');self.put('buffer_size_kb','128')
        self.put('options/stacktrace','1')
        self.details['event_formats']={n:(self.path/f'events/cma/{n}/format').read_text() for n in EVENTS}
        for n in EVENTS:
            self.put(f'events/cma/{n}/enable','1');self.enabled.append(n)
        self.put('tracing_on','1');self.put('trace_marker','M441_FIRST_SWITCH_BEGIN')

    def stop(self):
        errors=[]
        try:
            self.put('trace_marker','M441_FIRST_SWITCH_END');self.put('tracing_on','0')
            trace=(self.path/'trace').read_bytes()
            if len(trace)>MAX_TRACE_BYTES:raise RuntimeError('Trace exceeds fixed 1MiB bound')
            self.details['trace_text']=trace.decode('utf-8');self.details['trace_sha256']=digest(trace)
            self.details['stats']={p.parent.name:p.read_text() for p in sorted((self.path/'per_cpu').glob('cpu*/stats'))}
            self.details['elapsed_trace_s']=time.monotonic()-self.started
            (self.evidence/'CMA_TRACE.txt').write_bytes(trace)
        except BaseException as exc:errors.append(traceback.format_exc())
        finally:
            if self.created:
                try:
                    self.put('tracing_on','0')
                    for n in self.enabled:self.put(f'events/cma/{n}/enable','0')
                    self.put('options/stacktrace','0')
                    self.path.rmdir();self.details['own_instance_removed']=True
                except BaseException:errors.append(traceback.format_exc())
        self.details['observer_errors']=errors
        return self.details

def narrow_run(engine,runtime,policy,base,here,evidence,result,patch,features,provider,switch):
    """Replace only the trial dispatcher: initial B proof then a single A switch."""
    result.update(gate_level='first-switch-CMA-diagnostic',experiment_scope='Zero model requests; original initial B minimal then exactly one B-to-A minimal; unchanged admission guard',samples=[],diagnostic_only=True)
    assert runtime.host_calls==runtime.logical_calls==0
    assert not result.get('model_forward_calls')
    assert not result.get('vision_forward_calls')
    expected_sources=json.loads((Path(__file__).parent/'SOURCE_IDENTITIES.json').read_bytes())
    for row in expected_sources:
        if digest(Path(row['path']).read_bytes())!=row['sha256']:raise RuntimeError('Installed programming source drift')
    original_loader=switch.load_overlay
    trace=Trace(evidence)
    def traced_loader(path):
        DETAILS['before_program_counts']=policy.counters()
        DETAILS['before_program_memory']=policy.snapshot()
        DETAILS['bit_path']=path;DETAILS['bit_bytes']=Path(path).stat().st_size
        DETAILS['bit_sha256']=digest(Path(path).read_bytes())
        DETAILS['page_size']=os.sysconf('SC_PAGE_SIZE')
        DETAILS['maximum_bitstream_pages']=(DETAILS['bit_bytes']+DETAILS['page_size']-1)//DETAILS['page_size']
        trace.started=time.monotonic()
        try:
            trace.start()  # Any trace preflight failure happens before programming.
            return original_loader(path)
        finally:
            DETAILS['trace']=trace.stop() if trace.created else trace.details
            DETAILS['after_program_counts']=policy.counters()
            DETAILS['after_program_memory']=policy.snapshot()
            save(evidence/'DIAGNOSTIC_PROGRESS.json',DETAILS)
    switch.load_overlay=traced_loader
    try:
        switch.select('A',1)
        raise RuntimeError('Diagnostic stops here; no complete-request trial is permitted')
    except BaseException:
        DETAILS['after_minimal_or_failure_counts']=policy.counters()
        DETAILS['after_minimal_or_failure_memory']=policy.snapshot()
        DETAILS['original_guard_exception']=traceback.format_exc()
        save(evidence/'DIAGNOSTIC_PROGRESS.json',DETAILS)
        raise
    finally:provider.dispose()

def flatten_counts(counts):
    # Preserve arbitrary actual area naming; the original policy supplies this schema.
    return {str(k):v for k,v in counts.items()}

def verdict(gate):
    d=dict(DETAILS)
    d['status']='INCONCLUSIVE_M441_CMA_TRACE13'
    d['old_guard_unchanged']=True;d['original_gate_rc']=gate['gate_return_code']
    d['model_requests']=0;d['performance_pass']=False;d['new_DMA_allowed']=False
    text=d.get('trace',{}).get('trace_text','')
    records=[]
    for line in text.splitlines():
        match=re.search(r'\b(cma_alloc_start|cma_alloc_finish|cma_alloc_busy_retry|cma_release):\s*(.*)',line)
        if match:records.append(dict(event=match[1],fields=match[2],line=line))
    d['events']=records
    problems=[]
    before=d.get('before_program_counts',{});after=d.get('after_program_counts',{})
    if not before or set(before)!=set(after):problems.append('Missing counter identities')
    else:
        d['counter_deltas']={k:after[k]-before[k] for k in before}
        success=[v for k,v in d['counter_deltas'].items() if k.endswith(':alloc_pages_success')]
        if len(success)!=1 or success[0]!=d.get('maximum_bitstream_pages') or any(v for k,v in d['counter_deltas'].items() if k.endswith(':alloc_pages_fail')):problems.append('Counter delta does not equal one successful bitstream allocation')
        if d.get('after_minimal_or_failure_counts')!=after:problems.append('Extra allocation after programming')
    if len(records)!=3 or [r['event'] for r in records]!=['cma_alloc_start','cma_alloc_finish','cma_release']:problems.append('Expected exactly start/finish/release; unknown event or allocation')
    for r in records:
        m=re.search(r'\bcount(?:=|\s+)(\d+)',r['fields'])
        if not m or int(m[1])!=d.get('maximum_bitstream_pages'):problems.append('Actual count differs from bitstream page bound')
        if not re.search(r'-'+str(d.get('trace',{}).get('pid'))+r'\s',r['line']):problems.append('Event task differs from programming process')
    if len(records)==3:
        pfns=[re.search(r'\bpfn(?:=|\s+)(0x[0-9a-fA-F]+|\d+)',r['fields']) for r in records[1:]]
        if any(m is None for m in pfns) or pfns[0][1]!=pfns[1][1]:problems.append('Allocated and released PFN differ')
    if 'zynqmp_fpga' not in text or 'dma_alloc' not in text:problems.append('Kernel stack does not directly attribute allocation to FPGA driver')
    for stats in d.get('trace',{}).get('stats',{}).values():
        for name in ('overrun','commit overrun','dropped events'):
            m=re.search(r'^'+re.escape(name)+r':\s*(\d+)',stats,re.M)
            if m and int(m[1]):problems.append('Trace lost events: '+name)
    if not d.get('trace',{}).get('stats') or d.get('trace',{}).get('observer_errors') or not d.get('trace',{}).get('own_instance_removed'):problems.append('Trace collection/cleanup incomplete')
    if gate.get('samples') or gate.get('model_forward_calls') or gate.get('vision_forward_calls') or gate.get('host_calls') or gate.get('logical_calls'):problems.append('Unexpected model/request work')
    if gate.get('fpga_transactions')!=2 or len(gate.get('kernel_transitions',[]))!=1 or not gate['kernel_transitions'][0].get('full_output_exact'):problems.append('Expected two complete minimal proofs absent')
    if not gate.get('safe_buffers_released') or gate.get('original_buffer_release_count')!=7 or gate.get('unsafe_buffers_retained') or not gate.get('stable_overlay_reloaded'):problems.append('Original owner cleanup/stable restore incomplete')
    if gate.get('errors')!=['RuntimeError: Global CMA API counter changed; ownership unknown, stop diagnostic']:problems.append('Failure differs from unchanged original CMA guard')
    d['problems']=problems
    if not problems:d['status']='PASS_M441_CMA_DRIVER_ATTRIBUTION_ONLY13'
    return d
