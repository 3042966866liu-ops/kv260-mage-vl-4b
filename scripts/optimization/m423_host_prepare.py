"""Versioned integrated collector/control; no COM3 calls here."""
from m351_workflow import HERE,atomic
from m421_prepare import once

def main():
    s=(HERE/'m421_workflow.py').read_text(encoding='utf-8')
    s=s.replace('candidates/M421-combination-saved-language-01','candidates/M423-integrated-video-01').replace('runs/M421-saved-language-board-01','runs/M423-integrated-video-board-01')
    s=s.replace('m421','m423').replace('M421','M423').replace('PASS_M423_SAVED_FEATURE_DECISION_CONSISTENCY','PASS_M423_INTEGRATED_VIDEO_NUMERICAL').replace('saved-feature-fixed159-language-quality','integrated-fixed159-visual-language-quality')
    s=once(s,'or r.get(\'vision_forward_calls\',0) or',"or not 0<=r.get('vision_forward_calls',0)<=2 or")
    s=once(s,"        if r['gate_return_code'] or r['errors'] or r['model_forward_calls']!=2", "        if r.get('vision_forward_calls')!=2 or r['gate_return_code'] or r['errors'] or r['model_forward_calls']!=2")
    s=once(s,"        if r['fpga_transactions']!=1+total", "        if r['fpga_transactions']!=1+total+52")
    anchor="        q=r['logit_comparison']"
    proof="""        if r.get('integrated_sources_checked_before_overlay') is not True or r.get('visual_provider_disposed') is not True or r.get('borrowed_buffer_identity_preserved') is not True or r.get('visual_static_cache_invalidated') is not True or r.get('borrowed_extra_DMA')!=0:raise ValueError('Borrowed integration owner proof missing')
        if r.get('integrated_visual')!=[x['tensor'] for x in plan['features']] or len(r.get('integrated_exact_comparisons',[]))!=2 or any(set(x)!=set(('input','visual','token','logits','keys','values','families','grouped_attention_calls','counts')) or not all(v is True for v in x.values()) for x in r['integrated_exact_comparisons']):raise ValueError('Full integrated references differ')
        rows=r.get('visual_transactions',[])
        if len(rows)!=52 or [(x['layer'],x['part'],x['start']) for x in rows]!=[(i,p,start) for i in (12,13) for p in ('fc1','fc2') for start in range(0,392,32)] or any(x.get('completed') is not True or not safe_to_release(x['completed_snapshot']) or x['completed_snapshot']['ap_return']!=0x4d333537 for x in rows):raise ValueError('All52 visual physical transactions not proven')
        staging=r.get('visual_staging',[])
        if len(staging)!=4 or [(x['layer'],x['part'],x['bytes']) for x in staging]!=[(i,p,2228224) for i in (12,13) for p in ('fc1','fc2')]:raise ValueError('Actual four visual stage windows differ')
"""
    s=once(s,anchor,proof+anchor)
    s=once(s,"BASE/'candidates/M415-saved-feature-language-04/PACKAGE_MANIFEST.json'","BASE/'candidates/M421-combination-saved-language-01/PACKAGE_MANIFEST.json'")
    s=s.replace('latest_m423_saved_language_board','latest_m423_integrated_board').replace('latest_m423_saved_language_transfer','latest_m423_integrated_transfer').replace('runs/M423-saved-language-transfer-01','runs/M423-integrated-transfer-01')
    s=s.replace('只复用M420原版和第12＋13层候选98×2560特征','实际原版和第12＋13层候选视觉复用原七DMA、各接相同语言').replace('0视觉前向','2实际视觉前向')
    atomic(HERE/'m423_workflow.py',s.encode('utf-8'),immutable=True)
    s=(HERE/'m421_control.ps1').read_text(encoding='utf-8')
    original="foreach ($key in @('latest_m420_combination_board','latest_m420_combination_closure','latest_m415_saved_feature_language_board','latest_m368_video_closure','latest_m421_saved_language_preparation','latest_m421_saved_language_support')) { VerifyEvidence $key }"
    s=once(s,original,"__INTEGRATED_PRIOR_CHECKS__")
    s=s.replace('candidates/M421-combination-saved-language-01','candidates/M423-integrated-video-01').replace('candidates/M415-saved-feature-language-04','__BORROWED_OLD_PACKAGE__')
    s=s.replace('m421','m423').replace('M421','M423').replace('m423_saved_feature_candidate_01','m423_integrated_video_candidate_01')
    s=s.replace('__BORROWED_OLD_PACKAGE__','candidates/M421-combination-saved-language-01')
    s=s.replace('__INTEGRATED_PRIOR_CHECKS__',"foreach ($key in @('latest_m420_combination_board','latest_m420_combination_closure','latest_m421_saved_language_board','latest_m421_saved_language_closure','latest_m422_borrowed_DMA_component','latest_m423_integrated_preparation','latest_m423_integrated_support')) { VerifyEvidence $key }")
    s=s.replace('latest_m423_saved_language_preparation','latest_m423_integrated_preparation').replace('latest_m423_saved_language_support','latest_m423_integrated_support').replace('latest_m423_saved_language_transfer','latest_m423_integrated_transfer').replace('runs/M423-saved-language-board-01','runs/M423-integrated-video-board-01')
    atomic(HERE/'m423_control.ps1',s.encode('utf-8'),immutable=True)
    print('M423_HOST_PREPARED')
if __name__=='__main__':main()
