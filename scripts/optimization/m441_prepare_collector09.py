"""Derive strict original saved-byte collector for same-policy two kernels."""
import m351_workflow as w
from m441_host_io08 import atomic
from m441_prepare_layer09 import once

def main():
    src=(w.HERE/'m437_workflow.py').read_text(encoding='utf-8');src=src[:src.index('\ndef collect(')]
    src=src.replace('M437-late11-natural-IO-performance-01','M441-complete-request-performance-09').replace('M437-natural-IO-board-01','M441-complete-request-performance-board-09').replace('M437','M441P')
    src=src.replace('natural-IO-complete-request-performance','same-visual-kernel-complete-request-performance')
    src=src.replace("r['build_id']!='0x4D333537'","r['build_id']!='0x4D343431'")
    src=src.replace("r['fpga_transactions']!=11089","r['fpga_transactions']!=12813").replace("r['completed_visual_physical']!=1716","r['completed_visual_physical']!=3432")
    src=once(src,"index=0 if s['variant']=='A' else 1;expected=references[index]","index=1;expected=references[index]\n            expected_build=0x4d333537 if s['variant']=='A' else 0x4d343431\n            if s.get('kernel_build')!=f'0x{expected_build:08X}':raise ValueError('Per-request kernel identity differs')")
    src=once(src,"s['final_snapshot']['ap_return']!=0x4d333537","s['final_snapshot']['ap_return']!=expected_build")
    src=src.replace("proof['snapshot']['ap_return']!=0x4d333537","proof['snapshot']['ap_return']!=0x4d343431").replace("r['final_snapshot']['ap_return']!=0x4d333537","r['final_snapshot']['ap_return']!=0x4d343431")
    anchor="        proof=r['same_overlay_minimal_proof']"
    add='''        perf=json.loads((PKG/'PERFORMANCE_PLAN.json').read_bytes())
        if r.get('m441_video_numerical_source_sha256')!=perf['m441_video_sha256']:raise ValueError('M441 numerical prerequisite differs')
        switches=[(1,'A'),(2,'B'),(4,'A'),(6,'B'),(8,'A'),(9,'B'),(10,'A'),(12,'B')]
        transitions=r.get('kernel_transitions',[]);environments=r.get('kernel_switch_environment',[])
        if len(transitions)!=8 or len(environments)!=8 or r.get('kernel_switch_minimal_attempts')!=8:raise ValueError('Frozen eight transitions missing')
        prior=0x4d343431
        for row,env,(index,variant) in zip(transitions,environments,switches):
            expected=0x4d333537 if variant=='A' else 0x4d343431
            if row['index']!=index or row['variant']!=variant or row['from_build']!=prior or row['to_build']!=expected:raise ValueError('Kernel transition order differs')
            for key in ('completed','full_output_exact','original_buffer_identities_preserved','outside_request_timer'):
                if row.get(key) is not True:raise ValueError('Kernel transition incomplete '+key)
            if row.get('extra_DMA')!=0 or not safe_to_release(row['before_snapshot']) or row['before_snapshot']['ap_return']!=prior or not safe_to_release(row['completed_snapshot']) or row['completed_snapshot']['ap_return']!=expected:raise ValueError('Kernel transition ownership/Build unsafe')
            manifest='2e9cbd00d0d01edf05e171674f71f86a94ce389a0658ce6c5466cebb77220d18' if variant=='A' else '56253626a550c9c1358e805e6e3ad9b8b03c2fd9c1ff048be87c64c9f04dd5a0'
            if env['index']!=index or env['variant']!=variant or env['manifest_sha256']!=manifest or not re.fullmatch('[0-9a-f]{64}',env['environment_sha256']):raise ValueError('Switch environment proof differs')
            prior=expected
'''
    src=once(src,anchor,add+anchor)
    src+='''
def collect(log):
    digest,raw,r,count=decode(Path(log).read_text(encoding='utf-8-sig'))
    atomic(OUT,raw,immutable=True)
    atomic(OUT.with_name('COLLECTION.json'),encoded(dict(raw_sha256=digest,chunks=count,source_log=str(log),source_log_sha256=sha(Path(log)),reexecuted=False)),immutable=True)
    sync('latest_m441_complete_request_board',dict(status=r['status'],result=OUT.relative_to(ROOT).as_posix(),sha256=digest,manifest_sha256=r['manifest_sha256'],build_id=r['build_id'],numerical_pass=r['numerical_pass'],performance_pass=False),f'## M441 同视觉完整请求测量回收09（2026-10-09）\\n\\nraw {digest}，{count}个900B原字节块，原rc{r["gate_return_code"]}；{r["status"]}。固定同视觉A原M357/B新M441、4＋8全样本及计时后数值/七owner核对；只收集非性能裁决，不重跑或追加。')
    print(r['status'],digest,count)
    return r['gate_return_code']

if __name__=='__main__':
    import sys
    raise SystemExit(collect(sys.argv[1]))
'''
    compile(src,'m441_performance_collect09.py','exec')
    atomic(w.HERE/'m441_performance_collect09.py',src.encode('utf-8'),immutable=True)
    ctl=w.HERE/'m441_performance_control09.ps1'
    text=ctl.read_text(encoding='utf-8').replace('M441P_ENABLE_WARM_REQUESTS=1','M441P_ENABLE_INTEGRATED_VIDEO=1')
    atomic(ctl,text.encode('utf-8'))
    print('M441_PERFORMANCE_COLLECTOR_PREPARED')

if __name__=='__main__':main()
