"""Load byte-verified dense runtime without replacing installed module objects.

Factory construction is separate from release preflight and hardware execution.
Aliases exist only while loading modules under a unique private namespace;
all ordinary sys.modules names and sys.path are restored before returning.
"""
import hashlib
import importlib.util
import json
import sys
import threading
from pathlib import Path

LOCK = threading.RLock()
ORDER = ('m455_dense_output', 'm455_runtime_abi01', 'm455_output_parser02', 'contract_runtime', 'board_runtime',
         'm230_prefill_runtime', 'm231_prefill_runtime', 'm236_prefill_runtime', 'm238_prefill_runtime')
REQUIRED = set(ORDER) | {'reserved_ddr_pool'}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_private(directory, manifest_sha256, *, namespace='_m455_dense_private01'):
    directory = Path(directory).resolve()
    assert namespace.isidentifier() and namespace.startswith('_m455_')
    manifest_path = directory / 'PACKAGE_MANIFEST.json'
    if digest(manifest_path) != manifest_sha256:
        raise RuntimeError('Private component manifest identity differs')
    manifest = json.loads(manifest_path.read_bytes())
    rows = manifest['files']
    if manifest.get('missing') != 0 or {Path(r['path']).stem for r in rows} != REQUIRED:
        raise RuntimeError('Only the exact closed private runtime component is supported')
    if {p.name for p in directory.iterdir()} != {r['path'] for r in rows} | {'PACKAGE_MANIFEST.json'}:
        raise RuntimeError('Private runtime component contains undeclared files')
    for row in rows:
        path = directory / row['path']
        if path.parent != directory or path.suffix != '.py' or path.is_symlink():
            raise RuntimeError('Private module path differs')
        if path.stat().st_size != row['bytes'] or digest(path) != row['sha256']:
            raise RuntimeError('Private module bytes differ: ' + row['path'])
    with LOCK:
        if any(namespace + '.' + name in sys.modules for name in ORDER):
            raise RuntimeError('Private namespace already loaded; reuse its returned factory')
        sentinel = object()
        original = {name: sys.modules.get(name, sentinel) for name in ORDER}
        old_path = list(sys.path)
        loaded = {}
        complete = False
        try:
            sys.path.insert(0, str(directory))
            for name in ORDER:
                unique = namespace + '.' + name
                path = directory / (name + '.py')
                spec = importlib.util.spec_from_file_location(unique, path)
                module = importlib.util.module_from_spec(spec)
                sys.modules[unique] = module
                sys.modules[name] = module
                spec.loader.exec_module(module)
                loaded[name] = module
            board = loaded['board_runtime']
            if board.BUILD_ID != 0x4D343535:
                raise RuntimeError('Private driver Build-ID differs')
            runtime = loaded['m238_prefill_runtime'].M238PrefillRuntime
            if runtime.__module__ != namespace + '.m238_prefill_runtime':
                raise RuntimeError('Private class identity differs')
            complete = True
            return dict(runtime_class=runtime, base=board, contract=loaded['contract_runtime'],
                        modules=loaded, manifest_sha256=manifest_sha256, namespace=namespace,
                        constructor_executed=False, board=False)
        finally:
            sys.path[:] = old_path
            for name, before in original.items():
                if before is sentinel:
                    sys.modules.pop(name, None)
                else:
                    sys.modules[name] = before
            if not complete:
                for name in ORDER:
                    sys.modules.pop(namespace + '.' + name, None)
