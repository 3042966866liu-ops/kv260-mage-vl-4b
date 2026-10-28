from common_joint import *
import numpy as np

def main():
    f=RUNS/(PREFIX+'-target-head-training-01/RESULT.json');v=read(f);assert v['original_rc']==0
    arm='progressive_augmented';a=v['arms'][arm];assert a['evaluations']['fixed_demo_correct']==a['evaluations']['fresh_hard_correct']==4
    package=OPT/'candidates/M525-10V18L-learned-head-augmented-01';assert not package.exists();package.mkdir()
    source=ROOT/a['adapter_path'];assert sha(source)==a['adapter_sha256'];manifest=dict(scale=1.,arm=arm,training_result_sha256=sha(f),training_adapter_sha256=sha(source),inference_extra_MACs=1235968,full_vocab=151936,body_unmodified=True,no_token_specific_bias=True)
    with np.load(source,allow_pickle=False) as z:
        for name in ('A','B'):
            data=z[name].copy();file=package/(name+'.npy')
            with file.open('xb') as stream:np.save(stream,data,allow_pickle=False)
            manifest[name]=dict(path=file.name,sha256=sha(file),bytes=file.stat().st_size)
    code=HERE/'learned_head.py';compile(code.read_bytes(),code.name,'exec');(package/code.name).open('xb').write(code.read_bytes())
    manifest['source_sha256']=sha(code);save(package/'HEAD_MANIFEST.json',manifest)
    rows=[dict(path=p.name,sha256=sha(p),bytes=p.stat().st_size) for p in sorted(package.iterdir())]
    save(package/'PACKAGE_MANIFEST.json',dict(files=rows,file_count=len(rows),total_bytes=sum(r['bytes'] for r in rows)))
    p=dict(status='FROZEN_REAL_FP32_HEAD_EXPORT_AND_INDEPENDENT_RELOAD',package=relative(package),manifest_sha256=sha(package/'PACKAGE_MANIFEST.json'),head_manifest_sha256=sha(package/'HEAD_MANIFEST.json'),training_result_sha256=sha(f),new_full_prefills=12,source_sha256=sha(HERE/'target_reload.py'),selected_arm='progressive_augmented',heldout_opened=False,board_actions=0)
    out=RUNS/(PREFIX+'-target-head-reload-protocol-01/RESULT.json');save(out,p);print(p['status'],sha(out),flush=True)
if __name__=='__main__':main()
