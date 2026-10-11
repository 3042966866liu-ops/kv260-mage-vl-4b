"""Create isolated shape-fix sources; never modify frozen packages."""
from m351_workflow import HERE,atomic

def change(text,old,new,count=1):
    assert text.count(old)==count,(old,text.count(old),count)
    return text.replace(old,new)

capture=(HERE/'m408_mlp_capture.py').read_text(encoding='utf-8')
capture=change(capture,"    x = value.detach().cpu().numpy()\n", "    x = value.detach().cpu().numpy()\n    if x.ndim == 3 and x.shape[0] == 1: x = x[0]\n")
capture=change(capture,"raise ValueError('Original finite FP32 matrix required')", "raise ValueError('Original finite FP32 matrix or single-batch matrix required: shape='+str(tuple(value.shape))+', dtype='+str(value.dtype))")
capture=change(capture,"self.values, self.counts, self.handles = {}, {}, []", "self.values, self.counts, self.handles = {}, {}, []\n        self.native_shapes = {}")
capture=change(capture,"        x = array(value)\n", "        self.native_shapes[key] = list(value.shape)\n        x = array(value)\n")
atomic(HERE/'m408_mlp_capture04.py',capture.encode('utf-8'),immutable=True)
component=(HERE/'m408_target_component03.py').read_text(encoding='utf-8')
component=change(component,'from m408_mlp_capture import Capture','from m408_mlp_capture04 import Capture')
component=change(component,'reshape(3,64)*.013','reshape(1,3,64)*.013')
component=change(component,"torch.from_numpy(capture.values['residual']+capture.values['output']).to(torch.bfloat16)","torch.from_numpy(capture.values['residual']+capture.values['output']).unsqueeze(0).to(torch.bfloat16)")
component=change(component,"    rejects=0\n", "    assert all(v == [1,*shapes[k]] for k,v in capture.native_shapes.items())\n    bad_shapes_rejected = 0\n    from m408_mlp_capture04 import array\n    for bad in (torch.ones(2,3,64),torch.ones(1,1,3,64),torch.ones(3,64,dtype=torch.float64),torch.full((1,3,64),float('nan'))):\n        try: array(bad)\n        except ValueError: bad_shapes_rejected += 1\n        else: raise AssertionError('Non-contract matrix accepted')\n    rejects=0\n")
component=change(component,"                topology_rejects=rejects,topology=evidence", "                native_single_batch_preserved=True,bad_shapes_rejected=bad_shapes_rejected,topology_rejects=rejects,topology=evidence")
atomic(HERE/'m408_target_component04.py',component.encode('utf-8'),immutable=True)
basic=(HERE/'m408_component.py').read_text(encoding='utf-8')
basic=basic.replace('from m408_mlp_capture import','from m408_mlp_capture04 import')
assert basic!=(HERE/'m408_component.py').read_text(encoding='utf-8')
atomic(HERE/'m408_component04.py',basic.encode('utf-8'),immutable=True)
print('M408_SHAPE_FIX_SOURCES_CREATED')
