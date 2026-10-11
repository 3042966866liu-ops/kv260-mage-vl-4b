"""Recover a recorded historical prefix only when its exact SHA-256 matches."""
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]


def main():
    rtl=json.loads((ROOT/'deployment/mage_vl4b/M134_M120_RTL_COSIM_GATE_RESULT.json').read_text(encoding='utf-8'))
    row=next(r for r in rtl['evidence'] if r['path'].replace('\\','/')=='m132_m120_fifo_backpressure_hls/hls/hls.log')
    source=ROOT/row['path'].replace('\\','/')
    data=source.read_bytes();prefix=data[:row['bytes']]
    digest=hashlib.sha256(prefix).hexdigest()
    result=dict(status='PREFIX_NOT_MATCH_NO_RECOVERY',source=str(source),current_bytes=len(data),current_sha256=hashlib.sha256(data).hexdigest(),
                historical_bytes=row['bytes'],expected_sha256=row['sha256'],prefix_sha256=digest,source_modified=False)
    if digest==row['sha256']:
        out=ROOT/'deployment/mage_vl4b/optimization_v1/runs/M341-stable-hardware-reuse-audit-01/recovered_m132_hls.log'
        if out.exists(): raise RuntimeError('Immutable recovered log exists')
        out.write_bytes(prefix)
        result.update(status='RECOVERED_EXACT_RECORDED_PREFIX',recovered_path=out.relative_to(ROOT).as_posix())
    report=ROOT/'deployment/mage_vl4b/optimization_v1/runs/M341-stable-hardware-reuse-audit-01/PREFIX_RECOVERY.json'
    if report.exists():raise RuntimeError('Immutable recovery exists')
    report.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result))


if __name__=='__main__':main()
