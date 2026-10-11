"""One first-switch diagnostic. Never relax the original CMA admission policy."""
import hashlib
import json
import os
from pathlib import Path
import re
import time
import traceback

TRACE_NAME='m443_performance_cma01'
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

    def prepare(self):
        self.path.mkdir(exist_ok=False);self.created=True
        self.put('tracing_on','0');self.put('buffer_size_kb','128')
        self.put('options/stacktrace','1')
        self.details['event_formats']={n:(self.path/f'events/cma/{n}/format').read_text() for n in EVENTS}

    def start(self):
        assert self.created
        for n in EVENTS:
            self.put(f'events/cma/{n}/enable','1');self.enabled.append(n)
        self.put('tracing_on','1');self.put('trace_marker','M443_PERFORMANCE_CONFIGURATION01_BEGIN')

    def stop(self):
        errors=[]
        try:
            self.put('trace_marker','M443_PERFORMANCE_CONFIGURATION01_END');self.put('tracing_on','0')
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
