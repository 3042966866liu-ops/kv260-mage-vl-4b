"""Original and two fixed cropped L1 probes under actual M455 scale selection.

Two local 32-row software MLPs, zero complete models or hardware. The CUDA
integer dots/ordered FP32 group sums are only an oracle until new CSim passes.
"""
import ast,hashlib,importlib.util,json,os,sys,time,traceback
from pathlib import Path
import numpy as np
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'experiments/speed_target_30s_20261020'),str(ROOT/'experiments/adaptive_exec_error'),str(ROOT/'scripts/optimization')]
from generate_flap522 import FrozenCheckpoint,loc,read,sha
from adaptive.structured_flap01 import crop_gated_language
R=ROOT/'deployment/mage_vl4b/optimization_v1/runs'
PREP=R/'M523-M455-L1-vector-protocol-02/RESULT.json'
OUT=R/'M523-M455-L1-vectors-02'
def save(path,v):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as f:f.write((json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode());f.flush();os.fsync(f.fileno())
def binary(path,b):
    with path.open('xb') as f:f.write(b);f.flush();os.fsync(f.fileno())
def digest(b):return hashlib.sha256(b).hexdigest()

def main():
    p=read(PREP)
    for path,h in p['frozen'].items():assert sha(ROOT/path)==h,path
    assert not OUT.exists();OUT.mkdir();started=time.monotonic()
    value=dict(status='FAIL_M455_ADAPTIVE_LOCAL_VECTORS',original_rc=1,source_sha256=sha(__file__),
        full_model_forwards=0,local_MLP_forward_budget=2,training_steps=0,board_actions=0,heldout_opened=0,
        native_A53=False,CSim=False,quality_pass=False,speedup_pass=False,cases=[],variants=[])
    try:
        import torch
        from adaptive.language_mlp_probe import LanguageMLPCandidate,exact_gemm
        from adaptive.language_mlp_kernel_fp1602 import MIN_ROUND_UP_BITS
        assert torch.cuda.is_available();torch.set_num_threads(16);torch.set_num_interop_threads(1)
        torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
        full=R.parent/'candidates/M455-original94-layout-performance-05'
        spec=importlib.util.spec_from_file_location('_m523_adaptive_exact_loader',full/'m455_private_runtime_loader01.py')
        loader=importlib.util.module_from_spec(spec);spec.loader.exec_module(loader)
        factory=loader.load_private(full/'private_runtime',p['private_manifest_sha256'],namespace='_m455_adaptive_vectors52301')
        base,contract=factory['base'],factory['contract'];prepare=factory['runtime_class']._prepare_block
        cap=read(R/'M522-training-capture-02/RESULT.json');protocol=read(R/'M522-training-capture-protocol-03/RESULT.json')
        request=protocol['requests'][0];assert request['id']=='cal_00_t0' and request['role']=='training_only'
        name=request['id']+'/language_01_input.npy';input_path=loc(protocol['data_root'])/name
        assert sha(input_path)==cap['files'][name]['sha256']
        x=np.ascontiguousarray(np.load(input_path,allow_pickle=False)[:32]);assert x.dtype==np.float32 and x.shape==(32,2560) and np.isfinite(x).all()
        binary(OUT/'input_FP32.bin',x.tobytes())
        cp=FrozenCheckpoint(read(R.parent/'contracts/config.json'));weights=[]
        for suffix in ('gate_proj','up_proj','down_proj'):
            pair,bits=cp.packed('model.language_model.layers.1.mlp.'+suffix);assert bits==4;weights.append(pair)
        value.update(input_source_sha256=sha(input_path),input_FP32_sha256=digest(x.tobytes()),
            input_scope='First32 rows of seen BF16+A8 teacher training capture, not exact M455 full-model activation')
        silu_source=ROOT/p['SiLU_source'];assert sha(silu_source)==p['frozen'][p['SiLU_source']]
        nodes=[n for n in ast.parse(silu_source.read_text(encoding='utf-8')).body if isinstance(n,ast.FunctionDef) and n.name=='silu'];assert len(nodes)==1
        namespace={'np':np};exec(compile(ast.fix_missing_locations(ast.Module(body=nodes,type_ignores=[])),str(silu_source),'exec'),namespace)
        silu=namespace['silu']
        def evaluate(chain,values,folder,label):
            folder.mkdir(parents=True);legacy=chain.chain
            convert=factory['modules']['m455_runtime_abi01'].convert_chain
            dense=convert(legacy);initial=base.M120BoardRuntime._initial_scale_shift(values);attempts=[]
            for port,w in enumerate(chain.windows):binary(folder/('weight_port'+str(port)+'.bin'),w)
            binary(folder/'input_FP32.bin',np.ascontiguousarray(values).tobytes())
            selected=None;answer=None
            for shift in range(initial,base.MIN_ACTIVATION_SCALE_SHIFT-1,-1):
                if time.monotonic()-started>600:raise TimeoutError('Finite local vector budget')
                prepared=prepare(dense,values,0,0,shift);packet=prepared.packet
                # Execute only the actual packet produced by the original M238
                # source. No second quantizer supplies the oracle activations.
                count=len(chain.decoded);groups=dense['groups']
                records=np.frombuffer(packet[count*16:],np.uint8).reshape(groups,32,80)
                a=records[:,:,:64].copy().view(np.int8).transpose(1,0,2)
                sa=records[:,:,64:66].copy().view('<f2').reshape(groups,32).T.copy()
                aa=torch.from_numpy(a.copy()).to(chain.device,dtype=torch.float32)
                scales=torch.from_numpy(sa.copy()).to(chain.device);parts=[]
                with exact_gemm(chain.device):
                    for descriptor,(codes,ws) in zip(dense['descriptors'],chain.decoded):
                        dots=torch.bmm(aa.permute(1,0,2).contiguous(),codes.transpose(1,2).contiguous())
                        acc=torch.zeros((32,codes.shape[1]),device=chain.device,dtype=torch.float32)
                        for group in range(groups):
                            term=dots[group]*scales[:,group:group+1].float()
                            term=term*ws[group].float().unsqueeze(0);acc=acc+term
                        acc=acc.cpu().numpy();assert np.isfinite(acc).all()
                        # Preserve hardware overflow as Inf for the original
                        # finite-output retry predicate; never clip or fake PASS.
                        u=np.ascontiguousarray(acc).view(np.uint32)
                        with np.errstate(over='ignore'):bits=acc.astype('<f2').view('<u2').copy()
                        tiny=(u&np.uint32(0x7fffffff))<MIN_ROUND_UP_BITS
                        bits[tiny]=((u[tiny]>>16)&np.uint32(0x8000)).astype(np.uint16)
                        blocks=descriptor['rows_per_shard']//8
                        parts.append(bits.reshape(32,4,blocks,4,2).transpose(2,0,1,3,4).copy().tobytes())
                wire=b''.join(parts);assert len(wire)==dense['output_bytes']
                outputs=contract.parse_chain_output(dense,wire,output_scale_shift=shift)
                finite=base.M120BoardRuntime._written_outputs_finite(dense,outputs)
                attempt=folder/('shift'+str(shift));attempt.mkdir()
                binary(attempt/'packet.bin',packet);binary(attempt/'compact_expected.bin',wire)
                attempts.append(dict(shift=shift,finite=finite,packet_sha256=digest(packet),dense_wire_sha256=digest(wire)))
                value['cases'].append(dict(label=label+'_shift'+str(shift),directory=attempt.relative_to(OUT).as_posix(),
                    weight_directory=folder.relative_to(OUT).as_posix(),contract=dense,shift=shift,finite=finite,
                    input_packet_sha256=digest(packet),compact_golden_sha256=digest(wire)))
                if finite:selected=shift;answer=outputs;break
            assert selected is not None,'Original finite-output policy exhausted'
            for name,array in answer.items():binary(folder/(name+'_FP32.bin'),array.tobytes())
            save(folder/'TRACE.json',dict(initial_shift=initial,selected_shift=selected,attempts=attempts,
                original_M238_prepare_source=True,original_scale_selection_and_finite_predicate=True,
                exact_integer_dot_ordered_FP32_group_oracle=True,CSim=False,native_A53=False))
            return answer,selected,attempts
        for variant in ('original9728','energy9216'):
            if variant=='original9728':current=weights;width=9728
            else:
                method=variant[:-4];removed=p['fixed_maps'][method];keep=np.array(sorted(set(range(152))-set(removed)),np.int64)
                assert len(keep)==144;current=crop_gated_language(weights,keep);width=9216
                ids=(keep[:,None]*64+np.arange(64)[None,:]).reshape(-1)
                assert all(np.array_equal(current[i][0],weights[i][0][ids]) and current[i][1].tobytes()==weights[i][1][ids].tobytes() for i in (0,1))
                assert np.array_equal(current[2][0],weights[2][0][:,keep]) and current[2][1].tobytes()==weights[2][1][:,keep].tobytes()
            model=LanguageMLPCandidate('M523-M455-adaptive-'+variant,current,device='cuda')
            folder=OUT/variant;folder.mkdir()
            gu,sg,ag=evaluate(model.chains[0],x,folder/'gate_up',variant+'_gate_up')
            middle=silu(gu['gate'])*gu['up'];assert middle.dtype==np.float32 and np.isfinite(middle).all()
            down,sd,ad=evaluate(model.chains[1],middle,folder/'down',variant+'_down')
            binary(folder/'R0_FP32.bin',down['down'].tobytes())
            value['variants'].append(dict(variant=variant,width=width,GateUp_selected_shift=sg,Down_selected_shift=sd,
                physical_attempts=len(ag)+len(ad),R0_sha256=digest(down['down'].tobytes()),new_R1_fit=False))
            print('M455_ADAPTIVE_LOCAL_VECTOR',variant,sg,sd,flush=True)
        value.update(status='PASS_SOFTWARE_M455_ADAPTIVE_LOCAL_VECTORS_NOT_CSIM',original_rc=0,
            files={p.relative_to(OUT).as_posix():dict(bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(OUT.rglob('*')) if p.is_file()},
            elapsed_s=time.monotonic()-started,next_step='Actual A53 input/PS packet identity and numerical CSim of every changed packet before own board gate')
    except BaseException:value['errors']=[traceback.format_exc()]
    save(OUT/'RESULT.json',value);print('M455_ADAPTIVE_VECTOR_RESULT',sha(OUT/'RESULT.json'),value['status'],flush=True)
    return value['original_rc']
if __name__=='__main__':raise SystemExit(main())
