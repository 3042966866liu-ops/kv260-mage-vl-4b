"""Complete language layer0 MLP screening with real M120 weights/inputs.

No board access. GPU performs an ordered group arithmetic proxy with FP16 FTZ;
this is not vendor CSim, RTL, a board measurement or semantic quality approval.
"""
import hashlib, json, os, sys, threading, time, traceback
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'deployment/mage_vl4b/scripts'))
import numpy as np
import torch
from mixed_bit_checkpoint import unpack_unsigned_codes, unpack_orientation_bits, recover_full_range_rows_for_storage

OUT=ROOT/'deployment/mage_vl4b/optimization_v1/runs/M445-complete-MLP-screen-01'
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(8<<20),b''):h.update(b)
    return h.hexdigest()
def save(p,r):
    raw=(json.dumps(r,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode('utf-8')
    t=p.with_name(p.name+'.part')
    with t.open('wb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
    os.replace(t,p)
def arraysha(x):return hashlib.sha256(x.detach().cpu().contiguous().numpy().tobytes()).hexdigest()
def activation(x):
    g=x.float().reshape(x.shape[0],-1,64);m=g.abs().amax(-1)
    s=(m/127).half();s=torch.where(m==0,torch.ones_like(s),s)
    if not torch.isfinite(s).all() or (s<=0).any():raise ValueError('Unrepresentable A8 scale')
    return torch.round(g/s.float().unsqueeze(-1)).clamp(-127,127),s
def linear(x,w):
    """Exact integer partials, separate scaled FP32 terms, ordered accumulation."""
    a,sa=activation(x);c,s=w
    # [G,T,64] @ [G,64,R]; integer dot bound < 2**24, TF32 disabled.
    dots=torch.bmm(a.permute(1,0,2).contiguous(),c.permute(1,2,0).contiguous())
    z=torch.zeros((x.shape[0],c.shape[0]),device=x.device,dtype=torch.float32)
    for i in range(c.shape[1]):
        term=dots[i]*sa[:,i:i+1].float()
        term=term*s[:,i].float().unsqueeze(0)
        z=z+term
    z=z.half()
    if not torch.isfinite(z).all():raise ValueError('Nonfinite proxy output: no clipping or retry bypass')
    # Existing M157 FTZ includes signed zeros.
    z=torch.where(z.abs()<2**-14,z*0,z)
    return z.float()
def fresh(w):
    c,s,o,z=recover_full_range_rows_for_storage(torch,w.float(),4,64,'fp16','endpoints')
    signed=c.float()+torch.where(o.bool(),-7.,-8.).unsqueeze(-1)
    return (signed,s),z.float()
def mlp(x,weights):
    g=linear(x,weights[0]);u=linear(x,weights[1])
    # SiLU uses the existing NumPy expression, keeping its FP32 boundary.
    gn=g.cpu().numpy();un=u.cpu().numpy()
    a=(gn/(np.float32(1)+np.exp(-gn,dtype=np.float32)))*un
    return linear(torch.from_numpy(a).to(x.device),weights[2]),g,u
def factor_mlp(x,factors):
    g=linear(linear(x,factors[0][0]),factors[0][1])
    u=linear(linear(x,factors[1][0]),factors[1][1])
    gn=g.cpu().numpy();un=u.cpu().numpy()
    a=torch.from_numpy((gn/(np.float32(1)+np.exp(-gn,dtype=np.float32)))*un).to(x.device)
    return linear(linear(a,factors[2][0]),factors[2][1])
def metric(y,ref):
    y=y.double();ref=ref.double();e=(y-ref).norm(dim=1)/ref.norm(dim=1).clamp_min(1e-20)
    return dict(relative_l2=float((y-ref).norm()/ref.norm()),row_p95=float(torch.quantile(e,.95)),row_max=float(e.max()),
                cosine_mean=float(torch.nn.functional.cosine_similarity(y,ref).mean()),max_abs=float((y-ref).abs().max()))
def main():
    OUT.mkdir(parents=True,exist_ok=False)
    r=dict(status='RUNNING_M445_LOCAL_NUMERICAL_SCREEN',board=False,performance_pass=False,semantic_quality_pass=False,
           vendor_CSim=False,RTL=False,promoted=False,candidates=[],target='model.language_model.layers.0.mlp',
           geometry=[2560,9728,2560],baseline_build_id='0x4D343433',source_sha256=sha(Path(__file__)),
           scope='one complete MLP, real saved fixed-text input; no end-to-end language quality claim',
           provisional_screen=dict(relative_l2_max=.05,row_p95_max=.10,semantic_acceptance=False))
    save(OUT/'RESULT.json',r);phase=['identity'];stop=threading.Event();start=time.monotonic()
    def beat():
        while not stop.wait(30):print('M445_HEARTBEAT',phase[0],round(time.monotonic()-start,1),flush=True)
    threading.Thread(target=beat,daemon=True).start()
    try:
        torch.set_num_threads(8);torch.backends.cuda.matmul.allow_tf32=False
        torch.backends.cudnn.allow_tf32=False
        if not torch.cuda.is_available():raise RuntimeError('Explicit CUDA screen runtime unavailable')
        device='cuda';r['torch']=torch.__version__;r['device']=torch.cuda.get_device_name()
        cfg=json.loads((ROOT/'deployment/mage_vl4b/optimization_v1/contracts/config.json').read_text(encoding='utf-8'))
        cp=Path(cfg['checkpoint']);mp=cp/'CHECKPOINT_MANIFEST.json'
        if sha(mp)!=cfg['checkpoint_manifest_sha256']:raise ValueError('Checkpoint manifest changed')
        m=json.loads(mp.read_text(encoding='utf-8'));blob=cp/m['blob']['path']
        phase[0]='hash entire original checkpoint'
        if sha(blob)!=cfg['checkpoint_blob_sha256'] or blob.stat().st_size!=m['blob']['bytes']:raise ValueError('Blob changed')
        r['checkpoint_manifest_sha256']=sha(mp);r['checkpoint_blob_sha256']=sha(blob)
        ws=[];dense=[];bindings=[]
        with blob.open('rb') as f:
            for short in ('gate','up','down'):
                e=next(e for e in m['entries'] if e['name']==r['target']+'.'+short+'_proj.weight')
                assert e['kind']=='packed' and e['bits']==4 and e['group_size']==64
                raw={}
                for k,s in e['sections'].items():
                    f.seek(s['offset']);b=f.read(s['bytes'])
                    if hashlib.sha256(b).hexdigest()!=s['sha256']:raise ValueError('Section changed')
                    raw[k]=b
                shape=e['shape'];codes=unpack_unsigned_codes(raw['codes'],4,int(np.prod(shape))).reshape(shape[0],-1,64)
                ori=unpack_orientation_bits(raw['orientations'],e['group_count']).reshape(shape[0],-1)
                c=torch.from_numpy(codes.astype(np.float32)).to(device)+torch.from_numpy(np.where(ori,-7.,-8.).astype(np.float32)).to(device).unsqueeze(-1)
                s=torch.from_numpy(np.frombuffer(raw['scales'],'<f2').copy().reshape(shape[0],-1)).to(device)
                w=(c*s.float().unsqueeze(-1)).reshape(shape)
                ws.append((c,s));dense.append(w);bindings.append(e)
        r['weight_bindings']=bindings
        inp=ROOT/'deployment/mage_vl4b/artifacts/m143_m120_layer0_boundaries.npz'
        if sha(inp)!='9565ec2f7d1df162997456a6ccb01234c3b3e4802107ed318827553c3aa66eab':raise ValueError('Saved real input changed')
        with np.load(inp,allow_pickle=False) as a:x=torch.from_numpy(a['layer00_gate_up'].copy()).to(device)
        assert x.shape==(30,2560) and torch.isfinite(x).all()
        r['input_sha256']=sha(inp);r['input_array_sha256']=arraysha(x)
        r['calibration_rows']=list(range(0,30,2));r['evaluation_rows']=list(range(1,30,2))
        r['split_limitation']='15/15 disjoint positions in one fixed text, correlated; not an independent prompt test'
        phase[0]='complete baseline MLP'
        baseline,g,u=mlp(x,ws);ref=baseline[1::2];r['baseline_output_sha256']=arraysha(baseline)
        np.save(OUT/'input.npy',x.cpu().numpy(),allow_pickle=False)
        np.save(OUT/'baseline_output.npy',baseline.cpu().numpy(),allow_pickle=False)
        # Weight-only low-rank SVD avoids fitting the evaluation rows.
        svds=[]
        for i,w in enumerate(dense):
            phase[0]='full weight SVD '+('gate','up','down')[i]
            print('M445_SVD_START',i,flush=True)
            a,s,b=torch.linalg.svd(w,full_matrices=False)
            svds.append((a,s,b));print('M445_SVD_DONE',i,flush=True)
        phase[0]='paired complete MLP candidates'
        act=(torch.nn.functional.silu(g[::2])*u[::2])
        scores=act.square().mean(0)*dense[2].square().sum(0)
        order=torch.argsort(scores,descending=True,stable=True)
        h,d=2560,9728;base_params=3*h*d;base_wire=base_params*17//32
        for width in (9600,9472,9216,8704,7296,4864):
            ids=torch.sort(order[:width]).values
            selected=[(ws[0][0][ids],ws[0][1][ids]),(ws[1][0][ids],ws[1][1][ids])]
            # Down regrouping arbitrary surviving columns changes G64 lattice.
            dw=dense[2][:,ids];qd,_=fresh(dw);selected.append(qd)
            y,_,_=mlp(x,selected);n=3*h*width
            detail=dict(method='intermediate_channel_pruning',width=width,parameters=n,wire_weight_bytes=n*17//32,
                        ratio_to_baseline=n/base_params,linear_stages=3,chain_launches_per_T32=2,
                        parsed_values_per_token=2*width+h,metrics=metric(y[1::2],ref),
                        channel_selection='calibration E[activation^2] times original Down column norm squared',
                        down_quantization='fresh W4 G64 after arbitrary column regrouping')
            detail['screen_pass']=detail['metrics']['relative_l2']<=.05 and detail['metrics']['row_p95']<=.10
            r['candidates'].append(detail);save(OUT/'RESULT.json',r)
            np.savez(OUT/f'channels_{width}.npz',indices=ids.cpu().numpy(),gate=dense[0][ids].cpu().numpy(),up=dense[1][ids].cpu().numpy(),down=dw.cpu().numpy(),output=y.cpu().numpy())
            print('M445_CHANNEL',width,json.dumps(detail['metrics']),flush=True)
            rank=int(round((h*width/(h+d))/64))*64
            fs=[];factor_arrays={}
            for i,(a,s,b) in enumerate(svds):
                root=s[:rank].sqrt();left=a[:,:rank]*root;right=root[:,None]*b[:rank]
                qright,_=fresh(right);qleft,_=fresh(left);fs.append((qright,qleft))
                factor_arrays[f'{i}_right']=right.cpu().numpy();factor_arrays[f'{i}_left']=left.cpu().numpy()
            y=factor_mlp(x,fs);n=3*rank*(h+d)
            detail=dict(method='independent_weight_SVD',rank=rank,parameters=n,wire_weight_bytes=n*17//32,
                        ratio_to_baseline=n/base_params,linear_stages=6,chain_launches_per_T32=5,
                        parsed_values_per_token=2*d+3*rank+h,metrics=metric(y[1::2],ref),
                        factor_quantization='each fresh W4 G64, sqrt singular value balanced; A8 at all six inputs',
                        weight_relative_errors=[float(s[rank:].norm()/s.norm()) for _,s,_ in svds])
            detail['screen_pass']=detail['metrics']['relative_l2']<=.05 and detail['metrics']['row_p95']<=.10
            r['candidates'].append(detail);save(OUT/'RESULT.json',r)
            np.savez(OUT/f'lowrank_{rank}.npz',**factor_arrays,output=y.cpu().numpy())
            print('M445_LOWRANK',rank,json.dumps(detail['metrics']),flush=True)
        r['baseline_wire_weight_bytes']=base_wire;r['baseline_parsed_values_per_token']=2*d+h
        r['status']='COMPLETE_M445_LOCAL_NUMERICAL_SCREEN_NOT_BOARD'
        r['elapsed_s']=time.monotonic()-start
        r['files']=[dict(path=p.name,sha256=sha(p),bytes=p.stat().st_size) for p in sorted(OUT.iterdir()) if p.is_file() and p.name!='RESULT.json']
        save(OUT/'RESULT.json',r)
        print(r['status'],sha(OUT/'RESULT.json'),flush=True)
    except BaseException:
        r['status']='FAIL_M445_LOCAL_NUMERICAL_SCREEN';r['error']=traceback.format_exc();save(OUT/'RESULT.json',r);raise
    finally:stop.set()
if __name__=='__main__':main()
