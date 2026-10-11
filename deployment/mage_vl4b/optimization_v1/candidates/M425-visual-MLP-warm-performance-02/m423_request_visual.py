"""Actual fixed input visual provider, original or12+13, borrowed DMA only."""
from contextlib import ExitStack
import hashlib,json,sys
from pathlib import Path
import numpy as np

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def verify_sources(plan):
    # Full saved-source checks run before Overlay or any buffer allocation.
    result={}
    for name,entry in plan['integrated_sources'].items():
        path=Path(entry['path']);raw=path.read_bytes()
        if path.is_symlink() or hashlib.sha256(raw).hexdigest()!=entry['sha256']:raise RuntimeError('Integrated prerequisite SHA differs')
        r=json.loads(raw)
        if r['status']!=entry['status'] or type(r['gate_return_code']) is not int or r['gate_return_code']!=0 or r['errors'] or r['safe_buffers_released'] is not True:raise RuntimeError('Integrated prerequisite scope/owner differs')
        if name=='visual':
            if r['selected_layers']!=[12,13] or r['stable_restored'] is not True or r['software_PL_complete_features_exact'] is not True:raise RuntimeError('Combined visual evidence differs')
        elif name=='language':
            if r['selected_layers']!=[12,13] or r['stable_overlay_reloaded'] is not True or r['original_reference_pass'] is not True or r['decision_consistency_pass'] is not True or r['vision_forward_calls']!=0:raise RuntimeError('Saved language evidence differs')
        else:raise RuntimeError('Unknown prerequisite role')
        result[name]=r
    if set(result)!={'visual','language'}:raise RuntimeError('Both complete prerequisites required')
    for row in plan['visual_reused_packages']:
        folder=Path(row['directory'])
        if digest(folder/'PACKAGE_MANIFEST.json')!=row['manifest_sha256']:raise RuntimeError('Visual package manifest differs')
        manifest=json.loads((folder/'PACKAGE_MANIFEST.json').read_bytes())
        for entry in manifest['files']:
            p=folder/entry['path']
            if p.is_symlink() or p.stat().st_size!=entry['bytes'] or digest(p)!=entry['sha256']:raise RuntimeError('Visual support payload differs')
    return result

class VisualProvider:
    def __init__(self,engine,runtime,policy,base,here,result,sources):
        self.engine,self.runtime,self.policy,self.base,self.result=engine,runtime,policy,base,result
        self.sources=sources;self.current_owner=None;self.disposed=False
        plan=json.loads((here/'PLAN.json').read_bytes());self.plan=plan
        # These exact support paths were checked before resources.
        sys.path[1:1]=[x['directory'] for x in plan['visual_reused_packages']]
        import torch
        from frozen_video_identity import RELEASE,FRAMES,ADDON,STACK_SHA
        from m273_latest_multiscale_contract import preprocess
        from m206_ps_vision_runtime import M206ProgressLayer
        from ps_vision_runtime import M196PrecisionBoundary
        from m207_ps_vision_runtime import M207FP32GemmW4Linear
        from m408_target03 import resolve_target as target12,verify_matrices as matrices12
        from m416_target13 import resolve_target as target13,verify_matrices as matrices13
        from m410_saved_case import load_case as load12
        from m418_saved_case import load_case as load13
        from test_m409_ftz_reference import actual_host
        self.torch=torch;self.root=RELEASE;self.host,self.initial=actual_host(RELEASE)
        self.targets={};self.cases={};self.windows={}
        for i,resolver,verify,loader in ((12,target12,matrices12,load12),(13,target13,matrices13,load13)):
            layer,topology=resolver(engine.vision.vision,M206ProgressLayer,M196PrecisionBoundary,torch)
            if topology!=sources['visual']['target_resolution'][str(i)] or verify(layer,M207FP32GemmW4Linear,torch)!=sources['visual']['target_matrices'][str(i)]:raise RuntimeError('Actual complete-runtime visual target differs')
            self.targets[i]=layer
            spec=json.loads((Path(plan['lower_packages'][str(i)])/'BOARD_CASES.json').read_bytes());chains={};windows={}
            for mode in ('Chain','Descriptor'):
                c,_,_,w,_=loader(spec,mode,RELEASE,self.host);part=spec['cases'][mode]['part'];chains[part]=c;windows[part]=spec['cases'][mode]['windows']
            self.cases[i]=chains;self.windows[i]=windows
        frames=[]
        for name,expected in FRAMES.items():
            p=ADDON/'fixtures'/name
            if digest(p)!=expected:raise RuntimeError('Fixed frame SHA differs')
            frames.append(np.load(p,allow_pickle=False))
        frames=np.ascontiguousarray(np.stack(frames))
        if frames.shape!=(4,448,448,3) or frames.dtype!=np.uint8 or hashlib.sha256(frames.tobytes()).hexdigest()!=STACK_SHA:raise RuntimeError('Ordered source frame stack differs')
        self.frames=frames;self.preprocess=preprocess
        self.reference={}
        for index,rows in sources['visual']['software_wire_identities'].items():
            for row in rows:self.reference[(int(index),row['part'],row['start'],row['shift'])]=row
        if len(self.reference)!=52:raise RuntimeError('All52 saved combined wire identities required')
        result['visual_staging']=[];result['integrated_visual']=[];result['visual_transactions']=[];result['borrowed_extra_DMA']=0
    def __call__(self,index):
        from m411_mlp_binding import PLMLPBinding
        from m422_borrowed_visual import BorrowedVisual
        from m423_saved_features import tensor
        if index not in (0,1) or len(self.result['integrated_visual'])!=index or self.result.get('language_scope_active',False):raise RuntimeError('Two sequential fixed requests only')
        print('M423_VISUAL_BEGIN '+('original' if index==0 else 'layer12_13_candidate'),flush=True)
        self.policy.capture('before-integrated-visual:'+str(index),True)
        tensors=self.preprocess(np.ascontiguousarray(self.frames[-1:]))
        if {k:tensor(v) for k,v in sorted(tensors.items())}!=self.sources['visual']['preprocessed']:raise RuntimeError('Fixed preprocess differs')
        bindings={};owner=None
        try:
            with ExitStack() as stack:
                if index==1:
                    owner=stack.enter_context(BorrowedVisual(self.runtime,self.policy,self.base,self.result,enabled=True,numerical_reference=self.reference,language_active=lambda:self.result.get('language_scope_active',False)));self.current_owner=owner
                    for layer in (12,13):
                        stage=lambda part,c,layer=layer:owner.stage(layer,part,c,self.windows[layer][part],self.root)
                        submit=lambda part,c,start,shift,packet,layer=layer:owner.submit(layer,part,c,start,shift,packet)
                        bindings[layer]=stack.enter_context(PLMLPBinding(self.torch,self.targets[layer].mlp,self.cases[layer],self.initial,self.host,stage,submit))
                self.result['vision_request_active']=True
                try:visual=self.engine.vision(tensors['pixel_values'],tensors['image_grid_thw'],tensors['patch_positions'])
                finally:self.result['vision_request_active']=False
            if any(not binding.restored or binding.calls!={'fc1':1,'fc2':1} for binding in bindings.values()):raise RuntimeError('All four Linear instance forwards must restore')
            if owner is not None:
                if owner.retained or owner.entered or len(owner.rows)!=52 or len(owner.staging)!=4:raise RuntimeError('Borrowed transaction/ownership closure incomplete')
                self.result['visual_staging']=owner.staging;self.result['borrowed_buffer_identity_preserved']=True;self.result['visual_static_cache_invalidated']=self.runtime._programmed_config is None and self.runtime._programmed_weight_addresses is None
            expected=self.plan['features'][index]['tensor']
            if tensor(visual)!=expected:raise RuntimeError('Integrated complete visual feature differs from saved original/candidate')
            self.result['integrated_visual'].append(tensor(visual));self.policy.capture('after-integrated-visual:'+str(index),True)
            self.current_owner=None
            print('M423_VISUAL_EXACT_PASS '+str(index),flush=True)
            return visual
        finally:
            # Unsafe owner remains referenced by this provider and original engine.
            if owner is not None and (owner.retained or self.policy.active):self.current_owner=owner
    def dispose(self):
        if self.current_owner is not None or self.result.get('language_scope_active',False):raise RuntimeError('Cannot dispose active borrowed owner')
        self.engine=self.runtime=self.policy=self.base=self.targets=self.frames=self.cases=self.windows=self.sources=self.reference=self.host=None
        self.disposed=True;self.result['visual_provider_disposed']=True
