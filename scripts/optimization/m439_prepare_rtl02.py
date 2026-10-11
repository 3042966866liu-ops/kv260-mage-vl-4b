"""Actual frozen VIP filename closure, fresh W4 revision02 only."""
import sys,json,re
from m351_workflow import ROOT,BASE,HERE,sha
assert sys.argv[1] in ('baseline_w4','candidate_w4')
s=(HERE/'m439_prepare_rtl.py').read_text(encoding='utf-8')
s=s.replace("'tmp/m439_'+tag+'_01'","'tmp/m439_'+tag+'_02'")
s=s.replace('M439-{tag}-preparation-01','M439-{tag}-preparation-02').replace("'latest_m439_'+tag+'_preparation'","'latest_m439_'+tag+'_preparation02'")
anchor="    (out/'tv/rtldatafile').mkdir(parents=True)"
addition='''    support_map={x['path']:x['sha256'] for x in support_rows}
    for i in range(4):
        p=support/'tv/cdatafile'/(PREFIX+f'autotvin_s{i}.dat')
        assert sha(p)==support_map[p.relative_to(ROOT).as_posix()]
        assert values(p)==[0]
        atomic(out/'tv/cdatafile'/p.name,p.read_bytes(),immutable=True)
    consumed=set()
    for p in (out/'verilog').rglob('*'):
        if p.suffix in ('.v','.sv','.svh','.vh'):
            consumed.update(re.findall(r'"(\.\./tv/(?:cdatafile|stream_size)/[^"\\r\\n]+)"',p.read_text(encoding='utf-8-sig')))
    assert consumed
    for rel in consumed:assert (out/'verilog'/rel).resolve().is_file(),rel
'''
assert s.count(anchor)==1;s=s.replace(anchor,addition+anchor)
ns={'__name__':'m439_prepare_rtl02','__file__':str(HERE/'m439_prepare_rtl02.py')};exec(compile(s,str(HERE/'m439_prepare_rtl02.py')+':fixed-fixture','exec'),ns);ns['main']()
