"""Saved-only fresh W4 paths; presence required before aggregate checks."""
from m351_workflow import HERE
s=(HERE/'m439_collect_rtl.py').read_text(encoding='utf-8')
s=s.replace("'tmp/m439_'+tag+'_01'","'tmp/m439_'+tag+'_02'").replace('M439-{tag}-preparation-01','M439-{tag}-preparation-02').replace('M439-{tag}-{mode}-01','M439-{tag}-{mode}-02')
s=s.replace("'latest_m439_'+tag+'_'+mode","'latest_m439_'+tag+'_'+mode+'02'")
s=s.replace("checks['MAC_operations']=all(","checks['MAC_operations']=len(metrics)==4 and all(").replace("checks['read_protocol']=all(","checks['read_protocol']=len(metrics)==4 and all(")
ns={'__name__':'m439_collect_rtl02','__file__':str(HERE/'m439_collect_rtl02.py')};exec(compile(s,str(HERE/'m439_collect_rtl02.py')+':saved-only','exec'),ns);ns['main']()
