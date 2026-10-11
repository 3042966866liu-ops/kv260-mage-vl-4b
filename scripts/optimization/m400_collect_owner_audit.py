"""Collect the saved owner/source audit; never contact the board."""
import base64
import hashlib
import json
import re
from m351_workflow import ROOT,HERE,BASE,sha,atomic,encoded,sync


def main():
    log=ROOT/'tmp/m400/owner_audit_run.log'
    text=log.read_text(encoding='utf-8-sig')
    hashes=re.findall(r'(?m)^M400_OWNER_SHA256=([0-9a-f]{64})\s*$',text)
    chunks=re.findall(r'(?m)^M400_OWNER_CHUNK=(\d+)/(\d+):([A-Za-z0-9+/=]+)\s*$',text)
    if len(hashes)!=1 or not chunks or len(chunks)!=int(chunks[0][1]) or '__M400_OWNER_RUN_RC_0__' not in text:
        raise RuntimeError('Incomplete/duplicate audit export or original return code')
    data=[]
    for i,(n,count,b64) in enumerate(chunks):
        p=base64.b64decode(b64,validate=True)
        if int(n)!=i or int(count)!=len(chunks) or not 0<len(p)<=900:
            raise RuntimeError('Audit chunk order/length differs')
        data.append(p)
    raw=b''.join(data);digest=hashlib.sha256(raw).hexdigest()
    if digest!=hashes[0]:raise RuntimeError('Audit raw SHA differs')
    r=json.loads(raw)
    pkg=BASE/'candidates/M400-owner-audit-01'
    if r['status']!='PASS_READONLY_RETAINED_OWNER_AND_SOURCE_AUDIT' or r['gate_return_code'] or r['manifest_sha256']!=sha(pkg/'PACKAGE_MANIFEST.json'):
        raise RuntimeError('Unexpected audit identity/status')
    if not r['owner']['state'].startswith(('T','t')) or r['owner']['uid'].split()[0]!='0':
        raise RuntimeError('Root retained owner no longer suspended')
    for k in ('owner_release_authorized','process_recovered','stable_overlay_restored','new_overlay_loads',
              'new_DMA_allocations','model_calls','board_signals_sent','live_python_scope_state_observed'):
        if r[k]:raise RuntimeError('Read-only audit exceeded scope')
    s=r['source_reproduction']
    if not s['new_guard']['deterministic_source_equal'] or not s['same_interpreter_AST_equal']:
        raise RuntimeError('Source compatibility/math unresolved')
    out=BASE/'runs/M400-owner-audit-board-01/BOARD_RESULT.json'
    atomic(out,raw,immutable=True);atomic(out.parent/'UART.log',log.read_bytes(),immutable=True)
    for name in ('owner_pause_01.log','recovery_sudo_01.log','owner_audit_sudo_Upload.log','owner_audit_sudo_Run.log'):
        atomic(out.parent/name,(ROOT/'tmp/m400'/name).read_bytes(),immutable=True)
    atomic(out.parent/'SOURCE_DIFF.patch',s['exact_diff'].encode('utf-8'),immutable=True)
    sync('latest_m400_owner_audit_board',
         dict(status=r['status'],result=out.relative_to(ROOT).as_posix(),sha256=digest,
              process_recovered=False,stable_overlay_restored=False,owner_release_authorized=False),
         f'## M400 原owner及源码只读调查（2026-10-04）\n\nSHA `{digest}`；原root Python PID{r["owner"]["pid"]}挂起、{r["owner"]["threads"]}线程，七DMA未释放，稳定Overlay未恢复。新进程执行冻结实际derive，原text_equal={s["old_text_equal"]}/同解释器AST_equal={s["same_interpreter_AST_equal"]}，精确diff保存，确定性新guard在目标Python通过。只读proc及源码，未观察原Python对象状态、未附加调试器/发信号/新Overlay或DMA；不能据此释放owner。下一步受控owner回收入口方案，修正版单层包必须先于Overlay检查；原失败及性能结论保持。')
    print(json.dumps(dict(status=r['status'],raw_sha256=digest,owner=r['owner'],debuggers=r['debugger_paths'],
                          old_text_equal=s['old_text_equal'],AST_equal=s['same_interpreter_AST_equal'],diff=s['exact_diff']),ensure_ascii=False))


if __name__=='__main__':main()
