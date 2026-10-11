"""Saved-only OOC preparation02 identity, unchanged result validation."""
from m351_workflow import HERE
s=(HERE/'m439_collect_ooc.py').read_text(encoding='utf-8').replace('M439-record-load-core-OOC-preparation-01','M439-record-load-core-OOC-preparation-02')
ns={'__name__':'m439_collect_ooc02','__file__':str(HERE/'m439_collect_ooc02.py')};exec(compile(s,str(HERE/'m439_collect_ooc02.py')+':saved-only','exec'),ns);ns['main']()
