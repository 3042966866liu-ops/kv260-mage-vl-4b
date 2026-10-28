"""One fixed all-MLP FLAP candidate, exact checkpoint codes, training means.

No model loading, no CUDA, no ratio sweep, no test/development data. Generates
weights only; the complete propagated model must still pass quality gates.
"""
import hashlib
import json
import os
import shutil
import sys
import time
import traceback
from pathlib import Path
import numpy as np

sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'experiments/adaptive_exec_error'),str(ROOT/'deployment/mage_vl4b/scripts')]
from adaptive.structured_flap01 import select_fixed_width,crop_gated_language,crop_vision_mlp
from adaptive.structured_flap_bias02 import removed_mean_bias
from mixed_bit_checkpoint import unpack_unsigned_codes,unpack_orientation_bits
BASE=ROOT/'deployment/mage_vl4b/optimization_v1'
PREP=BASE/'runs/M522-fixed-flap50-protocol-01/RESULT.json'
OUT=BASE/'runs/M522-fixed-flap50-generation-01'


def read(p):return json.loads(Path(p).read_bytes())


def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(8<<20),b''):h.update(b)
    return h.hexdigest()


def loc(n):
    if len(n)>2 and n[1:3]==':/':return Path('/mnt/'+n[0].lower()+'/'+n[3:])
    return ROOT/n


def save(p,v):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('xb') as f:
        f.write((json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode());f.flush();os.fsync(f.fileno())


class FrozenCheckpoint:
    def __init__(self,cfg):
        root=Path(cfg['checkpoint']);manifest=root/'CHECKPOINT_MANIFEST.json'
        assert sha(manifest)==cfg['checkpoint_manifest_sha256']
        self.manifest=read(manifest)
        assert self.manifest['group_size']==64 and self.manifest['scale_format']=='fp16'
        self.entries={r['name']:r for r in self.manifest['entries']}
        self.blob=root/self.manifest['blob']['path']
        assert self.blob.stat().st_size==self.manifest['blob']['bytes']
        self.sections=[]

    def section(self,section):
        with self.blob.open('rb') as f:f.seek(section['offset']);raw=f.read(section['bytes'])
        assert len(raw)==section['bytes'] and hashlib.sha256(raw).hexdigest()==section['sha256']
        self.sections.append(dict(offset=section['offset'],bytes=section['bytes'],sha256=section['sha256']))
        return raw

    def packed(self,module):
        entry=self.entries[module+'.weight'];assert entry['kind']=='packed'
        rows,columns=entry['shape'];assert columns%64==0 and columns==entry['padded_columns']
        bits=entry['bits'];assert bits in (2,3,4)
        sections=entry['sections']
        u=unpack_unsigned_codes(self.section(sections['codes']),bits,rows*columns).reshape(rows,columns//64,64)
        scales=np.frombuffer(self.section(sections['scales']),'<f2').reshape(rows,columns//64).copy()
        orientation=unpack_orientation_bits(self.section(sections['orientations']),rows*columns//64).reshape(rows,columns//64)
        low=np.where(orientation!=0,-(1<<(bits-1))+1,-(1<<(bits-1))).astype(np.int16)
        codes=(u.astype(np.int16)+low[...,None]).astype(np.int8)
        assert np.isfinite(scales).all() and (scales>0).all()
        return (codes,scales),bits

    def bias(self,module):
        entry=self.entries[module+'.bias'];assert entry['kind']=='raw'
        raw=self.section(entry['section'])
        if entry['dtype']=='bfloat16':value=(np.frombuffer(raw,'<u2').astype(np.uint32)<<16).view(np.float32)
        elif entry['dtype']=='float32':value=np.frombuffer(raw,'<f4')
        elif entry['dtype']=='float16':value=np.frombuffer(raw,'<f2').astype(np.float32)
        else:raise ValueError('Unsupported frozen bias dtype')
        return value.reshape(entry['shape']).astype(np.float32).copy()


def verify():
    p=read(PREP)
    for n,h in p['inputs'].items():assert sha(loc(n))==h,n
    cap=read(loc(p['capture_result']))
    assert cap['status']=='PASS_M522_TRAINING_CAPTURE_36_LANGUAGE_24_VISION_MLPS' and cap['original_rc']==0
    assert len(cap['samples'])==8 and len(cap['files'])==1440
    return p,cap


def validate():
    p,cap=verify();checkpoint=FrozenCheckpoint(read(BASE/'contracts/config.json'))
    modules=p['capture_modules'];counts={}
    for key,item in modules.items():
        suffixes=('gate_proj','up_proj','down_proj') if key.startswith('language') else ('fc1','fc2')
        for suffix in suffixes:
            row=checkpoint.entries[item['module']+'.'+suffix+'.weight']
            assert row['kind']=='packed' and row['group_size']==64
            counts[str(row['bits'])]=counts.get(str(row['bits']),0)+1
        for request in p['requests']:
            n=request['id']+'/'+key+'_middle.npy'
            assert cap['files'][n]['shape']==[159 if key.startswith('language') else 392,item['width']]
    # First language layer's real checkpoint sections exercise the actual reader
    # before the full generation, without loading any model or writing weights.
    weights,bits=checkpoint.packed(modules['language_00']['module']+'.down_proj')
    assert weights[0].shape==(2560,152,64) and bits==4
    value=dict(status='PASS_M522_FIXED_FLAP50_GENERATION_INPUTS',protocol_sha256=sha(PREP),
               module_count=len(modules),packed_linear_bits=counts,first_real_Down_shape=list(weights[0].shape),
               first_selected_sections_verified=len(checkpoint.sections),model_loaded=False,board=False)
    save(PREP.parent/'INPUT_PREFLIGHT.json',value);print(value['status'],flush=True)


def run():
    p,cap=verify();assert read(PREP.parent/'INPUT_PREFLIGHT.json')['protocol_sha256']==sha(PREP)
    OUT.mkdir(parents=True,exist_ok=False);started=time.monotonic()
    save(OUT/'START.json',dict(pid=os.getpid(),protocol_sha256=sha(PREP),budget_s=p['budget_s']))
    result=dict(status='FAIL_M522_FIXED_FLAP50_GENERATION',original_rc=1,protocol_sha256=sha(PREP),rows=[],board=False)
    try:
        checkpoint=FrozenCheckpoint(read(BASE/'contracts/config.json'));root=loc(p['data_root']);root.mkdir(parents=True,exist_ok=False)
        captured=loc(p['capture_data_root'])
        for key,item in p['capture_modules'].items():
            if time.monotonic()-started>p['budget_s']:raise TimeoutError('Finite generation budget before next layer')
            if shutil.disk_usage(root).free<p['reserve_bytes']:raise RuntimeError('Storage reserve reached; no deletion')
            print('M522_FLAP_GENERATE_START',key,round(time.monotonic()-started,2),flush=True)
            middle=[]
            for request in p['requests']:
                name=request['id']+'/'+key+'_middle.npy';f=captured/name
                assert sha(f)==cap['files'][name]['sha256']
                middle.append(np.load(f,allow_pickle=False))
            x=np.concatenate(middle);del middle
            language=key.startswith('language');suffixes=('gate_proj','up_proj','down_proj') if language else ('fc1','fc2')
            weights=[];bits=[]
            for suffix in suffixes:
                w,b=checkpoint.packed(item['module']+'.'+suffix);weights.append(w);bits.append(b)
            width=p['widths']['language' if language else 'vision']
            keep,stats=select_fixed_width(weights[-1],x,width)
            if language:
                cropped=crop_gated_language(weights,keep)
                bias=removed_mean_bias(weights[-1],keep,stats['mean'])
                arrays={f'{n}_{s}':a for n,pair in zip(('gate','up','down'),cropped) for s,a in zip(('codes','scales'),pair)}
                arrays['down_bias']=bias
                extra='One explicit FP32 broadcast add after completed Down output; account in full-request timing'
            else:
                b1=checkpoint.bias(item['module']+'.fc1');b2=checkpoint.bias(item['module']+'.fc2')
                cropped=crop_vision_mlp(weights[0],weights[1],b1,b2,keep,stats['mean'])
                arrays={f'{n}_{s}':a for n in ('fc1','fc2') for s,a in zip(('codes','scales'),cropped[n])}
                arrays.update(bias1=cropped['bias1'],bias2=cropped['bias2'])
                extra='Removed-channel mean folded into existing FC2 bias; no additional broadcast add'
            arrays.update(kept_groups=keep,training_mean=stats['mean'],group_scores=stats['group_scores'])
            dest=root/(key+'.npz')
            with dest.open('xb') as f:np.savez(f,**arrays)
            row=dict(key=key,module=item['module'],kind='language' if language else 'vision',
                     original_width=item['width'],width=width,original_bits=bits,kept_original_groups=keep.tolist(),
                     path=p['data_root']+'/'+dest.name,sha256=sha(dest),bytes=dest.stat().st_size,
                     input_rows=len(x),mean_compensation=True,original_retained_codes_and_scales=True,
                     extra_inference_operations=extra)
            save(root/(key+'.json'),row);result['rows'].append(row)
            print('M522_FLAP_GENERATE_DONE',key,round(time.monotonic()-started,2),flush=True)
            del x,weights,arrays,stats,cropped
        assert len(result['rows'])==60 and sum(r['kind']=='language' for r in result['rows'])==36
        result.update(status='PASS_M522_FIXED_FLAP50_MEAN_COMPENSATED_WEIGHTS',original_rc=0,
                      widths=p['widths'],checkpoint_sections=checkpoint.sections,
                      checkpoint_full_blob_rehashed=False,all_selected_sections_sha_verified=True,
                      sources_sha256=p['inputs'],new_quantization=False,ratio_or_layer_search=False,
                      complete_propagated_quality_measured=False,FPGA_performance_measured=False,
                      generated_weight_bytes=sum(r['bytes'] for r in result['rows']))
    except BaseException:
        result['error']=traceback.format_exc();raise
    finally:
        result['elapsed_s']=time.monotonic()-started;save(OUT/'RESULT.json',result);print(result['status'],flush=True)


if __name__=='__main__':
    if sys.argv[1:]==['Validate']:validate()
    elif sys.argv[1:]==['Run']:run()
    else:raise SystemExit('Explicit Validate or Run required')
