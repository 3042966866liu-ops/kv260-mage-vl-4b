"""Complete current22 vs PS V2/V3/V6-3072 features, no language or hardware."""
import sys,traceback
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import *
PREP=R/(PREFIX+'-protocol-02');FIT=R/(PREFIX+'-fit-02')

def main():
    p=verify();fit=check_files(FIT);assert not FEATURES.exists();FEATURES.mkdir();start=time.monotonic()
    v=dict(status='FAIL_PS_V236_3072_COMPLETE_FEATURES',original_rc=1,protocol_sha256=sha(PREP/'RESULT.json'),
        fit_sha256=sha(FIT/'RESULT.json'),requests=[],comparisons=[],board_commands=0,heldout_opened=0,
        native_A53=False,FPGA_timing=False,quality_pass=False)
    runtime=None;bound=[];hooks=[];swaps=[]
    try:
        torch,runtime,linear,preprocess=setup()
        from late_oracle import LateOracle
        oracle=LateOracle(torch,p);bound=oracle.bind(runtime)
        originals={}
        for arm in ('A','B'):
            if arm=='B':
                for row in p['selected']:
                    with np.load(FIT/'codes'/(row['key']+'.npz'),allow_pickle=False) as z:mlp,old=replace_PS(torch,runtime,linear,row['index'],z)
                    swaps.append((mlp,old))
                    b=np.frombuffer((FIT/'R1'/(row['key']+'_FP32.bin')).read_bytes(),np.float32).copy()
                    correction=torch.from_numpy(b)
                    def compensate(m,a,y,bias=correction):
                        assert y.dtype==torch.float32 and tuple(y.shape)==(1,392,1024)
                        return torch.add(y,bias)
                    hooks.append(mlp.register_forward_hook(compensate))
            versions=[(n,z._version,tuple(z.shape),z.data_ptr()) for n,z in runtime.vision.named_parameters()]
            for request in p['requests']:
                assert time.monotonic()-start<p['budgets']['feature_seconds']
                folder=FEATURES/arm/request['id'];oracle.trace=[]
                x=inputs(torch,preprocess,request)
                with torch.inference_mode():output=runtime(x['pixel_values'].numpy(),x['image_grid_thw'].numpy(),x['patch_positions'].numpy()).copy()
                assert output.shape==(98,2560) and np.isfinite(output).all()
                assert len(oracle.trace)==286 and {(r['layer'],r['part']) for r in oracle.trace}=={(i,part) for i in range(13,24) for part in ('fc1','fc2')}
                array(folder/'features_FP32.npy',output);save(folder/'M455_TRACE.json',oracle.trace)
                assert versions==[(n,z._version,tuple(z.shape),z.data_ptr()) for n,z in runtime.vision.named_parameters()]
                record=dict(id=request['id'],arm=arm,feature_sha256=sha(folder/'features_FP32.npy'),
                    trace_sha256=sha(folder/'M455_TRACE.json'),logical_T32_calls=286,
                    actual_attempts=sum(len(t['attempts']) for t in oracle.trace),
                    parent22_unchanged=True,new_PS_layers=[2,3,6] if arm=='B' else [])
                v['requests'].append(record)
                if arm=='A':
                    originals[request['id']]=output
                    native=np.load(ROOT/request['features']['A']['path'],allow_pickle=False)
                    record['cross_platform_parent_vs_saved_native']=metric(output,native)
                else:
                    m=metric(output,originals[request['id']]);g=p['feature_gate']
                    passed=m['relative_L2']<=g['max_relative_L2'] and m['global_cosine']>=g['min_global_cosine'] and m['min_token_cosine']>=g['min_token_cosine']
                    v['comparisons'].append(dict(id=request['id'],**m,feature_gate_pass=passed))
                print('PS_V236_COMPLETE_FEATURE',arm,request['id'],record.get('cross_platform_parent_vs_saved_native',v['comparisons'][-1] if v['comparisons'] else {}),flush=True)
        passed=len(v['comparisons'])==12 and all(c['feature_gate_pass'] for c in v['comparisons'])
        v.update(status=('PASS' if passed else 'REJECT')+'_PS_V236_3072_COMPLETE_SOFTWARE_FEATURE_GATE',
            original_rc=0,feature_gate_pass=passed,native_A53_validation_pending=True,
            exact_late_M455_packet_oracle=True,source_GELU_PS_retained=True,parameter_updates=0,
            natural_answers_pending=True,full_release_quality_pass=False)
    except BaseException:v['traceback']=traceback.format_exc()
    finally:
        for h in hooks:h.remove()
        for mlp,old in reversed(swaps):mlp.fc1,mlp.fc2=old
        if bound:
            from late_oracle import LateOracle
            LateOracle.restore(bound)
        if runtime is not None:runtime.close()
        v['elapsed_s']=time.monotonic()-start;v['files']=files(FEATURES);save(FEATURES/'RESULT.json',v)
        print(v['status'],v.get('traceback',''),flush=True)
    return v['original_rc']
if __name__=='__main__':raise SystemExit(main())
