"""Exercise actual nested load function with fake preflight/MMIO only."""
import ast,json,sys,types
from unittest.mock import patch
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
p=HERE/'m439_board_probe.py'
tree=ast.parse(p.read_text(encoding='utf-8'))
main=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
load=next(n for n in main.body if isinstance(n,ast.FunctionDef) and n.name=='load')
class MakeGlobal(ast.NodeTransformer):
    def visit_Nonlocal(self,node):return ast.copy_location(ast.Global(names=node.names),node)
load=MakeGlobal().visit(load)
code=compile(ast.fix_missing_locations(ast.Module(body=[load],type_ignores=[])),str(p)+':fake-selection','exec')
ns=dict(active=False,buffers=[],STABLE=ROOT/'fake-stable',HERE=ROOT/'fake-candidate',STABLE_SHA='stable-manifest',args=types.SimpleNamespace(manifest_sha='candidate-manifest'),directory=ROOT/'tmp/m439_fake_env_never_written',result=dict(overlay_loads=[]),phase=['fake'],OLD_BUILD=0x4d333537,NEW_BUILD=0x4d343339,RESTORE_BUILD=0x4d395832,KERNEL_NAME='kernel',DMA_NAME='dma',sha256=lambda path:'fake-hash',sys=sys)
calls=[]
def preflight(argv,**kwargs):calls.append(dict(argv=argv,kwargs=kwargs));return types.SimpleNamespace(returncode=0)
ns['subprocess']=types.SimpleNamespace(run=preflight)
fake=types.ModuleType('pynq');bits=[]
class Overlay:
    def __init__(self,bit,download):bits.append(bit);self.kernel=object();self.dma=object();assert download
fake.Overlay=Overlay;fake.Clocks=types.SimpleNamespace(**{'fclk'+str(i)+'_mhz':200.0 for i in range(4)})
with patch.dict(sys.modules,pynq=fake):
    exec(code,ns)
    for v,b in [('A',0x4d333537),('B',0x4d343339),('R',0x4d395832)]:
        ns['load'](v,'fake-'+v);assert ns['expected_build']==b
    assert '/baseline/overlay/' in bits[0].replace('\\','/')
    assert bits[1].endswith('overlay\\m120_m89x2_t32.bit') or bits[1].endswith('overlay/m120_m89x2_t32.bit')
    assert 'fake-stable' not in bits[0] and 'fake-stable' not in bits[1] and 'fake-stable' in bits[2]
    assert calls[0]['argv'][calls[0]['argv'].index('--candidate')+1]==str(ns['HERE'])
    assert calls[0]['argv'][calls[0]['argv'].index('--expected-package-manifest-sha256')+1]=='candidate-manifest'
    assert calls[2]['argv'][calls[2]['argv'].index('--expected-package-manifest-sha256')+1]=='stable-manifest'
    ns['active']=True
    try:ns['load']('B','active-rejected')
    except RuntimeError:pass
    else:raise AssertionError('Active Overlay swap permitted')
    assert len(calls)==3 and len(bits)==3
r=dict(status='PASS_M439_ACTUAL_OVERLAY_SELECTION_FAKE_ONLY',build_id='0x4D343339',probe_sha256=sha(p),collector_sha256=sha(HERE/'m439_board_collection.py'),packager_sha256=sha(HERE/'m439_prepare_board_package.py'),selection=[dict(variant=v,bit=bit,expected_build=hex(b)) for (v,b),bit in zip([('A',0x4d333537),('B',0x4d343339),('R',0x4d395832)],bits)],checks=['A exact packaged M357 path/Build','B packaged M439 path/Build','R original stable restore path/Build','Same package preflight A/B; stable manifest R','Active transaction rejects swap before preflight'],actual_device=False,board=False,no_real_preflight_or_overlay=True)
p=BASE/'runs/M439-overlay-selection-checks-01/RESULT.json';atomic(p,encoded(r),immutable=True)
sync('latest_m439_overlay_selection_checks',dict(status=r['status'],result=p.relative_to(ROOT).as_posix(),sha256=sha(p),build_id=r['build_id'],board=False),'## M439 A/B/恢复选择核对（2026-10-07）\n\nSHA '+sha(p)+'；执行实际新load函数的fake环境测试：A只选精确同包M357、B新M439、R原稳定恢复，对应manifest/Build严格，活动事务在preflight前拒绝换Overlay。0真实环境preflight/Overlay/板端；防止误用旧M9作本次增量性能A。')
print(r['status'],sha(p))
