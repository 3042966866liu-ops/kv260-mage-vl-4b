"""Read-boundary process I/O counters; no changed arithmetic or file API.

Counter collection lies OUTSIDE the actual weight_file_read span, but remains
inside outer Decode timing. Process counters may include concurrent threads;
they are not per-file physical-sector counters. No mincore inference here.
"""
from contextlib import contextmanager
from pathlib import Path
from decode_trace import DecodeTrace


def process_snapshot():
    import resource
    values={k:int(v) for k,v in (line.split(':') for line in Path('/proc/self/io').read_text().splitlines())}
    usage=resource.getrusage(resource.RUSAGE_SELF)
    return dict(**values,minflt=usage.ru_minflt,majflt=usage.ru_majflt)


class DecodeIOTrace(DecodeTrace):
    def __init__(self,*args,snapshot=process_snapshot,**kwargs):
        super().__init__(*args,**kwargs);self.snapshot=snapshot

    @contextmanager
    def span(self,name,**metadata):
        if name!='weight_file_read':
            with super().span(name,**metadata) as event:yield event
            return
        before=self.snapshot()
        with super().span(name,**metadata) as event:
            yield event
        after=self.snapshot()
        delta={k:after[k]-before[k] for k in before}
        if any(v<0 for v in delta.values()):raise RuntimeError('I/O counter moved backwards')
        event['metadata']['process_io_delta']=delta
        event['metadata']['io_scope']='Process counters bracket only this read; counter instrumentation and concurrent-thread caveats apply'
