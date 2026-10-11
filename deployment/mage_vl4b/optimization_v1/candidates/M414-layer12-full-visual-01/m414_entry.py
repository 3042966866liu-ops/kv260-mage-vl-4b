"""CPU-only component isolation and bounded failed-reference evidence."""
import hashlib,json,os,subprocess,sys
from pathlib import Path


def run_component(root, folder, script=None):
    import torch
    def state():
        return dict(rng_sha256=hashlib.sha256(torch.get_rng_state().numpy().tobytes()).hexdigest(),
                    intraop=torch.get_num_threads(), interop=torch.get_num_interop_threads(),
                    dtype=str(torch.get_default_dtype()), inference=torch.is_inference_mode_enabled())
    before=state();env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=os.pathsep.join(sys.path))
    script=script or Path(__file__).with_name('test_m414_quality.py')
    child=subprocess.run([sys.executable,'-B',str(script),str(root)],env=env,capture_output=True,timeout=90)
    after=state()
    if before!=after:raise RuntimeError('CPU component changed parent Torch state')
    for name,data in (('component_stdout.txt',child.stdout),('component_stderr.txt',child.stderr)):
        if len(data)>128<<10:raise RuntimeError('Bounded CPU fixture output exceeded')
        with (folder/name).open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
    if child.returncode:raise RuntimeError('Isolated CPU fixture failed: '+child.stderr.decode('utf-8',errors='replace')[-2000:])
    lines=[x.split('=',1)[1] for x in child.stdout.decode('utf-8').splitlines() if x.startswith('M414_COMPONENT=')]
    if len(lines)!=1:raise RuntimeError('CPU fixture marker missing or duplicated')
    component=json.loads(lines[0])
    return component,dict(separate_process=True,return_code=child.returncode,timeout_seconds=90,
                          before=before,after=after,parent_state_unchanged=True,
                          stdout_sha256=hashlib.sha256(child.stdout).hexdigest(),
                          stderr_sha256=hashlib.sha256(child.stderr).hexdigest())


def retain_reference(folder,visual,captures):
    import numpy as np
    from m414_quality import tensor
    values=dict(captures,visual=visual)
    if set(values)!={'visual','residual','input','fc1','gelu','fc2','output'}:raise RuntimeError('Bounded reference keys differ')
    shapes=dict(visual=(98,2560),residual=(392,1024),input=(392,1024),fc1=(392,4096),gelu=(392,4096),fc2=(392,1024),output=(392,1024))
    if any(v.dtype!=np.float32 or v.shape!=shapes[k] or not np.isfinite(v).all() for k,v in values.items()):raise RuntimeError('Failed reference array contract differs')
    if sum(v.nbytes for v in values.values())>32<<20:raise RuntimeError('Failed reference evidence budget exceeded')
    result=[]
    for k,v in values.items():
        path=folder/('failed_reference_'+k+'.npy');partial=path.with_suffix('.partial')
        if path.exists():raise RuntimeError('Original reference evidence cannot be replaced')
        with partial.open('xb') as f:np.save(f,v,allow_pickle=False);f.flush();os.fsync(f.fileno())
        os.replace(partial,path)
        result.append(dict(path=path.name,file_bytes=path.stat().st_size,file_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),tensor=tensor(v)))
    return result
