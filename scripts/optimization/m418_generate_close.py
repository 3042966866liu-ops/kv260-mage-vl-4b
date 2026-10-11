"""Generate saved-only closure for the two layer13 lower gates."""
from m351_workflow import HERE,atomic
s=(HERE/'m410_close.py').read_text(encoding='utf-8').replace('M410','M418').replace('m410','m418').replace('M409','M417').replace('第12层','第13层')
atomic(HERE/'m418_close.py',s.encode('utf-8'),immutable=True)
print('M418_CLOSURE_READY')
