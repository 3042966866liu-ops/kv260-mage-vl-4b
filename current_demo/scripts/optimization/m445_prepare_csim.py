"""Prepare real-input candidate numerical fixtures for the unchanged M443 DUT."""
import json,sys,struct,hashlib
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent))
import m445_compare as q
import torch,numpy as np
ROOT=q.ROOT
BASE=ROOT/'deployment/mage_vl4b/optimization_v1'
OUT=ROOT/'tmp/m445_csim_01'
RUNTIME=ROOT/'release_staging/kv260-mage-vl-4b-prebuilt-install-20260926-v7/deployment/mage_vl4b/m175_m120_fixed_text_candidate/runtime'
sys.path.insert(0,str(RUNTIME))
from contract_runtime import pack_chain_input,parse_chain_output
from m355_reference import full_reference

def records(c,s):
    rows,groups,_=c.shape;assert rows%8==0
    pos=(c.max(-1)==8);qmin=np.where(pos,-7,-8)
    codes=(c-qmin[:,:,None]).astype(np.uint8)
    assert codes.max()<=15
    packed=(codes[:,:,::2]|(codes[:,:,1::2]<<4)).reshape(rows//8,8,groups,32).transpose(2,0,1,3).copy()
    tags=(s.view('<u2')|np.where(pos,0x8000,0).astype('<u2')).reshape(rows//8,8,groups).transpose(2,0,1).copy()
    raw=np.zeros((groups,rows//8,17,16),np.uint8)
    raw[:,:,0]=tags.view(np.uint8).reshape(groups,rows//8,16)
    raw[:,:,1:]=packed.reshape(groups,rows//8,16,16)
    return raw.tobytes()
def make_chain(modules,groups):
    windows=[bytearray() for _ in range(4)];descriptors=[];offset=0;index=0
    for name,c,s in modules:
        for start in range(0,len(c),2048):
            size=min(2048,len(c)-start);assert size%32==0
            rows=size//4;bytecount=groups*(rows//8)*272
            desc=dict(descriptor_index=index,module=name,row_start=start,valid_rows=size,rows_per_shard=rows,
                      bits=4,offset_words=offset,encoded_u64=hex(offset|(rows<<32)|(4<<42)),
                      record_bytes_per_shard=bytecount,output_bytes=size*32*4)
            for shard in range(4):
                a=start+shard*rows;b=a+rows;raw=records(c[a:b],s[a:b]);assert len(raw)==bytecount;windows[shard].extend(raw)
            descriptors.append(desc);offset+=bytecount//16;index+=1
    total=sum(d['output_bytes'] for d in descriptors)
    chain=dict(groups=groups,bits=4,descriptor_count=len(descriptors),config_u32=hex(groups|(4<<8)|(len(descriptors)<<16)),
               descriptors=descriptors,input_bytes=len(descriptors)*16+groups*32*80,output_bytes=total)
    return chain,[bytes(w) for w in windows]
def main():
    OUT.mkdir(parents=True,exist_ok=False)
    pr=BASE/'runs/M445-new-dataset-MLP-comparison-01/RESULT.json'
    assert q.sha(pr)=='be62117b4f3b3e22d0164e30e1a0c5e224f8fd6adb42514a749981f6b49c505c'
    prior=json.loads(pr.read_text(encoding='utf-8'));sel=prior['selected_for_further_numerical_validation']
    assert sel['method']=='G64_intermediate_compression' and sel['kept_groups']==151 and sel['screen_pass']
    caproot=BASE/'runs/M445-new-dataset-input-capture-01';cap=json.loads((caproot/'RESULT.json').read_text(encoding='utf-8'))
    sample=next(s for s in cap['samples'] if s['sample']['modality']=='SAR' and s['sample']['role']=='evaluation')
    inp=caproot/sample['input_file'];assert q.sha(inp)==sample['input_file_sha256']
    x=np.load(inp,allow_pickle=False)[-32:].copy();assert x.shape==(32,2560)
    torch.backends.cuda.matmul.allow_tf32=False
    cases=[];variants={}
    for label,npz in [('A',BASE/'runs/M445-G64-MLP-screen-01/groups_152.npz'),('B',pr.parent/'groups_151.npz')]:
        with np.load(npz,allow_pickle=False) as a:
            raw=[(a[s+'_codes'].copy(),a[s+'_scales'].copy()) for s in ('gate','up','down')]
        w=[(torch.from_numpy(c).cuda().float(),torch.from_numpy(s).cuda()) for c,s in raw]
        y,g,u=q.mlp(torch.from_numpy(x).cuda(),w)
        gn=g.cpu().numpy();un=u.cpu().numpy();down=(gn/(np.float32(1)+np.exp(-gn,dtype=np.float32)))*un
        gu,gwin=make_chain([('gate',*raw[0]),('up',*raw[1])],40)
        dc,dwin=make_chain([('down',*raw[2])],raw[2][0].shape[1])
        vv={}
        for fam,chain,windows,inputx,expected in [('gate_up',gu,gwin,x,{'gate':gn,'up':un}),('down',dc,dwin,down,{'down':y.cpu().numpy()})]:
            packet=pack_chain_input(chain,inputx);golden=full_reference(chain,windows,0,packet)
            parsed=parse_chain_output(chain,golden)
            assert set(parsed)==set(expected) and all(np.array_equal(parsed[k],expected[k]) for k in expected)
            name=label+'_'+fam;dest=OUT/name;dest.mkdir()
            for i,b in enumerate(windows):(dest/f'w{i}.bin').write_bytes(b)
            (dest/'packet.bin').write_bytes(packet);(dest/'golden.bin').write_bytes(golden)
            (dest/'input.bin').write_bytes(inputx.astype('<f4').tobytes())
            fixture=b'M441FUL1'+struct.pack('<5I',int(chain['config_u32'],16),len(chain['descriptors']),len(packet),len(golden),len(windows[0]))+packet+b''.join(windows)+golden
            (dest/'fixture.bin').write_bytes(fixture)
            vv[fam]=dict(chain=chain,files={p.name:dict(sha256=q.sha(p),bytes=p.stat().st_size) for p in dest.iterdir()},path=name)
            if (label,fam) in [('B','gate_up'),('B','down'),('A','gate_up')]:cases.append((label,fam,dest/'fixture.bin'))
        variants[label]=vv
    # The unchanged sealed vendor-generated CSim executable checks three cases,
    # every word, keep/strb/final TLAST, build return and both stream consumptions.
    by={(a,b):p for a,b,p in cases}
    for i,key in enumerate([('B','gate_up'),('B','down'),('A','gate_up')]):(OUT/f'case{i}.bin').write_bytes(by[key].read_bytes())
    exe=ROOT/'tmp/m443_full_csim_project_03/hls/csim/build/csim.exe'
    original=BASE/'runs/M443-full-numeric-preparation-03/RESULT.json';orig=json.loads(original.read_text(encoding='utf-8'))
    for row in orig['files']:
        if '/source/' in row['path'] or row['path'].endswith('m443_full_chain_tb.cpp'):assert q.sha(ROOT/row['path'])==row['sha256']
    prerequisites={}
    for name in ('HARDWARE_CLOSURE.json','DEPENDENCY_CLOSURE.json'):
        p=BASE/'candidates/M443-pair-pipeline-01'/name;prerequisites[name]=dict(sha256=q.sha(p),content=json.loads(p.read_text(encoding='utf-8')))
    assert prerequisites['DEPENDENCY_CLOSURE.json']['content']['status']=='PASS_RECURSIVE_FROZEN_DEPENDENCY_CLOSURE'
    r=dict(status='PREPARED_M445_REAL_DATA_G64_NUMERICAL_CSIM',build_id='0x4D343433',DUT_modified=False,
           comparison_sha256=q.sha(pr),selected_width=9664,selected_sample=sample,token_slice='last 32 of 226 genuine single-image tokens',
           original_testbench_sha256=q.sha(ROOT/'tmp/m443_full_numeric_03/m443_full_chain_tb.cpp'),
           original_source_preparation_sha256=q.sha(original),executable_path=exe.relative_to(ROOT).as_posix(),executable_sha256=q.sha(exe),
           fixture_order=[dict(ordinal=i,variant=a,family=b,output_words=variants[a][b]['chain']['output_bytes']//8) for i,(a,b) in enumerate([('B','gate_up'),('B','down'),('A','gate_up')])],
           variants=variants,prerequisites=prerequisites,CPU_int32_full_outputs_match_GPU_proxy=True,board=False,performance_pass=False,
           files=[dict(path=p.relative_to(ROOT).as_posix(),sha256=q.sha(p),bytes=p.stat().st_size) for p in sorted(OUT.rglob('*')) if p.is_file()])
    q.save(OUT/'PREPARATION.json',r);print(r['status'],q.sha(OUT/'PREPARATION.json'),flush=True)
if __name__=='__main__':main()
