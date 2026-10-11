"""Four-pair pipeline with partitioned short LUTRAM weight banks."""
import difflib
import json
from pathlib import Path
from m441_host_io08 import atomic
from m351_workflow import ROOT,BASE,HERE,encoded,sha,sync

failed=BASE/'runs/M443-pair-pipeline-resource-guard-02/RESULT.json'
f=json.loads(failed.read_bytes());assert f['status']=='FAIL_M443_HLS_RESOURCE_OR_MAC_GUARD02' and not f['checks']['resources_fit']
old=ROOT/'tmp/m443_pair_pipeline_01';new=ROOT/'tmp/m443_pair_pipeline_03'
entry=Path('hls/mage_prefill_m89x_runtime/mage_prefill_m89x_runtime.cpp')
assert not new.exists() and not (ROOT/'tmp/m443_hls_project_03').exists()
source=(old/entry).read_text(encoding='utf-8')
replacement='#pragma HLS ARRAY_PARTITION variable=weight0 complete dim=2\n#pragma HLS ARRAY_PARTITION variable=weight1 complete dim=2\n#pragma HLS BIND_STORAGE variable=weight0 type=ram_2p impl=lutram\n#pragma HLS BIND_STORAGE variable=weight1 type=ram_2p impl=lutram'
anchor='#pragma HLS ARRAY_PARTITION variable=weight0 complete dim=0\n#pragma HLS ARRAY_PARTITION variable=weight1 complete dim=0'
assert source.count(anchor)==1
candidate=source.replace(anchor,replacement)
for p in old.rglob('*'):
    if p.is_file() and p.suffix in ('.cpp','.h','.hpp'):
        atomic(new/p.relative_to(old),candidate.encode() if p.relative_to(old)==entry else p.read_bytes(),immutable=True)
atomic(new/'run_m443_hls.tcl',(old/'run_m443_hls.tcl').read_text(encoding='utf-8').replace('m443_pair_pipeline_01','m443_pair_pipeline_03').replace('m443_hls_project_01','m443_hls_project_03').encode(),immutable=True)
atomic(new/'SOURCE.diff',''.join(difflib.unified_diff(source.splitlines(True),candidate.splitlines(True),fromfile='frozen01.cpp',tofile='independent03.cpp')).encode(),immutable=True)
controller=(HERE/'m443_control02.py').read_text(encoding='utf-8').replace('revision02','revision03').replace('REVISION02','REVISION03').replace('pipeline_02','pipeline_03').replace('project_02','project_03').replace('hls-02','hls-03').replace('preparation-02','preparation-03').replace('active02','active03').replace('HLS02','HLS03')
atomic(HERE/'m443_control03.py',controller.encode(),immutable=True)
record=dict(status='PREPARED_M443_WEIGHT_BANK_RESOURCE_REVISION03',build_id='0x4D343433',failed_resource_guard_sha256=sha(failed),source_sha256=sha(new/entry),original_source_sha256='de023abc5b849a56048d5e71bcefc67be1564fe150174607fdc89792905dbe6a',contiguous_work=64,only_weight_storage_pragmas_changed_from01=True,no_math_or_group_order_change=True,board=False,performance=False,files=[dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p)) for p in sorted(new.rglob('*')) if p.is_file()])
dest=BASE/'runs/M443-pair-pipeline-preparation-03/RESULT.json'
atomic(dest,encoded(record),immutable=True)
sync('latest_m443_pair_pipeline_preparation03',dict(status=record['status'],result=dest.relative_to(ROOT).as_posix(),sha256=sha(dest),board=False),f'## M443资源本级03准备（2026-10-10）\n\nSHA {sha(dest)}；02仍超HLS LUT，保留原字节。03仅从01修改weight存储pragma：64元素分区、四pair短LUTRAM bank，保留64-work连续与所有原算式。实际binding/II/资源/数值待裁决，未扩大RTL/上板。')
print(record['status'],sha(dest))
