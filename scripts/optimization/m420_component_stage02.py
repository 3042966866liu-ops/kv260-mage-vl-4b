"""Close the component's explicit same-SHA PL binding dependency."""
from m351_workflow import ROOT,BASE,HERE,atomic,sha
def main():
    old=ROOT/'tmp/m42001/component_stage';stage=ROOT/'tmp/m42002/component_stage';stage.mkdir(parents=True,exist_ok=True)
    for name in ('m420_combination.py','test_m420_combination.py'):atomic(stage/name,(old/name).read_bytes(),immutable=True)
    binding=BASE/'candidates/M419-layer13-complete-MLP-03/m411_mlp_binding.py'
    assert sha(binding)=='275e85583abc6c1ecfc2f14d59341207f2d2184a5a00bb4f838898f215ec29f5'
    atomic(stage/binding.name,binding.read_bytes(),immutable=True)
    s=(old/'check.py').read_text(encoding='utf-8').replace('tmp/m42001','tmp/m42002')
    atomic(stage/'check.py',s.encode('utf-8'),immutable=True)
    print('M420_COMPONENT_STAGE02_CLOSED')
if __name__=='__main__':main()
