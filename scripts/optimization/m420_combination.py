"""Only layers12+13 MLP instance overrides; exact oracle follows changed input."""
from contextlib import ExitStack
import hashlib

SELECTED=(12,13)

def execute(torch,vision_call,targets,cases,initial,host,mode,*,stage=None,submit=None,expected=None):
    from m408_mlp_capture04 import Capture
    from m409_ftz_reference import SoftwareMLPBinding
    from m411_mlp_binding import PLMLPBinding
    if tuple(sorted(targets))!=SELECTED or tuple(sorted(cases))!=SELECTED or mode not in ('original','software','PL'):
        raise ValueError('Only fixed original or12+13 combination')
    if mode=='PL' and (stage is None or submit is None or set(expected or {})!={12,13}):
        raise ValueError('Both dynamic software references required before PL')
    bindings={};captures={};wire={i:{} for i in SELECTED};identities={};shapes=None
    try:
        with ExitStack() as stack:
            for index in SELECTED:
                layer=targets[index];mlp=layer.mlp
                if mode=='software':
                    def sink(part,start,shift,packet,raw,index=index):
                        key=(part,start,shift)
                        if key in wire[index]:raise RuntimeError('Duplicate software batch')
                        wire[index][key]=(packet,raw)
                    binding=SoftwareMLPBinding(torch,mlp,cases[index]['chains'],cases[index]['windows'],initial,host.pack_chain_input,host.parse_chain_output,sink)
                    bindings[index]=stack.enter_context(binding)
                elif mode=='PL':
                    binding=PLMLPBinding(torch,mlp,cases[index]['chains'],initial,host,
                        lambda part,c,index=index:stage(index,part,c),
                        lambda part,c,start,shift,packet,index=index:submit(index,part,c,start,shift,packet),expected[index])
                    bindings[index]=stack.enter_context(binding)
                # The component can provide64-wide shapes; board defaults are the real1024/4096 contract.
                shapes=cases[index].get('capture_shapes')
                kwargs={} if shapes is None else dict(shapes=shapes)
                captures[index]=stack.enter_context(Capture(mlp,norm=layer.layer_norm2,**kwargs))
            answer=vision_call()
        for index,capture in captures.items():capture.require_complete()
        if not all(c.restored for c in captures.values()) or not all(b.restored for b in bindings.values()):
            raise RuntimeError('Combination overrides/hooks not restored')
        for index,binding in bindings.items():
            if binding.calls!={'fc1':1,'fc2':1}:raise RuntimeError('Each selected MLP must execute exactly once')
        if mode=='software':
            for index in SELECTED:
                if len(wire[index])!=26:raise RuntimeError('Full26 software batches required per selected layer')
                identities[str(index)]=[dict(part=part,start=start,shift=shift,input_bytes=len(packet),output_bytes=len(raw),packet_sha256=hashlib.sha256(packet).hexdigest(),raw_sha256=hashlib.sha256(raw).hexdigest()) for (part,start,shift),(packet,raw) in wire[index].items()]
        return answer,{i:c.values for i,c in captures.items()},dict(bindings_restored=True,captures_restored=True,
            batches={str(i):b.batches for i,b in bindings.items()},software_wire=wire,software_wire_identities=identities)
    finally:
        # ExitStack closes previously entered bindings even when the second binding/forward fails.
        if any(c.handles for c in captures.values()) or any(b.previous for b in bindings.values()):
            raise RuntimeError('Combination context retained active hooks/overrides')
