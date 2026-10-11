"""Strict original-byte collector derived from the proven M365 collector."""
import argparse
import json
from pathlib import Path
import m351_workflow as w
from m441_host_io08 import atomic

PKG=w.BASE/'candidates/M441-single-layer-09'
_source=(w.HERE/'m365_collect.py').read_text(encoding='utf-8')
_source=_source[:_source.index('\ndef collect(')]
_source=_source.replace('M365-staged-layer-03','M441-single-layer-09').replace('M365','M441L').replace('0x4D333537','0x4D343431').replace('0x4d333537','0x4d343431')
_namespace={'__name__':'_m441_original_collector09'}
exec(compile(_source,'<exact-derived-M365-byte-collector09>','exec'),_namespace)

def decode(log):
    digest,raw,r=_namespace['decode'](log)
    if r['status']=='PASS_M441L_SINGLE_LAYER_DIAGNOSTIC':
        if r.get('prior_board_sha256')!='0b416a17669ae1a5690a62650237ce6ced33f922017625f685401ca806e2273d':raise ValueError('Actual compare prerequisite differs')
        if r.get('source_compatibility_checked_before_overlay') is not True:raise ValueError('Source not checked before resources')
        if r.get('additional_cma_requests_allowed') is not False:raise ValueError('Allocation seal absent')
    return digest,raw,r

def collect(logpath):
    digest,raw,r=decode(logpath.read_text(encoding='utf-8-sig'))
    out=w.BASE/'runs/M441-single-layer-board-09'
    atomic(out/'BOARD_RESULT.json',raw,immutable=True)
    atomic(out/'COLLECTION.json',w.encoded(dict(raw_sha256=digest,log_path=logpath.relative_to(w.ROOT).as_posix(),log_sha256=w.sha(logpath),collector_sha256=w.sha(Path(__file__)),reexecuted=False,gate_return_code=r['gate_return_code'])),immutable=True)
    w.sync('latest_m441_single_layer_board',dict(status=r['status'],result=(out/'BOARD_RESULT.json').relative_to(w.ROOT).as_posix(),sha256=digest,build_id='0x4D343431',numerical_pass=r['numerical_pass'],performance_pass=False),f'## M441 单层板端闭合09（2026-10-09）\n\n{r["status"]}，Build0x4D343431，原rc{r["gate_return_code"]}；完整原runtime驻留，单层159重复文本embedding，五family/hidden/KV/重试逐位参考、实际提交与七缓冲释放核对。CMA固定64MiB拒绝取消但新增DMA封锁；非完整模型/视频容量或请求性能。raw SHA {digest}；下一步PASS后独立固定文本预算和数值包，FAIL仅处理本级。')
    print(json.dumps(dict(status=r['status'],sha256=digest,errors=r['errors'],exact_comparison=r.get('exact_comparison'),host_calls=r.get('host_calls'),logical_calls=r.get('logical_calls'),released=len(r['released_buffers']),unsafe=r['unsafe_buffers_retained'])))
    return r['gate_return_code']

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('log',type=Path);a=p.parse_args();raise SystemExit(collect(a.log.resolve()))
