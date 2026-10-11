"""Explicit, isolated M238 candidate class; no global runtime monkey patch.

Construction verifies the accepted parser/scheduler source bytes. Importing
this file neither imports PYNQ nor loads an overlay. The caller opts into the
returned class in its separate candidate entry point.
"""
import hashlib
import inspect
from pathlib import Path

from m442_output_parser06 import parse_into_and_check

SOURCE_SHA = {
    "m238_prefill_runtime.py": "daf30c982c276b90ac776178ad258e536925dce52de7ab26b06a9473ff9a9d9a",
    "m236_prefill_runtime.py": "d8061b561fe4d2a089523fde0d3860684244e76bca9646f255f03134fb50be56",
}


def make_candidate_runtime_class(accepted_class):
    scheduler_path = Path(inspect.getsourcefile(accepted_class))
    parser_path = Path(inspect.getsourcefile(accepted_class._parse_into_and_check))
    for path in (scheduler_path, parser_path):
        if path.name not in SOURCE_SHA or hashlib.sha256(path.read_bytes()).hexdigest() != SOURCE_SHA[path.name]:
            raise RuntimeError("M442 accepted runtime source identity differs: " + str(path))
    if scheduler_path.name != "m238_prefill_runtime.py" or parser_path.name != "m236_prefill_runtime.py":
        raise RuntimeError("M442 unexpected scheduler/parser binding")

    class M442PrefillRuntime(accepted_class):
        _parse_into_and_check = staticmethod(parse_into_and_check)

        def evidence(self):
            result = super().evidence()
            result.update(output_parser="m442-fp16-view-fused-fp32-scatter-scale-v1",
                          parser_full_fp32_intermediate_arrays=0,
                          parser_scope="language_family_many only; LM head and vision unchanged",
                          parser_workers=1, parser_candidate_only=True)
            return result

    return M442PrefillRuntime
