"""Small read-only process/boot/log observer. No restart, kill or checkpoint."""
import ctypes
import os
import re
import time
from pathlib import Path
from m441_continue_offline import opened, exit_code, kernel

kernel.GetTickCount64.argtypes=[]
kernel.GetTickCount64.restype=ctypes.c_ulonglong

def boot():
    now=time.time(); uptime=kernel.GetTickCount64()/1000
    return dict(captured_epoch=now,uptime_s=uptime,boot_epoch_estimate=now-uptime,
                boot_time_kind='GetTickCount64 estimate; 10s conservative tolerance')

def process(pid, expected=None):
    try:
        handle,born=opened(pid)
        if handle is None:return dict(pid=pid,status='NOT_FOUND',creation_FILETIME=None)
        try:code=exit_code(handle)
        finally:kernel.CloseHandle(handle)
        return dict(pid=pid,creation_FILETIME=born,exit_code=code,
                    status='PID_REUSED' if expected is not None and born!=expected else ('ALIVE' if code==259 else 'EXITED'))
    except OSError as e:
        return dict(pid=pid,status='UNPROVEN_QUERY_ERROR',error=str(e))

def classify(start, current, state):
    if abs(current['boot_epoch_estimate']-start['boot_epoch_estimate'])>10:
        return 'INTERRUPTED_HOST_BOOT_CHANGED'
    if state['status']=='ALIVE':return 'RUNNING_IDENTITY_CONFIRMED'
    return {'NOT_FOUND':'INTERRUPTED_PROCESS_MISSING','PID_REUSED':'INTERRUPTED_PID_REUSED',
            'EXITED':'PROCESS_RETURNED','UNPROVEN_QUERY_ERROR':'UNPROVEN_PROCESS_IDENTITY'}[state['status']]

def log_snapshot(path):
    path=Path(path)
    if not path.exists():return dict(path=str(path),exists=False)
    with path.open('rb') as f:
        f.seek(max(0,path.stat().st_size-131072));raw=f.read()
    text=raw.decode('utf-8-sig',errors='backslashreplace')
    totals=re.findall(r'^M441_PROGRESS [^\r\n]+',text,re.M)
    ports=re.findall(r'^M441_PORT_PROGRESS [^\r\n]+',text,re.M)
    hb=re.findall(r'^M441(?:MAX)?_HEARTBEAT [^\r\n]+',text,re.M)
    fatal=re.findall(r'^.*(?:Fatal:|ERROR:|M441.*TIMEOUT).*$',text,re.M)
    def fields(line):return {k:int(v) for k,v in re.findall(r'(\w+)=(\d+)',line)}
    last=fields(totals[-1]) if totals else (fields(hb[-1]) if hb else {})
    pp=[fields(s) for s in ports if fields(s).get('cycle')==last.get('cycle')]
    return dict(path=str(path),exists=True,bytes=path.stat().st_size,mtime_epoch=path.stat().st_mtime,
                last=last,last_ports=pp,failure_tail=fatal[-6:],exact_native_log_preserved=True)

def selftest():
    s=dict(boot_epoch_estimate=100)
    cases=[(s,dict(status='ALIVE'),'RUNNING_IDENTITY_CONFIRMED'),
           (dict(boot_epoch_estimate=200),dict(status='ALIVE'),'INTERRUPTED_HOST_BOOT_CHANGED'),
           (s,dict(status='NOT_FOUND'),'INTERRUPTED_PROCESS_MISSING'),
           (s,dict(status='PID_REUSED'),'INTERRUPTED_PID_REUSED'),
           (s,dict(status='EXITED'),'PROCESS_RETURNED'),
           (s,dict(status='UNPROVEN_QUERY_ERROR'),'UNPROVEN_PROCESS_IDENTITY')]
    for current,p,expected in cases:assert classify(s,current,p)==expected
    actual=process(os.getpid());assert actual['status']=='ALIVE'
    assert process(os.getpid(),actual['creation_FILETIME']+1)['status']=='PID_REUSED'
    assert classify(boot(),boot(),actual)=='RUNNING_IDENTITY_CONFIRMED'
    return dict(fake_state_checks=len(cases),real_self_process_checks=3,
                no_simulator_started=True,no_process_kill=True)
