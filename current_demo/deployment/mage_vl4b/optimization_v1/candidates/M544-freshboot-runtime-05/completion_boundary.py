"""Read-only bounded completion observation; unchanged strict M455 predicate."""
import time

def observe(first,reader,predicate,*,timeout_s=2.0,max_reads=2001,clock=time.monotonic,sleep=time.sleep):
    assert 0<timeout_s<=2 and 1<=max_reads<=2001
    start=clock();s=first;n=0
    while True:
        if any(s.get(k)!='' for k in ('kernel_read_error','return_read_error','dma_read_error')):
            raise RuntimeError('Completion MMIO read error: '+repr(s))
        if s.get('mm2s_error') is not False or s.get('s2mm_error') is not False:
            raise RuntimeError('Completion DMA error: '+repr(s))
        if any(type(s.get(k))is not int or s[k]<0 for k in ('ap_ctrl','ap_return','mm2s_dmasr','s2mm_dmasr')):
            raise RuntimeError('Completion field unavailable: '+repr(s))
        if (s['mm2s_dmasr']|s['s2mm_dmasr'])&0x770:
            raise RuntimeError('Completion DMA status error: '+repr(s))
        if s['ap_return']!=0x4D343535:
            raise RuntimeError('Completion wrong Build-ID: '+repr(s))
        if predicate(s):return s,dict(additional_reads=n,elapsed_s=clock()-start,first=first,final=s)
        if n>=max_reads or clock()-start>=timeout_s:
            raise TimeoutError('Strict completion remained unproved: '+repr(s))
        sleep(.001);s=reader();n+=1

def install(guard,result):
    from M455_adaptive_guard52301 import completed
    original=guard.after
    def after(snapshot):
        if completed(snapshot):return original(snapshot)
        row=dict(first=snapshot,current=dict(guard.current or {}),completed=False)
        result.setdefault('language_completion_boundaries',[]).append(row)
        try:
            final,detail=observe(snapshot,guard.snapshot_reader,completed)
            row.update(detail,completed=True)
            return original(final)
        except BaseException as error:
            row['error']=repr(error);raise
    guard.after=after

def tests():
    good=dict(ap_ctrl=4,ap_return=0x4D343535,mm2s_dmasr=2,s2mm_dmasr=2,mm2s_error=False,s2mm_error=False,kernel_read_error='',return_read_error='',dma_read_error='')
    predicate=lambda s:s['ap_ctrl']&4 and s['mm2s_dmasr']&3 and s['s2mm_dmasr']&3
    pending=dict(good,ap_ctrl=0);ticks=[0.0]
    clock=lambda:ticks[0]
    def sleep(dt):ticks[0]+=dt
    assert observe(good,lambda:None,predicate)[1]['additional_reads']==0
    assert observe(pending,lambda:good,predicate,clock=clock,sleep=sleep)[1]['additional_reads']==1
    for bad in (dict(good,dma_read_error='read failure'),dict(good,mm2s_error=True),dict(good,mm2s_dmasr=0x12),dict(good,ap_return=0),dict(good,ap_ctrl=None)):
        try:observe(bad,lambda:good,predicate)
        except RuntimeError:pass
        else:raise AssertionError('Invalid completion accepted')
    ticks[0]=0
    try:observe(pending,lambda:pending,predicate,timeout_s=.002,clock=clock,sleep=sleep)
    except TimeoutError:pass
    else:raise AssertionError('Uncompleted transaction accepted')
    return dict(passed=8,strict_predicate_unchanged=True,new_submissions=0)
