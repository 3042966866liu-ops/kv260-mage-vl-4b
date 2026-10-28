"""Independent actual cropped M207 modules and FP64 bias/Gram audit."""
import sys,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common_v4 import *
def main():
    p=verify();fit=read(FIT/'RESULT.json');assert fit['primary_rc']==0 and fit['selected_local_method']
    out=RUNS/'M536-V4-3584-recovery-local-audit-01';out.mkdir(exist_ok=False)
    v=dict(status='FAIL_M536_LOCAL_RECOVERY_AUDIT',primary_rc=1,board_commands=0,training_steps=0,complete_model_forwards=0)
    runtime=selector=subset=override=None
    try:
        torch,runtime,selector,subset,_=cpu_setup()
        from v4_recovery_native import V4Recovery
        mlp=core(subset.original[4]).mlp;original=(mlp.fc1,mlp.fc2);act=mlp.activation_fn
        w2=mlp.fc2.store.decode(mlp.fc2.name);bias2=mlp.fc2.bias.numpy().copy()
        keep=np.array(fit['group_selection']['kept_original_groups']);ids=np.concatenate([np.arange(g*64,(g+1)*64) for g in keep])
        rows=[];residuals=[];raw_SSE=0.;captured={}
        for item in fit['prefix_captures']:
            f=ROOT/item['file'];assert sha(f)==item['sha256']
            if item['kind']=='clean':
                with np.load(f,allow_pickle=False) as z:captured[item['id']]={k:z[k].copy() for k in z.files}
        override=V4Recovery(torch,mlp,PKG,lambda:None)
        with torch.inference_mode():
            for request in p['training_requests']:
                item=captured[request['id']];x=torch.from_numpy(item['x'][None])
                assert torch.equal(mlp.forward(x)[0],torch.from_numpy(item['y']))
                raw=torch.nn.functional.linear(torch.from_numpy(item['h'][:,ids].copy()),torch.from_numpy(w2[:,ids].copy()),torch.from_numpy(bias2)).numpy()
                difference=item['y'].astype(np.float64)-raw.astype(np.float64)
                residuals.append(difference);raw_SSE+=float(np.square(difference).sum())
                override.select(True);y=mlp.forward(x)[0].numpy();override.select(False)
                m=metric(y,item['y']);recorded=next(r for r in fit['variants'] if r['name']==fit['selected_local_method'])['metrics']
                old=next(r for r in recorded['clean_fit'] if r['id']==request['id'])
                assert abs(m['relative_L2']-old['relative_L2'])<=5e-6 and abs(m['cosine']-old['cosine'])<=5e-6
                assert passes([m]);rows.append(dict(id=request['id'],**m,actual_sliced_M207_fc1_GELU_fc2=True))
            with np.load(RUNS/'M535-V4-local-screen-board-01/V4_input.npz',allow_pickle=False) as z:x=torch.from_numpy(z['MLP_input'].copy())
            original_y=mlp.forward(x).numpy();override.select(True);candidate_y=mlp.forward(x).numpy();override.select(False)
            anchor=metric(candidate_y,original_y);assert passes([anchor])
        mean=np.concatenate(residuals).mean(0).astype(np.float32)
        with np.load(FIT/'R1_fused.npz',allow_pickle=False) as z:
            assert np.array_equal(mean,z['R1']) and np.array_equal(np.add(z['original_bias2'],mean,dtype=np.float32),z['fused_bias2'])
        with np.load(FIT/'contribution_gram.npz',allow_pickle=False) as z:G=z['gram']
        removed=fit['group_selection']['removed_original_groups'];predicted=float(G[np.ix_(removed,removed)].sum())
        assert abs(predicted-raw_SSE)/max(raw_SSE,1e-30)<=2e-5
        override.close();assert (mlp.fc1,mlp.fc2)==original and mlp.activation_fn is act
        plan=read(PKG/'V4_PLAN.json')
        with np.load(PKG/plan['weights']['path'],allow_pickle=False) as z:
            assert z['fc1_codes'].shape==(3584,16,64) and z['fc2_codes'].shape==(1024,56,64)
            assert z['fc1_scales'].dtype==z['fc2_scales'].dtype==np.float16
            assert z['fc2_codes'].min()>=-8 and z['fc2_codes'].max()<=7
        v.update(status='PASS_M536_ACTUAL_SLICED_PS_MLP_AND_BIAS_EXPORT_AUDIT',primary_rc=0,
            fit_result_sha256=sha(FIT/'RESULT.json'),candidate_manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),
            rows=rows,saved_A53_input=anchor,R1_independent_FP64_mean_bitwise_equal=True,
            group_Gram_prediction_relative_difference=abs(predicted-raw_SSE)/raw_SSE,
            actual_module_not_only_sliced_cached_hidden_tested=True,original_GELU_and_modules_restored=True,
            full_answer_quality_proven=False,board_TTFT_proven=False)
    except BaseException:v['traceback']=traceback.format_exc()
    finally:
        if override is not None:override.close()
        if subset is not None:subset.close()
        if selector is not None:selector.close()
        if runtime is not None:runtime.close()
        save(out/'RESULT.json',v);print(v['status'],v.get('traceback',''),flush=True)
    return v['primary_rc']
if __name__=='__main__':raise SystemExit(main())
