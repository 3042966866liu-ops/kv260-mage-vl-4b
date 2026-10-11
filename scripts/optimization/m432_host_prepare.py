"""Derive a strict late11 integrated collector from the accepted language collector."""
from m351_workflow import HERE, atomic
from m427_prepare import once


def main():
    s = (HERE / 'm428_workflow.py').read_text(encoding='utf-8')
    s = s.replace('candidates/M428-late11-saved-language-02', 'candidates/M432-late11-integrated-video-01').replace('runs/M428-saved-language-board-01', 'runs/M432-integrated-video-board-01')
    s = s.replace('m428', 'm432').replace('M428', 'M432')
    s = s.replace('PASS_M432_SAVED_FEATURE_DECISION_CONSISTENCY', 'PASS_M432_INTEGRATED_VIDEO_NUMERICAL').replace('saved-feature-fixed159-language-quality', 'integrated-fixed159-visual-language-quality')
    s = once(s, "or r.get('vision_forward_calls',0) or", "or not 0<=r.get('vision_forward_calls',0)<=2 or")
    s = once(s, "        if r['gate_return_code'] or r['errors'] or r['model_forward_calls']!=2", "        if r.get('vision_forward_calls')!=2 or r['gate_return_code'] or r['errors'] or r['model_forward_calls']!=2")
    s = once(s, "        if r['fpga_transactions']!=1+total", "        if r['fpga_transactions']!=1+total+286")
    extra = '''        from m429_pl_range import SavedWireCheck
        board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
        language_e=board['latest_m428_saved_language_board'];software_e=board['latest_m427_half_software_board']
        for e in (language_e,software_e):
            if sha(ROOT/e['result'])!=e['sha256']:raise ValueError('Frozen comparison source differs')
        language=json.loads((ROOT/language_e['result']).read_bytes())
        software=json.loads((ROOT/software_e['result']).read_bytes())
        accepted=next(x for x in software['ranges'] if x['name']=='late_13_23')
        keys=('input','visual','token','logits','keys','values','families','grouped_attention_calls','counts','decision')
        if any(any(s[k]!=old[k] for k in keys) for s,old in zip(samples,language['samples'])) or r['transactions']!=language['transactions']:raise ValueError('Complete accepted M428 sample/physical retry sequence differs')
        for k in ('integrated_sources_checked_before_overlay','visual_provider_disposed','borrowed_buffer_identity_preserved','visual_static_cache_invalidated','visual_bindings_restored'):
            if r.get(k) is not True:raise ValueError('Borrowed integration owner proof missing:'+k)
        if r.get('borrowed_extra_DMA')!=0 or r.get('peak_live_visual_layer_scopes')!=1 or r.get('visual_matched_wire_batches')!=286:raise ValueError('Exact borrowed visual scope required')
        if r.get('integrated_visual')!=[x['tensor'] for x in plan['features']] or len(r.get('integrated_exact_comparisons',[]))!=2 or any(set(x)!=set(('input','visual','token','logits','keys','values','families','grouped_attention_calls','counts')) or not all(v is True for v in x.values()) for x in r['integrated_exact_comparisons']):raise ValueError('Complete integrated references missing')
        expected_boundaries=[dict(layer=i,tensor=x['candidate']) for i,x in enumerate(accepted['boundary_comparison'])]
        if r.get('integrated_boundaries')!=expected_boundaries:raise ValueError('All24 complete visual boundaries differ')
        guard=SavedWireCheck(accepted['reference_batches'],lambda *x:None)
        rows=r.get('visual_transactions',[])
        if len(rows)!=286 or [(x['layer'],x['part'],x['start'],x['shift']) for x in rows]!=list(guard.expected_position):raise ValueError('All286 saved visual transaction identities required')
        for x in rows:
            ref=accepted['reference_batches'][str(x['layer'])][x['part']][x['start']//32]
            if x.get('completed') is not True or x['input_bytes']!=ref['input_bytes'] or x['output_bytes']!=ref['output_bytes'] or not safe_to_release(x['completed_snapshot']) or x['completed_snapshot']['ap_return']!=0x4d333537:raise ValueError('Visual DMA completion/build/bytes unproven')
        staging=r.get('visual_staging',[])
        if [(x['layer'],x['part'],x['bytes']) for x in staging]!=[(i,p,2228224) for i in range(13,24) for p in ('fc1','fc2')]:raise ValueError('All22 actual visual windows differ')
'''
    s = once(s, "        q=r['logit_comparison']", extra + "        q=r['logit_comparison']")
    s = s[:s.index('\ndef upload_names():')]
    # Reporting and evidence key must describe the actual integrated scope.
    s = s.replace('latest_m432_saved_language_board', 'latest_m432_integrated_board')
    s = s.replace('只复用M426保存原版和M427后11层候选98×2560特征', '实际原视觉与后11层PL视觉复用原七DMA，分别接同原语言路径')
    s = s.replace('0视觉前向', '2实际视觉前向').replace('保存原版与已通过特征筛查的后11层候选', '实际计算原版与已通过特征筛查的后11层候选')
    s = s.replace('2026-10-06', '2026-10-07')
    s += '''
def upload_names():
    old=BASE/'candidates/M428-late11-saved-language-02'
    byname={x['path']:x for x in json.loads((old/'PACKAGE_MANIFEST.json').read_bytes())['files']}
    m=json.loads((PKG/'PACKAGE_MANIFEST.json').read_bytes())
    return ['PACKAGE_MANIFEST.json']+[x['path'] for x in m['files'] if byname.get(x['path'])!=x]

def transfer():
    folder=ROOT/'tmp/m43201/board';m=json.loads((PKG/'PACKAGE_MANIFEST.json').read_bytes());receipts=[]
    for name in upload_names():
        size=(PKG/name).stat().st_size;count=(size+899)//900;prefix='upload_'+name.replace('.','_')
        final=(folder/(prefix+'_final.log')).read_text(encoding='utf-8-sig')
        if 'M212_CHUNKED_FILE_PASS' not in final or sha(PKG/name) not in final:raise ValueError('Transfer whole SHA absent')
        chunks=sorted(folder.glob(prefix+'_chunk_*.log'))
        if len(chunks)!=count:raise ValueError('Transfer count differs')
        for i,p in enumerate(chunks,1):
            if not re.search(r'M212_CHUNK_PASS\\s+'+str(i)+r'\\s+'+str(count)+r'\\s+'+str(min(i*900,size))+r'\\s',p.read_text(encoding='utf-8-sig')):raise ValueError('Transfer order differs')
        receipts.append(dict(path=name,sha256=sha(PKG/name),chunks=count))
    marker=f'M432_ASSEMBLY_PASS {sha(PKG/"PACKAGE_MANIFEST.json")} {m["file_count"]} {m["total_bytes"]}'
    if marker not in (folder/'assembly.log').read_text(encoding='utf-8-sig') or '__M432_SYNTAX_RC_0__' not in (folder/'syntax.log').read_text(encoding='utf-8-sig'):raise ValueError('Assembly/bash-n missing')
    r=dict(status='PASS_M432_MANIFEST_FIRST_HASHED_TRANSFER',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),receipts=receipts,gate_started=False)
    out=BASE/'runs/M432-integrated-transfer-01/RESULT.json';atomic(out,encoded(r),immutable=True)
    sync('latest_m432_integrated_transfer',dict(status=r['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out),manifest_sha256=r['manifest_sha256']),f'## M432 完整请求数值包传输（2026-10-07）\\n\\nSHA {sha(out)}；manifest-first900B整SHA/逐块顺序、同SHA旧包完整组装及bash-n通过，未运行。')
    print('M432_TRANSFER_SYNC',sha(out))

if __name__=='__main__':
    import sys
    if sys.argv[1:]==['transfer']:transfer()
    elif len(sys.argv)==3 and sys.argv[1]=='collect':collect(sys.argv[2])
    else:raise SystemExit('transfer | collect LOG')
'''
    atomic(HERE / 'm432_workflow.py', s.encode('utf-8'), immutable=True)
    print('M432_HOST_PREPARED')


if __name__ == '__main__':
    main()
