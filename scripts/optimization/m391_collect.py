"""Strict original saved bytes, CPU scope and independently derived statistics."""
import base64
import hashlib
import json
import re
from m351_workflow import ROOT,BASE,sha,atomic,encoded,sync
PKG=BASE/'candidates/M391-silu-real-input-component-01'

def statistics(rows):
    groups=[]
    if len(rows)!=48:raise ValueError('Incomplete balanced batches')
    for r in range(6):
        rr=rows[r*8:(r+1)*8]
        for i,x in enumerate(rr):
            if x['round']!=r or x['position']!=i or x['variant']!='ABBABAAB'[i] or x['calls']!=6 or type(x['total_ns']) is not int or x['total_ns']<=0 or x['ns_per_call']!=x['total_ns']/6:raise ValueError('Batch identity/timing differs')
        for name,part in [('ABBA',rr[:4]),('BAAB',rr[4:])]:
            a=[x['ns_per_call'] for x in part if x['variant']=='A'];b=[x['ns_per_call'] for x in part if x['variant']=='B'];am=sum(a)/2;bm=sum(b)/2
            groups.append(dict(round=r,order=name,A_ns=am,B_ns=bm,gain_ns=am-bm,gain_pct=(am-bm)/am*100,A_range_ns=max(a)-min(a),B_range_ns=max(b)-min(b)))
    a=[x['ns_per_call'] for x in rows if x['variant']=='A'];b=[x['ns_per_call'] for x in rows if x['variant']=='B']
    gain=min(x['gain_ns'] for x in groups);noise=max(max(x['A_range_ns'],x['B_range_ns']) for x in groups)
    criteria=dict(all_twelve_order_groups_positive=gain>0,min_order_gain_exceeds_largest_group_range=gain>noise,slowest_B_faster_than_fastest_A=max(b)<min(a),min_gain_ns=gain,max_group_range_ns=noise,min_A_minus_max_B_ns=min(a)-max(b))
    passed=all(criteria[k] for k in ('all_twelve_order_groups_positive','min_order_gain_exceeds_largest_group_range','slowest_B_faster_than_fastest_A'))
    return groups,criteria,passed

def decode(text):
    hs=re.findall(r'M391_RESULT_SHA256=([0-9a-f]{64})',text);cs=re.findall(r'M391_SAVED_GATE_RC=(\d+)',text)
    ps=re.findall(r'M391_RESULT_CHUNK=(\d+)/(\d+):([A-Za-z0-9+/=]+)',text)
    if len(hs)!=1 or len(cs)!=1 or not ps or len(ps)!=int(ps[0][1]):raise ValueError('Incomplete/duplicate raw')
    pieces=[]
    for i,(index,total,b64) in enumerate(ps):
        if int(index)!=i or int(total)!=len(ps):raise ValueError('Sequence differs')
        p=base64.b64decode(b64,validate=True)
        if not 0<len(p)<=1800:raise ValueError('Chunk bound differs')
        pieces.append(p)
    raw=b''.join(pieces);d=hashlib.sha256(raw).hexdigest()
    if d!=hs[0]:raise ValueError('Original SHA differs')
    r=json.loads(raw)
    if r['gate_level']!='CPU-only-real159-SiLU-workspace' or r['build_id']!='0x4D333537' or r['manifest_sha256']!=sha(PKG/'PACKAGE_MANIFEST.json'):raise ValueError('Scope identity differs')
    if type(r['gate_return_code']) is not int or r['gate_return_code']!=int(cs[0]) or int(cs[0]) not in (0,1):raise ValueError('Original code differs')
    for k in ('overlay_loaded','model_forward_calls','fpga_transactions','production_changed','full_request_performance_pass','formal_promotion_allowed','memory_capacity_proven','default_enabled','cache_eviction'):
        if r[k]:raise ValueError('Overclaimed CPU scope '+k)
    done=re.findall(r'M391_DONE gate_rc=(\d+) export_rc=(\d+)',text)
    if done and (len(done)!=1 or done[0]!=(cs[0],'0')):raise ValueError('Code/export differs')
    if r['status']=='PASS_M391_CPU_MEASUREMENTS':
        if r['gate_return_code'] or r['errors'] or not r['numerical_pass'] or not r['workspace_object_and_buffer_released']:raise ValueError('Incomplete numeric/lifetime PASS')
        e=json.loads((PKG/'INPUT_IDENTITY.json').read_text(encoding='utf-8'))
        if r['capture_raw_sha256']!=e['capture_raw_sha256'] or r['input_tensors']!={n:e['fixtures'][n]['tensor'] for n in ('gate','up')}:raise ValueError('Real input differs')
        if r['warmup_calls_each']!=4 or r['planned_rounds']!=6 or r['calls_per_batch']!=6 or r['planned_order']!='ABBABAAB' or r['workspace_bytes']!=6187008:raise ValueError('Geometry/design differs')
        if r['elapsed_s']>60 or r['environment']['euid']!=0 or r['environment']['uname'][0]!='Linux':raise ValueError('Platform/budget differs')
        if not re.fullmatch('[0-9a-f]{64}',r['output_sha256']):raise ValueError('Output digest differs')
        for n,identity in r['input_file_identities'].items():
            if n not in ('gate','up') or len(identity)!=7 or identity[2]!=e['fixtures'][n]['file_bytes']:raise ValueError('File identity missing')
        if set(r['input_file_identities'])!={'gate','up'}:raise ValueError('Missing input identity')
        g,c,p=statistics(r['batches'])
        if r['groups']!=g or r['performance_criteria']!=c or r['component_performance_pass']!=p:raise ValueError('Derived statistics differ')
        if len(r['memory'])!=9 or r['workspace_create_ns']<0 or r['workspace_close_ns']<0:raise ValueError('Lifetime overhead/memory missing')
    elif r['status']!='FAIL_M391_CPU_COMPONENT' or r['gate_return_code']!=1 or not r['errors']:raise ValueError('Unknown/empty failure')
    return d,raw,r

def collect(path):
    d,raw,r=decode(path.read_text(encoding='utf-8-sig'));p=BASE/'runs/M391-silu-component-board-01/BOARD_RESULT.json'
    atomic(p,raw,immutable=True)
    sync('latest_m391_silu_board',dict(status=r['status'],sha256=d,result=p.relative_to(ROOT).as_posix(),numerical_pass=r['numerical_pass'],component_performance_pass=r['component_performance_pass']),
         f'## M391 板端真实gate/up CPU组件结果（2026-10-04）\n\n原rc{r["gate_return_code"]}，{r["status"]}，原SHA {d}。板端Python/NumPy真实159×9728输入前后逐位/文件身份，六组ABBA+BAAB，每批6次；无Overlay/模型/FPGA。建立/关闭、lease/原astype边界显式；仅组件测量。下一步仅已有原字节离线裁决，未验证完整请求收益，禁止自动接入服务。')
    print(json.dumps(dict(status=r['status'],sha256=d,numerical_pass=r['numerical_pass'],component_performance_pass=r['component_performance_pass'],errors=r['errors'])))

if __name__=='__main__':
    import sys
    collect(ROOT/sys.argv[1])
