"""Close host-only scope-label and strict dependency changes; keep frozen package."""
import ast
import json
from m351_workflow import ROOT,HERE,BASE,sha,atomic,encoded,sync
from m401_collect import BASE_DECODE,PKG,PROOF
from m400_support import export

def main():
    original=BASE/'runs/M401-tail-text-support-01/RESULT.json'
    assert sha(original)=='251adb1d48ae6c5983849f02521d56be6421d6a82c01b4b892557e7647a7b5f9'
    value=json.loads(original.read_text(encoding='utf-8'))
    assert sha(PKG/'PACKAGE_MANIFEST.json')==value['manifest_sha256']
    text=(HERE/'m401_workflow.py').read_text(encoding='utf-8')
    assert '一次固定30文本完整36层/head' in text and '一次独立layer35组合' not in text
    # Exercise the original reused decoder on preserved authentic text evidence;
    # package/status labels alone adapt, no board data or numerical values changed.
    prior=BASE/'runs/M366-staged-text-board-02/BOARD_RESULT.json'
    assert sha(prior)=='b7c2532715f6b90201c9c092e83bcf5245ad7e6ad0b3e5d9bdace60618406ebb'
    r=json.loads(prior.read_text(encoding='utf-8'))
    r.update(status='PASS_M401_TAIL_TEXT_NUMERICAL',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),gate_level='sealed-DMA-fixed30-full36-layer-tail-prefill')
    assert BASE_DECODE(export(r).replace('M400','M401'))[2]==r
    for name in ('m401_close.py','m401_record_authorization.py','m401_collect.py','m401_workflow.py','m401_support02.py'):
        ast.parse((HERE/name).read_text(encoding='utf-8'),feature_version=(3,10))
    tree=ast.parse((HERE/'m401_collect.py').read_text(encoding='utf-8'));decode=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='decode')
    guard=next(n for n in decode.body if isinstance(n,ast.If) and "gate_return_code" in ast.unparse(n.test))
    code=compile(ast.Module(body=[guard],type_ignores=[]),'<actual-rc-guard>','exec')
    exec(code,dict(r={'gate_return_code':0}))
    try:exec(code,dict(r={'gate_return_code':True}))
    except ValueError:pass
    else:raise AssertionError('Boolean rc accepted')
    visual=next(n for n in decode.body if isinstance(n,ast.If) and isinstance(n.test,ast.Compare) and "PASS_M401_TAIL_TEXT_NUMERICAL" in ast.unparse(n.test))
    first=visual.body[0];code=compile(ast.Module(body=[first],type_ignores=[]),'<actual-visual-rejection>','exec')
    exec(code,dict(r={'vision_forward_calls':0}))
    try:exec(code,dict(r={'vision_forward_calls':1}))
    except ValueError:pass
    else:raise AssertionError('Visual forward accepted')
    names=list(value['source_sha256'])+['m36603_collect.py','m401_close.py','m401_record_authorization.py','m401_support02.py']
    value.update(status='PASS_OFFLINE_M401_HOST_SCOPE_AND_CLOSURE02',source_sha256={n:sha(HERE/n) for n in names},prior_support_sha256=sha(original),
                 frozen_package_unchanged=True,scope_label_corrected=True,strict_decoder_dependency_SHA_pinned=True,integer_rc_and_no_visual_checks=True,
                 closure_python310_syntax=True,scope_5_checks_and_13_negative_checks_reused=True,
                 offline_test_harness_rejection='First harness reused old module exception identity against dynamically imported new class; test adapter now maps both class and exception. Frozen candidate unchanged, five corrected tests PASS; no board execution.')
    out=BASE/'runs/M401-tail-text-support-02/RESULT.json';atomic(out,encoded(value),immutable=True);h=sha(out)
    sync('latest_m401_tail_text_support',dict(status=value['status'],result=out.relative_to(ROOT).as_posix(),sha256=h,manifest_sha256=value['manifest_sha256']),
         f'## M401 主机侧范围标签与闭合支持02（2026-10-04）\n\nSHA `{h}`；45载荷包不改，5组件/13负例等已通过检查复用。同步文本修为完整30token/36层/head，旧严格decoder来源SHA锁定，新增布尔rc和视觉越界拒绝的实际代码检查、闭合3.10语法通过。早期测试harness新旧模块异常类身份不一致已离线适配，候选未改/无板端执行。COM3 sudo等待续期，不重复阻塞；下一步只原固定文本上传/执行一次。')
    print(dict(status=value['status'],sha256=h,manifest_sha256=value['manifest_sha256']))
if __name__=='__main__':main()
