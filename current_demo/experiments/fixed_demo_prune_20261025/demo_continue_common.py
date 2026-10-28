from demo_common import *
PREP=R/(PREFIX+'-protocol-02');OUT=R/(PREFIX+'-search-02')
def verify():
    p=read(PREP/'RESULT.json')
    for path,h in p['frozen'].items():assert sha(ROOT/path)==h,path
    return p
