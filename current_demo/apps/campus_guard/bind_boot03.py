"""Bind the local presentation to the new immutable boot03 worker; no board call."""
import hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def main():
    f=HERE/'LIVE_BINDING.json';p=ROOT/'deployment/mage_vl4b/optimization_v1/runs/M544-campus-live-worker-preparation-03/RESULT.json';prep=json.loads(p.read_bytes())
    cpu=json.loads((ROOT/'deployment/mage_vl4b/optimization_v1/runs/M544-live-worker-CPU-03/RESULT.json').read_bytes());assert cpu['primary_rc']==0 and cpu['manifest_sha256']==prep['manifest_sha256']
    backup=HERE/'qa/live_software/LIVE_BINDING_before_boot03.json';backup.open('xb').write(f.read_bytes());v=json.loads(f.read_bytes());v.update(package_manifest_sha256=prep['manifest_sha256'],worker_preparation=p.relative_to(ROOT).as_posix(),worker_import_result='deployment/mage_vl4b/optimization_v1/runs/M544-campus-live-worker-board-03/Import/BOARD_RESULT.json',worker_expected_boot=prep['expected_boot'])
    q=f.with_suffix('.partial');q.open('x',encoding='utf-8').write(json.dumps(v,ensure_ascii=False,indent=2)+'\n');q.replace(f)
    print('Pinned current boot worker',prep['manifest_sha256'])
if __name__=='__main__':main()
