"""Finalize full-request numerical packet with recursive closure and same-SHA reuse."""
import ast
import json
from m351_workflow import ROOT, BASE, HERE, atomic, encoded, sha, sync
from m427_prepare import once

OLD = BASE / 'candidates/M432-late11-integrated-video-01'
PKG = BASE / 'candidates/M432-late11-integrated-video-02'


def main():
    if PKG.exists():
        raise RuntimeError('Immutable finalized packet exists')
    board = json.loads((ROOT / 'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    e = board['latest_m432_provider_component']
    if sha(ROOT / e['result']) != e['sha256'] or e['manifest_sha256'] != sha(OLD / 'PACKAGE_MANIFEST.json'):
        raise RuntimeError('Actual provider component differs')
    for n in ('CURRENT_STATE.md', 'docsMILESTONES.md'):
        if e['sha256'] not in (ROOT / n).read_text(encoding='utf-8-sig'):
            raise RuntimeError('Component not synchronized')
    PKG.mkdir(parents=True)
    for row in json.loads((OLD / 'PACKAGE_MANIFEST.json').read_bytes())['files']:
        if sha(OLD / row['path']) != row['sha256']:
            raise RuntimeError('Preparation changed')
        if row['path'] not in ('SHA256SUMS', 'm432_gate.py'):
            atomic(PKG / row['path'], (OLD / row['path']).read_bytes(), immutable=True)
    g = (OLD / 'm432_gate.py').read_text(encoding='utf-8')
    g = once(g, "result = dict(status='FAIL', gate_level=", "result = dict(status='FAIL', manifest_sha256=args.manifest_sha, gate_level=")
    # Complete PASS still requires verify_self; identity on early FAIL is only the supplied requested package identity.
    atomic(PKG / 'm432_gate.py', g.encode('utf-8'), immutable=True)
    reuse = BASE / 'candidates/M428-late11-saved-language-02'
    assembler = '''"""Whitelisted same-SHA immutable source copy; no model, board or external assets."""
import hashlib,json,shutil,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
OLD=Path('/home/ubuntu/m428_saved_feature_candidate_01')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
expected=''' + repr(sha(reuse / 'PACKAGE_MANIFEST.json')) + '''
if sha(OLD/'PACKAGE_MANIFEST.json')!=expected:raise RuntimeError('Old immutable packet identity differs')
original=json.loads((OLD/'PACKAGE_MANIFEST.json').read_bytes())
for row in original['files']:
    p=OLD/row['path']
    if p.is_symlink() or p.stat().st_size!=row['bytes'] or sha(p)!=row['sha256']:raise RuntimeError('Old payload differs')
m=json.loads((HERE/'PACKAGE_MANIFEST.json').read_bytes());byname={r['path']:r for r in original['files']}
for r in m['files']:
    p=HERE/r['path']
    if '/' in r['path'] or '\\\\' in r['path'] or Path(r['path']).name!=r['path']:raise RuntimeError('Path outside flat whitelist')
    if not p.exists():
        if byname.get(r['path'])!=r:raise RuntimeError('Missing changed file cannot reuse old source')
        shutil.copyfile(OLD/r['path'],p)
    if p.is_symlink() or p.stat().st_size!=r['bytes'] or sha(p)!=r['sha256']:raise RuntimeError('Final payload differs')
names={x['path'] for x in m['files']}
if len(names)!=m['file_count'] or sum(r['bytes'] for r in m['files'])!=m['total_bytes'] or {p.name for p in HERE.iterdir()}!=names|{'PACKAGE_MANIFEST.json'}:raise RuntimeError('Final exact closure differs')
if len(sys.argv)!=2 or sha(HERE/'PACKAGE_MANIFEST.json')!=sys.argv[1]:raise RuntimeError('Manifest argument differs')
print('M432_ASSEMBLY_PASS',sys.argv[1],m['file_count'],m['total_bytes'])
'''
    atomic(PKG / 'm432_assemble.py', assembler.encode('utf-8'), immutable=True)
    plan = json.loads((PKG / 'PLAN.json').read_bytes())
    folders = [PKG]
    for row in plan['visual_reused_packages']:
        matches = [p.parent for p in (BASE / 'candidates').glob('*/PACKAGE_MANIFEST.json') if sha(p) == row['manifest_sha256']]
        if len(matches) != 1:
            raise RuntimeError('Unique reused dependency package required')
        folders.extend(matches)
    folders.append(BASE / 'candidates/M368-staged-video-03')
    if not folders[-1].exists():
        matches = [p.parent for p in (BASE / 'candidates').glob('*/PACKAGE_MANIFEST.json') if sha(p) == 'f5937684306cd0ce40683a9bc46097b69cc7a9c7625bf208883eaada8071fb66']
        if len(matches) != 1:
            raise RuntimeError('Frozen common owner package required')
        folders[-1] = matches[0]
    modules = {}
    for folder in folders:
        for p in folder.glob('*.py'):
            modules.setdefault(p.stem, p)
    for row in json.loads((PKG / 'M348_SOURCE_IDENTITIES.json').read_bytes())['files']:
        for path in (ROOT / row['path'], ROOT / 'release_staging/kv260-mage-vl-4b-prebuilt-install-20260926-v7' / row['path']):
            if path.is_file() and path.stat().st_size == row['bytes'] and sha(path) == row['sha256']:
                modules.setdefault(path.stem, path); break
    seen, missing = set(), []
    def visit(name):
        if name in seen: return
        seen.add(name)
        tree = ast.parse(modules[name].read_text(encoding='utf-8-sig'), feature_version=(3, 10))
        deps = [a.name.split('.')[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names]
        deps += [(n.module or '').split('.')[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
        for dep in deps:
            if dep in modules: visit(dep)
            elif len(dep) > 1 and dep[0] == 'm' and dep[1].isdigit(): missing.append([name, dep])
    for name in ('m432_gate', 'm432_entry', 'm432_export', 'm432_assemble'): visit(name)
    if missing:
        raise RuntimeError('Recursive dependencies missing: ' + repr(missing))
    atomic(PKG / 'DEPENDENCY_CLOSURE.json', encoded(dict(missing=missing, recursive_modules=len(seen), files={n: sha(modules[n]) for n in sorted(seen)}, fixture_component_sha256=e['sha256'])), immutable=True)
    atomic(PKG / 'SHA256SUMS', ''.join(f'{sha(p)}  {p.name}\n' for p in sorted(PKG.iterdir())).encode('ascii'), immutable=True)
    files = sorted(PKG.iterdir())
    manifest = dict(file_count=len(files), total_bytes=sum(p.stat().st_size for p in files), files=[dict(path=p.name, bytes=p.stat().st_size, sha256=sha(p)) for p in files])
    atomic(PKG / 'PACKAGE_MANIFEST.json', encoded(manifest), immutable=True)
    record = dict(status='M432_INTEGRATED_PACKET_RECURSIVE_CLOSURE_SUPPORT_PENDING', manifest_sha256=sha(PKG / 'PACKAGE_MANIFEST.json'),
                  file_count=manifest['file_count'], total_bytes=manifest['total_bytes'], recursive_modules=len(seen), missing=missing,
                  original_01_preparation_preserved=True, only_gate_change_initial_requested_manifest_on_early_failure=True,
                  actual_provider_component_sha256=e['sha256'], board_run=False, numerical_pass=False, performance_pass=False,
                  temperature_measurement_enabled=False, next_step='Actual prerequisite negative checks and exporter/strict collector/control/assembly checks before one full numerical run.')
    out = BASE / 'runs/M432-packet-preparation-02/RESULT.json'; atomic(out, encoded(record), immutable=True)
    sync('latest_m432_integrated_packet', dict(status=record['status'], result=out.relative_to(ROOT).as_posix(), sha256=sha(out), manifest_sha256=record['manifest_sha256']),
         f'## M432 完整请求数值02包与递归闭包（2026-10-07）\n\nSHA {sha(out)}，manifest {record["manifest_sha256"]}；{manifest["file_count"]}载荷/{manifest["total_bytes"]}B、递归{len(seen)}模块missing0。实际provider组件同SHA复用，01原稿保留；只增加早期FAIL的请求manifest身份与同SHA旧包白名单组装，PASS仍要求完整校验。收集/控制配套待验证，未上传/模型/硬件数值或性能，不测温。')
    print('M432_FINAL_PACKET_SYNC', sha(out), record['manifest_sha256'])


if __name__ == '__main__':
    main()
