"""Pure package/lifecycle support, testable without a board or PYNQ."""
import json
from pathlib import Path
from measurement import sha256
from board_safety import safe_to_release


def verify_package(here,digest):
    here=Path(here).resolve();manifest=here/'PACKAGE_MANIFEST.json'
    if sha256(manifest)!=digest:raise RuntimeError('Manifest mismatch')
    data=json.loads(manifest.read_text())
    rows=data['files'];expected={r['path'] for r in rows}
    actual={p.relative_to(here).as_posix() for p in here.rglob('*') if p.is_file() and p!=manifest}
    if len(expected)!=len(rows) or len(rows)!=data['file_count'] or actual!=expected:
        raise RuntimeError('Package whitelist/count mismatch')
    if sum(r['bytes'] for r in rows)!=data['total_bytes']:raise RuntimeError('Byte count mismatch')
    for row in rows:
        path=(here/row['path']).resolve();path.relative_to(here)
        if path.stat().st_size!=row['bytes'] or sha256(path)!=row['sha256']:
            raise RuntimeError('Package member mismatch: '+row['path'])


def guarded_close_board(board,snapshot,launch_programmed):
    evidence=dict(recovery_required=False,buffers_released=False,errors=[])
    if board is None:return evidence
    if launch_programmed:
        try:
            state=snapshot(board.kernel,board.dma)
            evidence['release_snapshot']=state
            safe=safe_to_release(state)
        except Exception as exc:
            evidence['errors'].append('Snapshot failure: '+repr(exc));safe=False
        if not safe:
            evidence.update(recovery_required=True,unsafe_dma_buffers_retained=True)
            return evidence
    else:evidence['release_basis']='No launch was programmed in this object'
    try:
        board.close();evidence['buffers_released']=True
    except Exception as exc:
        # Do not allow cleanup to mask the original error or bypass evidence writing.
        evidence['errors'].append('Board close failed: '+repr(exc))
    return evidence


def compact_summary(result):
    summary={k:v for k,v in result.items() if k not in ('transactions','board_evidence','request')}
    if 'request' in result:
        summary['request']={k:v for k,v in result['request'].items() if k not in ('board_before','board_after','input_token_ids')}
    return summary
