"""Recover saved PS reference bytes only; never execute a board gate."""
import base64
import hashlib
import json
from pathlib import Path
import re
import sys
import m351_workflow as w
PKG=w.BASE/'candidates/M367-PS-visual-reference-02'


def decode(log):
    hashes=re.findall(r'(?m)^M367_RESULT_SHA256=([0-9a-f]{64})\s*$',log)
    codes=re.findall(r'(?m)^M367_SAVED_GATE_RC=([01])\s*$',log)
    chunks=re.findall(r'(?m)^M367_RESULT_CHUNK=(\d+)/(\d+):([A-Za-z0-9+/=]+)\s*$',log)
    if len(hashes)!=1 or len(codes)!=1 or not chunks or len(chunks)!=int(chunks[0][1]):raise ValueError('Incomplete/duplicate raw')
    parts=[]
    for i,(index,total,value) in enumerate(chunks):
        part=base64.b64decode(value,validate=True)
        if int(index)!=i or int(total)!=len(chunks) or not 0<len(part)<=900:raise ValueError('Order/size differs')
        parts.append(part)
    raw=b''.join(parts);digest=hashlib.sha256(raw).hexdigest();r=json.loads(raw)
    if digest!=hashes[0] or type(r['gate_return_code']) is not int or r['gate_return_code']!=int(codes[0]):raise ValueError('SHA/rc differs')
    if r['manifest_sha256']!=w.sha(PKG/'PACKAGE_MANIFEST.json') or r['build_id']!='0x4D395832' or r['gate_level']!='missing-PS-visual-reference-only':raise ValueError('Package/scope differs')
    if any(r[k] for k in ('overlay_loads','pynq_allocate_calls','fpga_transactions','language_forward_calls','performance_pass','promoted','extra_cma_budget_bytes')):raise ValueError('Wrong evidence scope')
    done=re.findall(r'M367_DONE case=PS1 gate_rc=(\d+) export_rc=(\d+)',log)
    if done and done!=[(codes[0],'0')]:raise ValueError('Gate/export rc differs')
    if r['status']=='PASS_MISSING_PS_VISUAL_REFERENCE':
        if r['gate_return_code'] or r['errors'] or r['vision_forward_calls']!=1:raise ValueError('Incomplete PASS')
        expected=json.loads((PKG/'VIDEO_EXPECTED.json').read_text(encoding='utf-8'))['baseline']['input']
        if r['video_input']!=expected or len(r['prompt_token_ids'])!=159 or r['visual_features']['shape']!=[98,2560] or r['visual_features']['dtype']!='float32' or r['visual_features']['bytes']!=1003520:raise ValueError('Reference geometry/composition differs')
        if r['frames_sha256']!='5911485955780036ac4c8990bcaa248667f2e86bd1fd6f9b0783002553b4adff':raise ValueError('Frame identity differs')
        if set(r['preprocessed'])!={'pixel_values','image_grid_thw','patch_positions','merged_visual_tokens','view_count'}:raise ValueError('Preprocess coverage differs')
        d=r['decoder']
        if d['cache_entries']!=26 or d['cache_bytes']!=66699264 or d['cache_misses']!=26 or not d['cache_within_budget']:raise ValueError('Visual cache differs')
        if not all(r[k] for k in ('boot_unchanged','cmdline_unchanged','no_PL_boundary_enforced','vision_store_maps_and_handles_closed','language_aux_maps_and_archive_closed')):raise ValueError('Identity/resource boundary differs')
        if r['sampled_memory']['stop_reason'] or r['sampled_memory']['sample_count']<=0 or r['sampled_memory']['exact_native_peak_proven']:raise ValueError('Memory evidence differs')
        if r['ps_growth_limit_bytes']!=768<<20 or r['ps_available_margin_bytes']!=64<<20:raise ValueError('PS policy differs')
        if r['platform']['euid']!=0 or r['platform']['uname'][0]!='Linux':raise ValueError('Environment differs')
    elif r['status']!='FAIL_PS_VISUAL_REFERENCE' or r['gate_return_code']!=1 or not r['errors']:raise ValueError('Invalid failure')
    return digest,raw,r


def self_test():
    def export(r):
        raw=w.encoded(r);parts=[raw[i:i+900] for i in range(0,len(raw),900)]
        return 'M367_RESULT_SHA256='+hashlib.sha256(raw).hexdigest()+'\nM367_SAVED_GATE_RC='+str(r['gate_return_code'])+'\n'+''.join(f'M367_RESULT_CHUNK={i}/{len(parts)}:'+base64.b64encode(p).decode('ascii')+'\n' for i,p in enumerate(parts))+f'M367_DONE case=PS1 gate_rc={r["gate_return_code"]} export_rc=0\n'
    fail=dict(status='FAIL_PS_VISUAL_REFERENCE',gate_return_code=1,errors=['fixture error'*400],manifest_sha256=w.sha(PKG/'PACKAGE_MANIFEST.json'),build_id='0x4D395832',gate_level='missing-PS-visual-reference-only')
    for k in ('overlay_loads','pynq_allocate_calls','fpga_transactions','language_forward_calls','performance_pass','promoted','extra_cma_budget_bytes'):fail[k]=0
    assert decode(export(fail))[2]==fail
    bads=[export(fail).replace('SAVED_GATE_RC=1','SAVED_GATE_RC=0'),export(fail).replace('RESULT_CHUNK=1/','RESULT_CHUNK=0/'),export(fail).replace('export_rc=0','export_rc=1'),export(fail)+'M367_RESULT_SHA256='+'0'*64+'\n']
    for k,v in [('fpga_transactions',1),('performance_pass',True),('build_id','0x4D333537'),('manifest_sha256','0'*64),('errors',[])]:bads.append(export(dict(fail,**{k:v})))
    for bad in bads:
        try:decode(bad)
        except (ValueError,RuntimeError):pass
        else:raise AssertionError('Invalid recovery accepted')
    return len(bads)


def collect(path):
    digest,raw,r=decode(Path(path).read_text(encoding='utf-8-sig'))
    out=w.BASE/'runs/M367-PS-reference-board-01';w.atomic(out/'BOARD_RESULT.json',raw,immutable=True)
    w.sync('latest_m367_visual_reference_board',dict(status=r['status'],sha256=digest,result=(out/'BOARD_RESULT.json').relative_to(w.ROOT).as_posix(),performance_pass=False,promoted=False),f'## M367 缺失视觉参考板端结果\n\n稳定输入身份0x4D395832；原rc{r["gate_return_code"]}，{r["status"]}。纯PS视觉参考，0Overlay/FPGA/语言forward，复用M345语言数值。原字节SHA `{digest}`，错误{json.dumps(r["errors"],ensure_ascii=False)}。只补视觉/159输入参考；不是新核视频正确性或性能PASS。下一步独立裁决并同步后才能准备视频门禁。')
    print(json.dumps(dict(status=r['status'],raw_sha256=digest,errors=r['errors'],sampled=r.get('sampled_memory'))))


if __name__=='__main__':
    if sys.argv[1:]==['selftest']:print('M367_COLLECT_SELFTEST_PASS negatives='+str(self_test()))
    else:collect(sys.argv[1])
