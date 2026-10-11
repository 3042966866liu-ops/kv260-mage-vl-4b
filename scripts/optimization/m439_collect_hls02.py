"""Versioned saved-only collector for independent02 paths."""
from m351_workflow import HERE
s=(HERE/'m439_collect_hls.py').read_text(encoding='utf-8')
s=s.replace('tmp/m439_record_load_01','tmp/m439_record_load_02').replace('tmp/m439_hls_project_01','tmp/m439_hls_project_02')
s=s.replace('M439-record-load-{tag}-01','M439-record-load-{tag}-02').replace('M439-record-load-preparation-01','M439-record-load-preparation-02').replace('M439-record-load-csim-01','M439-record-load-csim-02')
s=s.replace("'latest_m439_record_load_'+tag","'latest_m439_record_load_'+tag+'02'")
ns={'__name__':'m439_collector02','__file__':str(HERE/'m439_collect_hls02.py')}
exec(compile(s,str(HERE/'m439_collect_hls02.py')+':saved-only','exec'),ns)
ns['main']()
