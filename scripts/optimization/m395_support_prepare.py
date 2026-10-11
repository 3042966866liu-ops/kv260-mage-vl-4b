"""Draft controller and exact recovery for conditional SiLU performance gate."""
from m351_workflow import HERE,BASE,atomic,sha
from m377_prepare import once

def main():
    for src,dst in [('m394_control.ps1','m395_control.ps1'),('m394_workflow.py','m395_workflow.py')]:
        s=(HERE/src).read_text(encoding='utf-8-sig').replace('M394','M395').replace('m394','m395')
        s=s.replace('silu-video','silu-performance').replace('silu_video','silu_performance').replace('M387-ps-video-01','M388-ps-performance-01')
        s=s.replace('run_m395_silu_performance.sh','run_m395_light_video.sh').replace('M395_ENABLE_SILU_VIDEO','M395_ENABLE_LIGHT_VIDEO').replace('-TimeoutSeconds 1200','-TimeoutSeconds 3900')
        s=s.replace('一次原固定159视频SiLU数值门禁','一次同核原表达式/SiLU工作缓冲ABBABAAB轻量请求对照').replace('精确M387复制','精确M388复制')
        atomic(HERE/dst,s.encode('utf-8'))
    c=(HERE/'m388_collect.py').read_text(encoding='utf-8').replace('M388','M395').replace('m388','m395').replace('ps-performance','silu-performance').replace('ps_performance','silu_performance').replace('balanced-fixed159-video-original-staging-versus-PS-prefetch','balanced-fixed159-video-original-expression-versus-SiLU-workspace')
    c=c.replace('PS_video_prerequisite_sha256','silu_video_prerequisite_sha256')
    import json
    prior=json.loads((BASE/'runs/M395-silu-performance-preparation-01/RESULT.json').read_text(encoding='utf-8'))['video_raw_sha256']
    c=c.replace('0d36bf91329a1f2e433bfad64905b61836aa75e36c85a54432c028551609d348',prior)
    c=once(c,"r['ps_prefetch_enabled']!='B only'","r['ps_prefetch_enabled'] is not False or r['silu_workspace_enabled']!='B only'")
    c=c.replace("r['gate_return_code']!=int(cs[0])","type(r['gate_return_code']) is not int or r['gate_return_code']!=int(cs[0])")
    a=c.index("            p=s['ps_session']");z=c.index("            n=s['numeric_sha_after_timer']",a)
    c=c[:a]+'''            p=s['silu_scope']
            if s['variant']=='A':
                if p!=dict(enabled=False,original_expression=True,extra_pynq_allocations=0):raise ValueError('Original expression changed')
            else:
                from m394_collect import expected_scope
                if p!=dict(expected_scope(),scope_weakref_dead=True):raise ValueError('Timed workspace/owner/consumer lifecycle differs')
''' +c[z:]
    # Host collector cannot depend on a prior candidate path/module at board time.
    c=c.replace('                from m394_collect import expected_scope','                from m394_collect import expected_scope')
    c=c.replace('A原暂存/B普通PS预读，均原单parser','A原表达式/B单SiLU工作缓冲，均原单parser').replace('Changed PS prerequisite','Changed SiLU prerequisite')
    atomic(HERE/'m395_collect.py',c.encode('utf-8'))
    print('M395_CONTROL_RECOVERY_DRAFT_READY')

if __name__=='__main__':main()
