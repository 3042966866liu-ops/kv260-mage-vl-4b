"""Preserve preparation rejection; no board work or overwrite of partial01."""
from m351_workflow import BASE,HERE,sha,atomic,encoded
p=BASE/'candidates/M385-ps-layer-01'
r=dict(status='REJECTED_OFFLINE_MISSING_LAYER_BINDER',missing=['m343_layer_scope'],board_run=False,overlay_loaded=False,files=[dict(path=f.name,sha256=sha(f)) for f in sorted(p.iterdir())],next_candidate='M385-ps-layer-02',reason='Recursive dependency check refused incomplete layer binder before packaging; old partial staging retained')
out=BASE/'runs/M385-offline-rejection-01/RESULT.json';atomic(out,encoded(r),immutable=True);print(sha(out))
