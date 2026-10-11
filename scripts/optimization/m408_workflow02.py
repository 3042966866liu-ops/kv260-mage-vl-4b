"""M408 exact manifest-first receipts and saved-byte collector; no board commands."""
import base64
import hashlib
import json
from pathlib import Path
import re
import sys
from m351_workflow import ROOT,BASE,atomic,encoded,sha,sync

PKG = BASE/'candidates/M408-local-MLP-A8-capture-02'


def transfer(folder=ROOT/'tmp/m40802',save=True):
    manifest = json.loads((PKG/'PACKAGE_MANIFEST.json').read_bytes())
    receipts = []
    for name in ['PACKAGE_MANIFEST.json']+[r['path'] for r in manifest['files']]:
        prefix = 'upload_'+name.replace('.','_')
        final = folder/(prefix+'_final.log')
        text = final.read_text(encoding='utf-8-sig')
        if 'M212_CHUNKED_FILE_PASS' not in text or sha(PKG/name) not in text: raise RuntimeError('Final receipt differs')
        size = (PKG/name).stat().st_size; count = (size+899)//900
        chunks = sorted(folder.glob(prefix+'_chunk_*.log'))
        if len(chunks) != count: raise RuntimeError('Transfer chunk count differs')
        for i,path in enumerate(chunks,1):
            if not re.search(r'M212_CHUNK_PASS\s+'+str(i)+r'\s+'+str(count)+r'\s+'+str(min(i*900,size))+r'\s',path.read_text(encoding='utf-8-sig')):
                raise RuntimeError('Transfer chunk sequence differs')
        receipts.append(dict(path=name,sha256=sha(PKG/name),receipt_sha256=sha(final),chunks=count))
    syntax = folder/'syntax.log'
    if '__M408_SYNTAX_RC_0__' not in syntax.read_text(encoding='utf-8-sig'): raise RuntimeError('Runner syntax missing')
    r = dict(status='PASS_M408_MANIFEST_FIRST_TRANSFER',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),
             files=receipts,syntax_sha256=sha(syntax),model_started=False)
    if save:
        out = BASE/'runs/M408-local-MLP-transfer-02/RESULT.json'; atomic(out,encoded(r),immutable=True)
        sync('latest_m408_local_mlp_transfer02',dict(status=r['status'],result=out.relative_to(ROOT).as_posix(),
             sha256=sha(out),manifest_sha256=r['manifest_sha256']),
             f'## M408 局部视觉MLP捕获传输（2026-10-05）\n\nSHA {sha(out)}；全部manifest-first/900B回执/完整SHA及bash-n核对。'
             '仅准备一次原PS视觉捕获+第12层A8-QDQ筛选，无Overlay/DMA/语言，尚未执行。')
        print('M408_TRANSFER_SYNC',sha(out))
    return r


def decode(text):
    hashes = re.findall(r'(?m)^M408_RESULT_SHA256=([0-9a-f]{64})\s*$',text)
    chunks = re.findall(r'(?m)^M408_RESULT_CHUNK=(\d+)/(\d+):([A-Za-z0-9+/=]+)\s*$',text)
    if len(hashes) != 1 or not chunks or len(chunks) != int(chunks[0][1]): raise ValueError('Missing/duplicate result')
    parts = []
    for i,(index,total,data) in enumerate(chunks):
        part = base64.b64decode(data,validate=True)
        if int(index) != i or int(total) != len(chunks) or not 0 < len(part) <= 900: raise ValueError('Chunk ordering/size differs')
        parts.append(part)
    raw = b''.join(parts); digest = hashlib.sha256(raw).hexdigest()
    if digest != hashes[0]: raise ValueError('Original SHA differs')
    r = json.loads(raw)
    if r['manifest_sha256'] != sha(PKG/'PACKAGE_MANIFEST.json') or r['gate_level'] != 'PS-only-real-input-local-MLP-A8-rejection-screen' or r['selected_layer'] != 12:
        raise ValueError('Package/gate scope differs')
    for k in ('overlay_loaded','cache_policy_changed','thread_settings_changed','PL_arithmetic_proven',
              'semantic_quality_proven','performance_pass','formal_promotion_allowed'):
        if r[k] is not False: raise ValueError('Evidence scope changed')
    for k in ('dma_allocations','fpga_transactions','language_forward_calls'):
        if type(r[k]) is not int or r[k] != 0: raise ValueError('Unexpected hardware/language work')
    if type(r['gate_return_code']) is not int or r['gate_return_code'] not in (0,1): raise ValueError('Invalid original rc')
    done = re.findall(r'M408_DONE gate_rc=(\d+) export_rc=(\d+)',text)
    if done and done != [(str(r['gate_return_code']),'0')]: raise ValueError('Gate/export differs')
    if r['status'] == 'PASS_M408_PS_LOCAL_MLP_CAPTURE_A8_SCREEN':
        if r['gate_return_code'] or r['errors'] or r['visual_forward_calls'] != 1 or r['local_mlp_forward_calls'] != 2:
            raise ValueError('PASS call counts/error incomplete')
        for k in ('component_pass','capture_exact','local_A8_screen_pass','bindings_restored','visual_owner_closed','no_pynq_import'):
            if r[k] is not True: raise ValueError('PASS numerical/lifecycle incomplete')
        expected = json.loads((PKG/'EXPECTED.json').read_bytes())
        if r['visual'] != expected['visual'] or r['preprocessed'] != expected['preprocessed']: raise ValueError('Frozen input/output differs')
        if r['backend_before'] != r['backend_after'] or r['backend_before']['settings_changed']: raise ValueError('Backend changed')
        tc = r['target_component']
        if not tc['actual_frozen_wrappers_and_encoder_forward'] or not tc['original_capture_bit_exact'] or not tc['hooks_restored'] or tc['topology_rejects'] != 3 or tc['target_path'] != 'encoder.layers.12.layer.layer': raise ValueError('Target wrapper component incomplete')
        if r['target_resolution'] != tc['topology']: raise ValueError('Actual target wrapper differs')
        c = r['component']
        if not c['real_torch_CPU'] or not c['actual_M207_class'] or not c['exception_and_duplicate_restoration'] or not c['original_hooks_restored'] or c['rejects'] != 5 or not c['full_392_T32_geometry']:
            raise ValueError('Target actual component incomplete')
        if set(r['A8_batches']) != {'input','gelu'}: raise ValueError('Target activation coverage incomplete')
        for rows in r['A8_batches'].values():
            if [v['rows'] for v in rows] != [32]*12+[8] or [v['start'] for v in rows] != list(range(0,392,32)) or any(v['shift'] != 0 or v['clipped'] != 0 for v in rows):
                raise ValueError('Original T32 activation geometry changed')
        from m407_mlp_contract import local_screen
        if set(r['quality_metrics']) != {'fc1','gelu','fc2','output','residual_sum'} or not all(local_screen(v) for v in r['quality_metrics'].values()):
            raise ValueError('Predeclared rejection screen not met')
        from m408_mlp_capture import SHAPES
        if set(r['capture']) != set(SHAPES): raise ValueError('Retained capture incomplete')
        cm = r['capture_manifest']
        if cm['path'] != '/home/ubuntu/m408_mlp_capture_02/CAPTURE_MANIFEST.json' or len(cm['files']) != 6 or not re.fullmatch('[0-9a-f]{64}',cm['sha256']):
            raise ValueError('Capture artifact identity incomplete')
        if {x['path'] for x in cm['files']} != {k+'.npy' for k in SHAPES}: raise ValueError('Capture whitelist differs')
        for x in cm['files']:
            key = x['path'][:-4]; t = x['tensor']
            if t != r['capture'][key] or t['shape'] != list(SHAPES[key]) or t['dtype'] != 'float32' or t['bytes'] != SHAPES[key][0]*SHAPES[key][1]*4 or not re.fullmatch('[0-9a-f]{64}',x['file_sha256']):
                raise ValueError('Capture file geometry/hash incomplete')
        if sum(x['file_bytes'] for x in cm['files']) > 32 << 20 or not 0 < r['elapsed_s_diagnostic_not_performance'] <= 600:
            raise ValueError('Budget exceeded')
    elif r['status'] == 'FAIL_M408_PS_LOCAL_MLP_CAPTURE_A8_SCREEN':
        if r['gate_return_code'] != 1 or not r['errors']: raise ValueError('FAIL lacks original error')
    else: raise ValueError('Unknown result')
    return digest,raw,r,len(chunks)


def collect(path,out=None,sync_function=sync):
    digest,raw,r,chunks = decode(Path(path).read_text(encoding='utf-8-sig'))
    out = out or BASE/'runs/M408-local-MLP-A8-board-02/BOARD_RESULT.json'
    atomic(out,raw,immutable=True)
    report = '# M408 真实输入局部MLP A8筛选\n\n'+r['status']+'；原rc '+str(r['gate_return_code'])+'。\n\n'
    report += '仅一次原PS视觉捕获与两次局部MLP回放，无Overlay/DMA/语言/PL事务；不证明PL数学、语义质量或性能。\n\n'
    report += json.dumps(r.get('quality_metrics',r['errors']),ensure_ascii=False,indent=2)+'\n\n'
    report += '通过后仅准备同输入精确FTZ软件参考，再按单descriptor/单chain进入PL；失败则停在局部筛选级，不扩大24层。\n'
    atomic(out.with_name('REPORT.md'),report.encode('utf-8'),immutable=True)
    sync_function('latest_m408_local_mlp_board02',dict(status=r['status'],result=out.relative_to(ROOT).as_posix(),sha256=digest,
        manifest_sha256=r['manifest_sha256'],local_A8_screen_pass=r['local_A8_screen_pass'],PL_arithmetic_proven=False,
        semantic_quality_proven=False,performance_pass=False),
        f'## M408 真实视觉第12层MLP局部A8筛选（2026-10-05）\n\n原SHA {digest}，{chunks}个≤900B严格回收；{r["status"]}，rc{r["gate_return_code"]}。'
        '只原PS视觉捕获和局部回放，Attention/GELU/norm/输入/语言及硬件保持；无Overlay/DMA/PL、无语义质量或性能PASS。'
        '通过才准备精确原FTZ同输入参考及单descriptor/chain，失败停止本级；精度和完整MLP净时间未均成立前不扩24层。')
    print('M408_SAVED_RAW_SYNC',digest,r['status'])
    return r


if __name__ == '__main__':
    if sys.argv[1:] == ['transfer']: transfer()
    elif len(sys.argv) == 3 and sys.argv[1] == 'collect': collect(ROOT/sys.argv[2])
    else: raise SystemExit('transfer | collect log')
