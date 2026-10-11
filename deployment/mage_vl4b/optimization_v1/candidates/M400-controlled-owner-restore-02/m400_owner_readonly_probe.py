"""Read only retained process metadata and reproduce the frozen source guard."""
import ast
import base64
import copy
import difflib
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import time

HERE = Path(__file__).resolve().parent
OUT = Path('/home/ubuntu/m400_owner_audit_01/RESULT.json')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(expected):
    path = HERE/'PACKAGE_MANIFEST.json'
    if sha(path) != expected:
        raise RuntimeError('Probe manifest SHA differs')
    m = json.loads(path.read_text(encoding='utf-8'))
    if m['file_count'] != len(m['files']) or len({f['path'] for f in m['files']}) != len(m['files']):
        raise RuntimeError('Probe inventory differs')
    if {p.name for p in HERE.iterdir()} != {f['path'] for f in m['files']} | {'PACKAGE_MANIFEST.json'}:
        raise RuntimeError('Probe whitelist differs')
    for row in m['files']:
        if Path(row['path']).name != row['path']:
            raise RuntimeError('Probe path outside whitelist')
        p = HERE/row['path']
        if p.is_symlink() or not p.is_file() or p.stat().st_size != row['bytes'] or sha(p) != row['sha256']:
            raise RuntimeError('Probe payload differs')
    if sum(f['bytes'] for f in m['files']) != m['total_bytes']:
        raise RuntimeError('Probe byte count differs')


def owner_snapshot(pid):
    p = Path('/proc')/str(pid)
    raw_stat = (p/'stat').read_text(encoding='utf-8')
    rest = raw_stat[raw_stat.rindex(')')+2:].split()
    status = (p/'status').read_text(encoding='utf-8')
    fields = dict(line.split(':', 1) for line in status.splitlines() if ':' in line)
    if not fields['State'].strip().startswith(('T', 't')) or fields['Uid'].strip().split()[0] != '0':
        raise RuntimeError('Expected root owner must remain suspended')
    return dict(pid=pid, start_ticks=rest[19], state=fields['State'].strip(),
                uid=fields['Uid'].strip(), ppid=fields['PPid'].strip(), threads=int(fields['Threads']),
                rss=fields.get('VmRSS'), command=(p/'cmdline').read_bytes().split(b'\0')[:-1],
                executable=os.readlink(p/'exe'))


def reproduce(pin):
    original = Path(pin['original_source'])
    package = Path(pin['original_package'])
    if sha(package/'PACKAGE_MANIFEST.json') != pin['original_manifest_sha256']:
        raise RuntimeError('Original package manifest drift')
    for name, digest in pin['source_sha256'].items():
        if sha(package/name) != digest:
            raise RuntimeError('Frozen original helper drift')
    source = original.read_bytes()
    if hashlib.sha256(source).hexdigest() != pin['original_source_sha256']:
        raise RuntimeError('Installed M241 source drift')
    # Execute only the actual frozen derive function, with its original stdlib globals.
    layer_ns = {}
    exec(compile((package/'m343_layer_scope.py').read_bytes(), '<original-layer-helper>', 'exec'), layer_ns)
    tree = ast.parse((package/'m400_tail_layer_scope.py').read_bytes())
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'derive')
    namespace = dict(ast=ast, copy=copy, original_layer=layer_ns['derive'])
    exec(compile(ast.fix_missing_locations(ast.Module(body=[fn], type_ignores=[])), '<original-tail-derive>', 'exec'), namespace)
    actual = namespace['derive'](source)
    frozen = (package/'frozen_last_layer.py').read_text(encoding='utf-8')
    a = ast.dump(ast.parse(actual), include_attributes=False)
    b = ast.dump(ast.parse(frozen), include_attributes=False)
    from m400_tail_source_02 import validate
    new = (HERE/'frozen_last_layer_02.py').read_bytes()
    guard = validate(source, new, pin['new_frozen_sha256'])
    return dict(python_version=sys.version, source_sha256=hashlib.sha256(source).hexdigest(),
                old_frozen_file_sha256=sha(package/'frozen_last_layer.py'),
                reproduced_generated_text=actual,
                reproduced_generated_sha256=hashlib.sha256(actual.encode('utf-8')).hexdigest(),
                old_text_equal=actual == frozen, same_interpreter_AST_equal=a == b,
                exact_diff=''.join(difflib.unified_diff(frozen.splitlines(True), actual.splitlines(True),
                                                    fromfile='frozen-host-text', tofile='reproduced-board-text')),
                original_failure_generated_text_not_captured=True,
                reproduction_not_live_frame_capture=True, new_guard=guard)


def main(expected):
    verify(expected)
    if os.geteuid() != 0 or OUT.exists():
        raise RuntimeError('Root and fresh read-only audit result required')
    pin = json.loads((HERE/'PIN.json').read_text(encoding='utf-8'))
    raw = Path(pin['original_raw'])
    if sha(raw) != pin['original_raw_sha256']:
        raise RuntimeError('Original failure raw drift')
    target = (Path(pin['original_package'])/'m400_tail_layer_gate.py').as_posix().encode()
    matches = []
    for p in Path('/proc').iterdir():
        if not p.name.isdigit():
            continue
        try:
            argv = (p/'cmdline').read_bytes().split(b'\0')
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            continue
        if target in argv:
            matches.append(int(p.name))
    if len(matches) != 1:
        raise RuntimeError('Exact retained Python owner not unique')
    pid = matches[0]
    before = owner_snapshot(pid)
    thread_rows = []
    for t in (Path('/proc')/str(pid)/'task').iterdir():
        thread_rows.append(dict(tid=int(t.name), name=(t/'comm').read_text(encoding='utf-8').strip(),
                                wait_channel=(t/'wchan').read_text(encoding='utf-8').strip()))
    fds = []
    for f in (Path('/proc')/str(pid)/'fd').iterdir():
        fds.append(dict(fd=int(f.name), target=os.readlink(f)))
    source = reproduce(pin)
    after = owner_snapshot(pid)
    if before != after:
        raise RuntimeError('Owner identity/state changed during read-only audit')
    before['command'] = [x.decode('utf-8') for x in before['command']]
    gate_text = (Path(pin['original_package'])/'m400_tail_layer_gate.py').read_text(encoding='utf-8')
    result = dict(status='PASS_READONLY_RETAINED_OWNER_AND_SOURCE_AUDIT', gate_return_code=0,
                  manifest_sha256=expected, owner=before, threads=thread_rows, descriptors=fds,
                  debugger_paths={name:shutil.which(name) for name in ('gdb','gdbserver','py-spy')},
                  gate_contains_retained_wait='while True: time.sleep(30)' in gate_text,
                  signal_handler_or_recovery_endpoint_found=False,
                  live_python_scope_state_observed=False, owner_release_authorized=False,
                  process_recovered=False, stable_overlay_restored=False,
                  new_overlay_loads=0, new_DMA_allocations=0, model_calls=0,
                  board_signals_sent=0, source_reproduction=source,
                  timestamp_ns=time.time_ns())
    OUT.parent.mkdir(parents=True, exist_ok=True)
    partial = OUT.with_suffix('.part')
    partial.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    os.replace(partial, OUT)
    emit()


def emit():
    raw = OUT.read_bytes()
    count = (len(raw)+899)//900
    print('M400_OWNER_SHA256='+hashlib.sha256(raw).hexdigest(), flush=True)
    for i in range(count):
        print('M400_OWNER_CHUNK=%d/%d:%s' % (i, count, base64.b64encode(raw[i*900:(i+1)*900]).decode()), flush=True)
        time.sleep(.08)


if __name__ == '__main__':
    if sys.argv[1:] == ['Collect']:
        emit()
    elif len(sys.argv) == 3 and sys.argv[1] == 'Run':
        main(sys.argv[2])
    else:
        raise SystemExit('Run expected-manifest-sha | Collect')
