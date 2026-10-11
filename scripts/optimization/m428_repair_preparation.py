"""Pre-board helper assembly correction; frozen packet01 kept intact."""
import importlib.util
import json
import tempfile
import numpy as np
from m351_workflow import ROOT, BASE, HERE, atomic, encoded, sha, sync


def main():
    old = BASE / 'candidates/M428-late11-saved-language-01'
    spec = importlib.util.spec_from_file_location('actual_m428_helper01', old / 'm428_saved_features.py')
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as temp:
        try:
            mod.save_array(__import__('pathlib').Path(temp) / 'test.npy', np.zeros((98, 2560), dtype=np.float32))
        except NameError as error:
            assert "'os'" in str(error)
            cause = str(error)
        else:
            raise AssertionError('Expected local missing os import not reproduced')
    r = dict(status='REJECT_M428_PACKET01_HELPER_IMPORT_LOCAL_ONLY',
             manifest_sha256=sha(old / 'PACKAGE_MANIFEST.json'), actual_save_array_error=cause,
             board_upload=False, model_forward_calls=0, new_packet_required=True)
    p = BASE / 'runs/M428-preparation-rejection-01/RESULT.json'
    atomic(p, encoded(r), immutable=True)
    sync('latest_m428_preparation_rejection', dict(status=r['status'], result=p.relative_to(ROOT).as_posix(), sha256=sha(p)),
         f'## M428 上传前helper组装缺失导入拒绝（2026-10-06）\n\nSHA {sha(p)}；实际save_array自有NPY检查复现os导入遗漏，01包未上传/执行。原01保留，新02只补stdlib os导入，语言数学与固定范围不改，完整实际加载/保存/导出链路组件后才能上传。')
    helper = (HERE / 'm428_saved_features.py').read_text(encoding='utf-8')
    fixed = helper.replace('import json\n', 'import json\nimport os\n', 1)
    assert fixed.replace('import json\nimport os\n', 'import json\n', 1) == helper
    atomic(HERE / 'm428_saved_features02.py', fixed.encode('utf-8'), immutable=True)
    preparation = (HERE / 'm428_prepare.py').read_text(encoding='utf-8')
    preparation = preparation.replace('M428-late11-saved-language-01', 'M428-late11-saved-language-02')
    preparation = preparation.replace("HERE / 'm428_saved_features.py'", "HERE / 'm428_saved_features02.py'")
    preparation = preparation.replace('M428-saved-language-preparation-01', 'M428-saved-language-preparation-02')
    atomic(HERE / 'm428_prepare02.py', preparation.encode('utf-8'), immutable=True)
    print('M428_LOCAL_REJECTION_PRESERVED', sha(p))


if __name__ == '__main__':
    main()
