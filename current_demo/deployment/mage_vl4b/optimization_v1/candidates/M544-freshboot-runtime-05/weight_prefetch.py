"""One next-family ordinary-RAM window, no device API on the I/O worker.

The synchronous arm executes the original copy function under its original
timer.  The candidate reuses four bounded bytearrays and preopened verified
regular files. Only the caller copies to and synchronizes existing DMA owners.
"""
import hashlib, inspect, os, stat, textwrap, threading, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import numpy as np
from M455_weight_stage_profile523381 import WeightStageProfile


def identity(s):
    return (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_nlink)


class WindowReader:
    def __init__(self, groups, maximum, free_bytes=None):
        if not groups or len(groups)>256 or not 0<maximum<=8<<20:
            raise ValueError('Bounded nonempty four-shard schedule required')
        self.groups=groups;self.maximum=maximum;self.owner=threading.get_ident()
        self.pool=None;self.future=None;self.pending=None;self.closed=False
        self.files={};self.slots=[]
        try:
            names={str(w['path']) for group in groups for w in group}
            if len(names)>192:raise ValueError('Too many preopened weights')
            for group in groups:
                if len(group)!=4:raise ValueError('Exactly four shards per family')
                for w in group:
                    if type(w['offset']) is not int or type(w['effective_bytes']) is not int or not 0<=w['offset'] or not 0<w['effective_bytes']<=maximum:
                        raise ValueError('Invalid source window')
            if free_bytes is not None and free_bytes()<4*maximum+(64<<20):
                raise MemoryError('Ordinary RAM plus 64MiB reserve unavailable')
            for name in sorted(names):
                p=Path(name);before=p.lstat()
                if not stat.S_ISREG(before.st_mode) or before.st_nlink!=1 or p.is_symlink():
                    raise ValueError('Independent plain source file required')
                fd=os.open(name,os.O_RDONLY|getattr(os,'O_NOFOLLOW',0))
                try:
                    if identity(os.fstat(fd))!=identity(before):raise ValueError('Source changed during open')
                except BaseException:os.close(fd);raise
                self.files[name]=(fd,identity(before))
            for group in groups:
                for w in group:
                    if w['offset']+w['effective_bytes']>self.files[str(w['path'])][1][2]:
                        raise ValueError('Source window exceeds original file')
            self.slots=[bytearray(maximum) for _ in range(4)]
        except BaseException:
            for fd,_ in self.files.values():os.close(fd)
            self.files.clear();raise

    def _check(self,name):
        fd,expected=self.files[name]
        if identity(os.fstat(fd))!=expected or identity(Path(name).lstat())!=expected:
            raise RuntimeError('Preopened source identity changed')
        return fd

    def _read(self,index):
        began=time.perf_counter_ns();rows=[]
        for slot,w in zip(self.slots,self.groups[index]):
            name=str(w['path']);fd=self._check(name);size=w['effective_bytes'];cursor=0
            os.lseek(fd,w['offset'],os.SEEK_SET)
            view=memoryview(slot);started=time.perf_counter_ns()
            try:
                while cursor<size:
                    n=os.readv(fd,[view[cursor:size]])
                    if n<=0:raise RuntimeError('Short prefetch weight read')
                    cursor+=n
            finally:view.release()
            elapsed=time.perf_counter_ns()-started;self._check(name)
            rows.append(dict(path=name,offset=w['offset'],effective_bytes=size,read_ns=elapsed))
        return dict(index=index,rows=rows,worker_total_ns=time.perf_counter_ns()-began)

    def start(self,index):
        if threading.get_ident()!=self.owner or self.closed or self.future is not None:
            raise RuntimeError('Single pending window / main-thread submission required')
        if self.pool is None:self.pool=ThreadPoolExecutor(max_workers=1,thread_name_prefix='m455-weight-read')
        self.pending=index;self.future=self.pool.submit(self._read,index)

    def take(self,index):
        if threading.get_ident()!=self.owner or self.pending!=index or self.future is None:
            raise RuntimeError('Unexpected next-family prefetch')
        began=time.perf_counter_ns();result=self.future.result(timeout=30)
        self.future=None;self.pending=None
        return result,time.perf_counter_ns()-began

    def drain(self):
        if self.future is not None:
            try:self.future.result(timeout=30)
            finally:
                if self.future.done():
                    self.future=None;self.pending=None
                    if self.pool is not None:self.pool.shutdown(wait=True);self.pool=None
        if self.pool is not None:self.pool.shutdown(wait=True);self.pool=None

    def close(self):
        if self.closed:return
        self.drain()
        for name,(fd,_) in self.files.items():self._check(name);os.close(fd)
        self.files.clear();self.slots.clear();self.closed=True


class WeightPrefetch:
    def __init__(self,base,runtime,windows,expected_source_sha256):
        if not windows or len(windows)%4:raise ValueError('Complete saved stage sequence required')
        self.groups=[[dict(path=str(w['path']),offset=w['offset'],effective_bytes=w['effective_bytes']) for w in windows[i:i+4]] for i in range(0,len(windows),4)]
        self.runtime=runtime;self.base=base;self.owner=threading.get_ident();self.active=False;self.original=None
        self.maximum=int(runtime.maximum_weight_window_bytes)
        if len(runtime.staged_buffers)!=4 or any(int(b.nbytes)!=self.maximum for b in runtime.staged_buffers):
            raise ValueError('Original four equal DMA owners required')
        self.buffers=tuple(runtime.staged_buffers);self.ids=tuple(map(id,self.buffers))
        self.sync_profile=WeightStageProfile(expected_source_sha256)
        self.sync_profile.install(base)
        self.namespace=self.sync_profile.namespace;self.original=self.namespace['copy_window_to_buffer']
        def free():
            if Path('/proc/meminfo').exists():
                return int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024
            return 1<<40
        try:self.reader=WindowReader(self.groups,self.maximum,free)
        except BaseException:self.sync_profile.restore();raise
        self.wrapper=self.copy;self.namespace['copy_window_to_buffer']=self.wrapper

    def begin(self,variant):
        if self.active or variant not in ('A','B') or self.reader.future is not None:raise RuntimeError('Unclosed prefetch request')
        self.variant=variant;self.active=True;self.index=0;self.shard=0;self.rows=[];self.wait_ns=0;self.read_groups=[]
        self.current=None;self.current_wait=0
        if variant=='A':self.sync_profile.begin()
        else:self.reader.start(0)

    def copy(self,path,offset,size,buffer):
        if not self.active:return self.original(path,offset,size,buffer)
        if threading.get_ident()!=self.owner or tuple(map(id,self.runtime.staged_buffers))!=self.ids:
            raise RuntimeError('DMA copying must stay on original caller and owners')
        if self.index>=len(self.groups):raise RuntimeError('Unexpected extra staging group')
        w=self.groups[self.index][self.shard]
        if (str(path),offset,size)!=(w['path'],w['offset'],w['effective_bytes']) or buffer is not self.buffers[self.shard]:
            raise RuntimeError('Actual staging differs from frozen complete sequence')
        if self.variant=='A':result=self.original(path,offset,size,buffer)
        else:
            if self.shard==0:
                self.current,self.current_wait=self.reader.take(self.index)
                self.wait_ns+=self.current_wait;self.read_groups.append(self.current)
            row=dict(self.current['rows'][self.shard]);started=time.perf_counter_ns()
            copy_started=time.perf_counter_ns()
            buffer[:size]=np.frombuffer(self.reader.slots[self.shard],dtype=np.uint8,count=size)
            row['copy_ns']=time.perf_counter_ns()-copy_started
            sync_started=time.perf_counter_ns();buffer.sync_to_device();row['sync_ns']=time.perf_counter_ns()-sync_started
            row.update(buffer_capacity_bytes=int(buffer.nbytes),ok=True,read_calls=1,copy_calls=1,sync_calls=1,
                       total_ns=time.perf_counter_ns()-started,open_seek_close_and_observer_ns=0)
            self.rows.append(row);result=None
        self.shard+=1
        if self.shard==4:
            self.shard=0;self.index+=1;self.current=None
            if self.variant=='B' and self.index<len(self.groups):self.reader.start(self.index)
        return result

    def end(self):
        if not self.active or self.shard or self.index!=len(self.groups):raise RuntimeError('Incomplete source schedule')
        self.reader.drain();self.active=False
        if self.variant=='A':report=self.sync_profile.end()
        else:
            ns=('read_ns','copy_ns','sync_ns','total_ns','open_seek_close_and_observer_ns')
            summary={k[:-3]+'_s':sum(r[k] for r in self.rows)/1e9 for k in ns}
            summary.update(windows=len(self.rows),effective_bytes=sum(r['effective_bytes'] for r in self.rows),
                           whole_buffer_sync_capacity_bytes=sum(r['buffer_capacity_bytes'] for r in self.rows))
            report=dict(summary=summary,windows=self.rows)
        report['prefetch']=dict(variant=self.variant,depth=1,ordinary_RAM_bytes=4*self.maximum,
            preopened_files=len(self.reader.files),source_groups=self.index,worker_groups=len(self.read_groups),
            caller_future_wait_s=self.wait_ns/1e9,worker_group_s=sum(r['worker_total_ns'] for r in self.read_groups)/1e9,
            no_worker_device_access=True,original_sync_capacity=True,original_four_DMA_owners=True,
            read_and_wait_overlap_compute=True,worker_drained=True)
        return report

    def abort(self):
        self.reader.drain()
        self.active=False;self.sync_profile.active=False;self.sync_profile.current=None

    def restore(self):
        if self.active:raise RuntimeError('Active source worker must close first')
        self.reader.close()
        if self.original is not None:
            if self.namespace['copy_window_to_buffer'] is not self.wrapper:raise RuntimeError('Source hook changed')
            self.namespace['copy_window_to_buffer']=self.original
            self.sync_profile.restore();self.original=None
