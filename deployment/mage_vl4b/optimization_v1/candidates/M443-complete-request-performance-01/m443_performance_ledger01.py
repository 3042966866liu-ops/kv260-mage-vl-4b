"""Independent M441/M443 released configuration ledger; never reset resident counters."""
import hashlib
import json
import os
from pathlib import Path
import platform
import time
import traceback
from m441_cma_ledger15 import StagePolicy as OriginalLedger
from m441_cma_ledger15 import validate as validate_m441
from m443_configuration01 import BIT as BIT_SHA, SHELL as SHELL_SHA, validate_record
from m443_cma_contract01 import KERNEL
from m443_performance_trace01 import Trace

M441_BIT='73350f615a5bc98d1d8aa2b5c69c4d6fd399aa1ef651f37411cbed21c0daed2e'
BITS={M441_BIT,BIT_SHA}


def validate(record,application_sha,manifest_sha):
    if record['bit_sha256']==M441_BIT:
        assert record['variant']=='A'
        return validate_m441(record)
    assert record['bit_sha256']==BIT_SHA and record['variant']=='B'
    validate_record(record,application_sha,manifest_sha)
    return {'reserved:alloc_pages_success':1904}


def prerequisite(here,manifest_sha):
    here=Path(here);p=here/'M443_BUILD_CONFIGURATION_PROOF.json';proof=json.loads(p.read_bytes())
    application_sha=hashlib.sha256((here/'CONFIGURATION_APPLICATION.json').read_bytes()).hexdigest()
    assert proof['status']=='PASS_M443_BUILDID' and proof['gate_return_code']==0
    validate_record(proof['configuration_record'],application_sha,manifest_sha)
    assert proof['configuration_application_accepted'] and not proof['unknown_configuration_ownership']
    assert proof['safe_buffers_released'] and not proof['unsafe_dma_buffers_retained'] and proof['stable_restored']
    assert platform.release()==KERNEL and os.sysconf('SC_PAGE_SIZE')==4096
    return dict(sha256=hashlib.sha256(p.read_bytes()).hexdigest(),application_sha256=application_sha,
                manifest_sha256=manifest_sha,actual_new_bit_application=True,configuration_credits_granted=0)


class StagePolicy(OriginalLedger):
    def __init__(self,result,runtime,base,*,evidence,application_sha,manifest_sha,**kwargs):
        super().__init__(result,runtime,base,evidence=evidence,**kwargs)
        self.application_sha,self.manifest_sha=application_sha,manifest_sha
        self.configuration_overlay_history=[]
        self.result['configuration_CMA_contract']='M44301: immutable original resident baseline minus exact same-PID/PFN released configuration pages only; M441 original validator and independent M443 application'

    def prepare_programming(self,path,index,variant):
        assert self.pending is None and self.sealed and not self.active and self.completed
        assert not self.thread or not self.thread.is_alive(),'Request observer still active'
        self.capture('before-programming-ledger:'+str(index),True)
        p=Path(path);raw=p.read_bytes();sha=hashlib.sha256(raw).hexdigest()
        assert variant in ('A','B') and sha==(M441_BIT if variant=='A' else BIT_SHA)
        assert len(raw)==7797914 and platform.release()==KERNEL and os.sysconf('SC_PAGE_SIZE')==4096
        trace_dir=self.evidence/('cma_program_'+str(index));trace_dir.mkdir(exist_ok=False)
        t=Trace(trace_dir)
        try:t.prepare()
        except BaseException:
            if t.created:t.started=time.monotonic();t.stop()
            raise
        self.pending=dict(trace=t,path=str(p),index=index,variant=variant,bit_sha256=sha,bit_bytes=len(raw))

    def commit(self,record):
        if record['bit_sha256']==BIT_SHA:
            record.update(application_sha256=self.application_sha,manifest_sha256=self.manifest_sha,
                          shell_closure_sha256=SHELL_SHA,observation_kind='same-process-kernel-CMA-trace',
                          configuration_credits_granted=0,overlay_returned=True)
        credits=validate(record,self.application_sha,self.manifest_sha)
        assert {k:v-self.credits.get(k,0) for k,v in record['before'].items()}==self.initial_counts,'Unknown allocation before configuration'
        proposed={k:self.credits.get(k,0)+credits.get(k,0) for k in record['after']}
        assert {k:v-proposed[k] for k,v in record['after'].items()}==self.initial_counts,'Unknown allocation after configuration'
        for k,v in credits.items():self.credits[k]=self.credits.get(k,0)+v
        assert self.accounted_counts()==self.initial_counts,'Unknown allocation after configuration'
        record['verified_released_configuration_pages']=credits
        record['cumulative_verified_credits']=dict(self.credits)
        record['original_baseline_unchanged']=dict(self.initial_counts)
        self.result['configuration_CMA_ledger'].append(record)

    def wrap_overlay(self,original):
        def load(path,*args,**kwargs):
            if not self.sealed:return original(path,*args,**kwargs)
            q=self.pending
            assert q is not None and str(path)==q['path'],'Unprepared programming refused'
            assert not args and kwargs=={'download':True},'Exact programming call required'
            t=q['trace'];record={k:v for k,v in q.items() if k not in ('trace','path')}
            record.update(kernel=platform.release(),page_size=os.sysconf('SC_PAGE_SIZE'),pages=1904,pid=os.getpid(),before=self.raw_counters())
            t.started=time.monotonic()
            try:
                t.start();overlay=original(path,*args,**kwargs)
                # Retain an actual returned Overlay even if the subsequent proof is unknown.
                self.configuration_overlay_history.append(overlay)
                record['trace']=t.stop();record['after']=self.raw_counters();self.commit(record)
                return overlay
            except BaseException:
                if not t.details.get('own_instance_removed'):record['trace']=t.stop()
                record['after']=self.raw_counters();record['error']=traceback.format_exc()
                self.result.setdefault('configuration_CMA_rejected',[]).append(record)
                raise
            finally:self.pending=None
        return load
