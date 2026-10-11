"""Generate draft support from proven strict text recovery tests."""
from m351_workflow import HERE,atomic

def main():
    s=(HERE/'m393_support.py').read_text(encoding='utf-8').replace('M393','M394').replace('m393','m394').replace('M386','M387').replace('m386','m387')
    s=s.replace('silu-text','silu-video').replace('silu_text','silu_video').replace('ps-text','ps-video').replace('ps_text','ps_video').replace('SILU_TEXT','SILU_VIDEO').replace('fixed-text-numerical','fixed159-video-numerical')
    s=s.replace('silu_layer_prerequisite_sha256','silu_text_prerequisite_sha256').replace('8eb467882777edd2ff8d9b11e6b02077a58b72f20a1d401478ac67502b35a63d','5f304889c48969a259297b56dfc4d7e361f19ed434208b4e8ae8a154c33785b3').replace('workspace_bytes=1167360','workspace_bytes=6187008')
    s=s.replace("('layer_result',{})","('video_result',{})").replace('257<<20','1025<<20').replace('test_m394_silu_scope.py','test_m394_video_scope.py').replace("HERE/'m394_silu_scope.py'","HERE/'m393_silu_scope.py'").replace("PKG/'m394_silu_scope.py'","PKG/'m393_silu_scope.py'")
    s=s.replace("HERE/'m387_control.ps1'","HERE/'m387_control_recovered_02.ps1'")
    a=s.index('    for kind in (');s=s[:a]+'''    for k,v in [('visual_features',{}),('prompt_token_ids',[]),('vision_forward_calls',0),('candidate_semantic',{}),('decoder',{}),('same_loading_path_video_sha256','bad'),('preprocessed',{}),('events',[])]:
        q=copy.deepcopy(r);q[k]=v;bad.append(export(q))
    q=copy.deepcopy(r);q['head_observer_proof']['every_retry_physical_boundary']=False;bad.append(export(q))
''' +s[a:]
    s=s.replace("log=ROOT/'tmp/m394/support_tests.log'","log=ROOT/'tmp/m394_video_support_draft.log'").replace("'Ran 6 tests'","'Ran 4 tests'").replace('actual_full_prefill_gate_lifetime_tests=6','actual_video_wrapper_stream_lifetime_tests=4')
    s=s.replace("'m394_silu_scope.py','m394_silu_workspace.py'","'m393_silu_scope.py','m393_silu_workspace.py'")
    s=s.replace('6项真实原36层Prefill/30与159尺寸激活数学/实际gate调用/晚层故障与head完成屏障检查','4项实际冻结视频wrapper/原M276 stream/159几何/晚层故障owner保留/输入拒绝检查（复用M393同SHA6项Prefill证据）').replace('仅本级文本数值','仅本级视频数值').replace('一次原固定30文本/完整head数值门禁','一次原固定159视频/完整head数值门禁')
    s=s.replace('PASS_OFFLINE_SILU_TEXT_CONTROL_RECOVERY','PASS_OFFLINE_SILU_VIDEO_CONTROL_RECOVERY')
    atomic(HERE/'m394_support.py',s.encode('utf-8'))
    print('M394_SUPPORT_GENERATED')

if __name__=='__main__':main()
