"""Actual provider and four bindings over frozen native layers; all DMA fake."""
import ast,copy,hashlib,json,tempfile
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from m423_request_visual import VisualProvider
from m423_saved_features import tensor
from test_m422_borrowed_visual import Buffer
from m422_borrowed_visual import SIZES

def component(root):
    import torch
    from m420_combination import execute
    from m355_reference import full_reference
    source=Path(__file__).with_name('test_m420_combination.py')
    tree=ast.parse(source.read_text());fn=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='component')
    stop=next(i for i,x in enumerate(fn.body) if isinstance(x,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='calls' for t in x.targets))
    setup=copy.deepcopy(fn);setup.name='setup';setup.body=setup.body[:stop]+[ast.Return(value=ast.Call(func=ast.Name(id='locals',ctx=ast.Load()),args=[],keywords=[]))]
    namespace=dict(Path=Path,ast=ast,__future__=__import__('__future__'),json=json,sys=__import__('sys'),threading=__import__('threading'),time=__import__('time'),SimpleNamespace=SimpleNamespace,np=np)
    exec(compile(ast.fix_missing_locations(ast.Module(body=[setup],type_ignores=[])),str(source),'exec'),namespace)
    q=namespace['setup'](root);targets,cases,host,initial,forward=(q[k] for k in ('targets','cases','host','initial','forward'))
    with torch.inference_mode():
        original,_,_=execute(torch,forward,targets,cases,initial,host,'original');software,_,ev=execute(torch,forward,targets,cases,initial,host,'software')
    expected=[tensor(x.float().detach().numpy().reshape(392,64)) for x in (original,software)]
    buffers=[Buffer(n) for n in SIZES];kernel=SimpleNamespace(writes=[],write=lambda r,v:kernel.writes.append((r,v)))
    rt=SimpleNamespace(staged_buffers=buffers[:4],input_buffer=buffers[4],output_buffer=buffers[5],output_buffer_alt=buffers[6],kernel=kernel,_programmed_config=123,_programmed_weight_addresses=(1,2,3,4))
    receive=SimpleNamespace(buffer=None,nbytes=0)
    def rx(b,nbytes):receive.buffer=b;receive.nbytes=nbytes
    rt.dma=SimpleNamespace(recvchannel=SimpleNamespace(transfer=rx),sendchannel=SimpleNamespace(transfer=lambda b,nbytes:None))
    policy=SimpleNamespace(sealed=True,buffer_bytes=list(SIZES),ever=True,completed=True,active=False,build=0x4d333537)
    policy.safe=lambda:not policy.active and policy.completed;policy.capture=lambda *unused:None
    snap=dict(ap_ctrl=4,ap_return=0x4d333537,mm2s_dmasr=4098,s2mm_dmasr=4098,kernel_read_error='',return_read_error='',dma_read_error='')
    c=cases[12]['chains']['fc1'];window_size=len(cases[12]['windows']['fc1'][0]);submitted=[];fail_at=None
    def wait(*unused):
        if fail_at is not None and len(submitted)==fail_at:raise TimeoutError('EXPLICIT second layer active DMA timeout')
        packet=bytes(memoryview(buffers[4])[:c['input_bytes']]);windows=[bytes(memoryview(b)[:window_size]) for b in buffers[:4]]
        raw=full_reference(c,windows,c['stage_base_words'],packet);receive.buffer[:len(raw)]=np.frombuffer(raw,np.uint8);submitted.append(raw);return copy.deepcopy(snap)
    base=SimpleNamespace(REG_POINTERS=(16,28,40,52),REG_CONFIG=64,REG_AP_CTRL=0,physical_address=lambda b:id(b),write_u64=lambda k,r,v:k.write(r,v),wait_transaction=wait)
    reference={(i,part,start,shift):dict(input_bytes=len(packet),output_bytes=len(raw),packet_sha256=hashlib.sha256(packet).hexdigest(),raw_sha256=hashlib.sha256(raw).hexdigest()) for i,rows in ev['software_wire'].items() for (part,start,shift),(packet,raw) in rows.items()}
    with tempfile.TemporaryDirectory() as temp:
        folder=Path(temp);windows={}
        for i in (12,13):
            windows[i]={}
            for part in ('fc1','fc2'):
                rows=[]
                for port,data in enumerate(cases[i]['windows'][part]):
                    name=f'{i}_{part}_{port}';(folder/name).write_bytes(data);rows.append(dict(relative_file=name,file_bytes=len(data),bytes=len(data),offset=0))
                windows[i][part]=rows
        values=dict(pixel_values=np.zeros(1,np.float32),image_grid_thw=np.zeros(1,np.float32),patch_positions=np.zeros(1,np.float32))
        def create():
            provider=VisualProvider.__new__(VisualProvider);r=dict(integrated_visual=[],visual_staging=[],visual_transactions=[],borrowed_extra_DMA=0,vision_forward_calls=0)
            def vision(*unused):
                assert r.get('vision_request_active') is True;r['vision_forward_calls']+=1
                return forward().float().detach().numpy().reshape(392,64)
            provider.engine=SimpleNamespace(vision=vision);provider.runtime=rt;provider.policy=policy;provider.base=base;provider.result=r;provider.sources=dict(visual=dict(preprocessed={k:tensor(v) for k,v in values.items()}))
            provider.targets=targets;provider.torch=torch;provider.host=host;provider.initial=initial;provider.cases={i:cases[i]['chains'] for i in cases};provider.windows=windows;provider.reference=reference;provider.root=folder;provider.frames=np.zeros((4,1,1,3),np.uint8);provider.preprocess=lambda *unused:values;provider.plan=dict(features=[dict(tensor=v) for v in expected]);provider.current_owner=None;provider.disposed=False
            return provider
        provider=create()
        with torch.inference_mode():
            assert tensor(provider(0))==expected[0]
            # Simulate original language having left a cached configuration.
            rt._programmed_config=0x11223344
            assert tensor(provider(1))==expected[1]
        assert len(submitted)==52 and len(provider.result['visual_transactions'])==52 and rt._programmed_config is None and rt._programmed_weight_addresses is None and provider.current_owner is None
        assert all('forward' not in getattr(targets[i].mlp,k).__dict__ for i in (12,13) for k in ('fc1','fc2'))
        provider.dispose();assert provider.disposed and provider.targets is None
        submitted.clear();fail_at=26;bad=create();bad.result['integrated_visual']=[expected[0]]
        with torch.inference_mode():
            try:bad(1)
            except TimeoutError:pass
            else:raise AssertionError('Active second-layer timeout not propagated')
        assert policy.active and bad.current_owner is not None and bad.current_owner.retained
        assert all('forward' not in getattr(targets[i].mlp,k).__dict__ for i in (12,13) for k in ('fc1','fc2'))
        try:bad.dispose()
        except RuntimeError:pass
        else:raise AssertionError('Unsafe original owner disposed')
    return dict(actual_provider_forward=True,frozen_native24_wrappers_M207=True,synthetic64_wide_weights_attention=True,fake_DMA_MMIO_memory=True,real_original_buffer_geometry_bytes=sum(SIZES),complete52_packets_wires_and_features_exact=True,static_cache_invalidated=True,second_layer_timeout_retains_owner_and_restores_bindings=True,successful_provider_disposal=True,no_actual_board_or_capacity=True)

if __name__=='__main__':
    import sys
    print('M423_PROVIDER_COMPONENT='+json.dumps(component(Path(sys.argv[1])),sort_keys=True))
