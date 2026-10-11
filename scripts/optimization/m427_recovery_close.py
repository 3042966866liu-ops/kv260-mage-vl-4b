"""Confirm all saved-only recovery receipts and immutable original bytes."""
import json
import re
from m351_workflow import ROOT, BASE, HERE, atomic, encoded, sha, sync
from m427_workflow02 import decode


def main():
    pkg = BASE / 'candidates/M427-saved-export-recovery-01'
    folder = ROOT / 'tmp/m427_recovery01'
    manifest = json.loads((pkg / 'PACKAGE_MANIFEST.json').read_bytes())
    receipts = []
    for name in ['PACKAGE_MANIFEST.json'] + [x['path'] for x in manifest['files']]:
        size = (pkg / name).stat().st_size; count = (size+899)//900
        prefix = 'upload_'+name.replace('.', '_')
        final = (folder / (prefix+'_final.log')).read_text(encoding='utf-8-sig')
        assert 'M212_CHUNKED_FILE_PASS' in final and sha(pkg / name) in final
        logs = sorted(folder.glob(prefix+'_chunk_*.log'))
        assert len(logs) == count
        for i, path in enumerate(logs, 1):
            assert re.search(r'M212_CHUNK_PASS\s+'+str(i)+r'\s+'+str(count)+r'\s+'+str(min(i*900, size))+r'\s', path.read_text(encoding='utf-8-sig'))
        receipts.append(dict(path=name, sha256=sha(pkg / name), chunks=count))
    assert '__M427_RECOVERY_SYNTAX_RC_0__' in (folder / 'syntax.log').read_text(encoding='utf-8-sig')
    log = folder / 'export.log'; text = log.read_text(encoding='utf-8-sig')
    assert '__M427_RECOVERY_EXPORT_RC_0__' in text
    digest, raw, r, chunks = decode(text)
    board = json.loads((ROOT / 'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    e = board['latest_m427_half_software_board']
    assert digest == e['sha256'] and raw == (ROOT / e['result']).read_bytes()
    assert all(digest in (ROOT / n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md', 'docsMILESTONES.md'))
    record = dict(status='CLOSED_M427_SAVED_ONLY_EXPORT_RECOVERY', raw_sha256=digest,
                  recovery_manifest_sha256=sha(pkg / 'PACKAGE_MANIFEST.json'), receipts=receipts,
                  recovered_chunks=chunks, recovered_bytes=len(raw), export_rc=0, original_gate_rc=r['gate_return_code'],
                  original_failed_export_preserved=True, model_or_hardware_reexecuted=False,
                  PS_owner_closed=r['visual_owner_closed'], bindings_restored=r['bindings_restored'],
                  host_control_sha256=sha(HERE / 'm427_collect_saved02.ps1'), performance_pass=False)
    path = BASE / 'runs/M427-saved-export-recovery-closure-01/RESULT.json'
    atomic(path, encoded(record), immutable=True)
    sync('latest_m427_export_recovery_closure', dict(status=record['status'], result=path.relative_to(ROOT).as_posix(), sha256=sha(path), raw_sha256=digest),
         f'## M427 保存原结果导出修复闭合（2026-10-06）\n\nSHA {sha(path)}；raw {digest}，{chunks}块≤900B/完整顺序与全SHA恢复，export rc0。小包全部文件/分块SHA、bash-n核对；唯一修正旧gate_level字面量，原gate rc0/export rc1包及日志保留，没有重新视觉/模型/硬件。owner关闭{r["visual_owner_closed"]}、钩子恢复{r["bindings_restored"]}。后11层特征通过的独立闭合已同步，任务和PL性能仍待验证。')
    print('M427_EXPORT_RECOVERY_CLOSURE_SYNC', sha(path), digest, chunks)


if __name__ == '__main__':
    main()
