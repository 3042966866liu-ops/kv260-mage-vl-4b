"""Isolated family numerical pair only; never a request performance claim."""
import hashlib
import threading
import numpy as np
from m376_gate_up_workers import GateUpWorkers

COUNTERS=('logical_calls','host_calls','scale_retry_count','pipeline_retry_launches',
          'fused_nonfinite_detections','stage_bytes','pipeline_submissions','pipeline_reuse_waits')

def tensor(value):
    value=np.ascontiguousarray(value)
    if not np.isfinite(value).all():raise FloatingPointError('Nonfinite family output')
    return dict(shape=list(value.shape),dtype=str(value.dtype),bytes=value.nbytes,
                sha256=hashlib.sha256(memoryview(value).cast('B')).hexdigest())

def snapshot(runtime):
    return {k:getattr(runtime,k) for k in COUNTERS}|{'parse_calls':runtime.phase_calls['parse']}

def run_pair(runtime,policy,values):
    if values.shape!=(159,2560) or values.dtype!=np.float32:raise ValueError('Original159x2560 embedding input required')
    input_identity=tensor(values)
    outputs=(runtime.output_buffer,runtime.output_buffer_alt)
    owned_ids=[id(v) for v in outputs];result=[]
    if any(t.name.startswith(('m238-parse','m238-pack')) for t in threading.enumerate()):raise RuntimeError('Prior worker still active')
    policy.begin_sampling()
    try:
        for workers in (1,2):
            policy.capture('before-gate-up-workers:'+str(workers),True)
            before=snapshot(runtime);attempt_start=len(runtime.scale_attempts)
            if workers==1:
                answer=runtime.language_family_many(0,'gate_up',values)
                scope=dict(parse_workers=1,gate_up_calls=1,bindings_restored=True,extra_dma_allocations=0,
                           original_single_worker_dispatch=True)
            else:
                experiment=GateUpWorkers(runtime,workers=2,enabled=True)
                with experiment:answer=runtime.language_family_many(0,'gate_up',values)
                scope=experiment.report()
            policy.capture('after-gate-up-workers:'+str(workers),True)
            after=snapshot(runtime);counts={k:after[k]-before[k] for k in before}
            attempts=runtime.scale_attempts[attempt_start:]
            if (counts['logical_calls']!=5 or counts['host_calls']!=5+counts['pipeline_retry_launches'] or
                counts['scale_retry_count']!=counts['pipeline_retry_launches'] or
                counts['fused_nonfinite_detections']!=counts['pipeline_retry_launches'] or
                counts['pipeline_submissions']!=5 or counts['pipeline_reuse_waits']!=3 or
                counts['parse_calls']!=counts['host_calls'] or len(attempts)!=5):
                raise RuntimeError('Original family/retry/statistics contract differs')
            if [id(runtime.output_buffer),id(runtime.output_buffer_alt)]!=owned_ids:raise RuntimeError('Output slots changed')
            if any(t.name.startswith(('m238-parse','m238-pack')) for t in threading.enumerate()):raise RuntimeError('Worker lifecycle open')
            result.append(dict(workers=workers,input=input_identity,outputs={k:tensor(v) for k,v in sorted(answer.items())},
                               counts=counts,scale_attempts=attempts,scope=scope))
            del answer
            if tensor(values)!=input_identity:raise RuntimeError('Input changed')
        if result[0]['outputs']!=result[1]['outputs'] or result[0]['counts']!=result[1]['counts'] or result[0]['scale_attempts']!=result[1]['scale_attempts']:
            raise RuntimeError('Full gate/up outputs or retry/counts differ')
    finally:
        policy.stop_sampling()
    return dict(status='PASS_CURRENT_SINGLE_VS_TWO_WORKER_GATE_UP_FAMILY_NUMERICAL',pairs=result,
                input_contract='159 repeated frozen text embeddings; one layer0 gate_up family only',
                additional_cma_bytes=0,model_forward_calls=0,performance_pass=False)
