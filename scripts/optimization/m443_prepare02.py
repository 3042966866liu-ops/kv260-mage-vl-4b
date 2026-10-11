"""Local revision at the failed HLS resource level, preserving attempt01."""
import json
import difflib
import xml.etree.ElementTree as ET
from pathlib import Path
from m441_host_io08 import atomic
from m351_workflow import ROOT,BASE,HERE,encoded,sha,sync

old=ROOT/'tmp/m443_pair_pipeline_01'
new=ROOT/'tmp/m443_pair_pipeline_02'
entry=Path('hls/mage_prefill_m89x_runtime/mage_prefill_m89x_runtime.cpp')
previous=BASE/'runs/M443-pair-pipeline-hls-collection-01/RESULT.json'
prior=json.loads(previous.read_bytes())
top=ROOT/'tmp/m443_hls_project_01/hls/syn/report/m89x_runtime_kernel_csynth.xml'
t=ET.parse(top).getroot()
resources={e.tag:int(e.text) for e in t.find('AreaEstimates/Resources')}
capacity={e.tag:int(e.text) for e in t.find('AreaEstimates/AvailableResources')}
assert resources['LUT']>capacity['LUT']
guard=dict(status='FAIL_M443_HLS_RESOURCE_ADMISSION01',numerical_and_II_sha256=sha(previous),report_sha256=sha(top),resources=resources,capacity=capacity,checks=dict(resources_fit=all(resources[k]<=capacity[k] for k in resources)),routed_resource_fit_unknown=True,no_RTL_or_shell_or_board_started=True,next_step='Only failed HLS resource level: two contiguous pairs per 32-work pipeline, two blocks per record; preserve source01')
out=BASE/'runs/M443-pair-pipeline-resource-guard-01/RESULT.json'
atomic(out,encoded(guard),immutable=True)
sync('latest_m443_resource_admission',dict(status=guard['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out),board=False),f'## M443 HLS资源门禁01拒绝（2026-10-10）\n\nSHA {sha(out)}；II1/七数值PASS保持，HLS LUT126802>117120，不能当资源通过，也不按实现可能优化绕过。本级独立02尝试每次两对32-work，保留旧64-work原字节；未启动RTL/整壳/板端。')
assert not new.exists() and not (ROOT/'tmp/m443_hls_project_02').exists()
s=(old/entry).read_text(encoding='utf-8')
begin=s.index('      // Decode all four independent output pairs')
end=s.index('\n    }\n    for (unsigned token',begin)
block=s[begin:end]
block=block.replace('// Decode all four independent output pairs before one shared MAC loop.','// Decode two independent pairs before each shared 32-work MAC loop.')
block=block.replace('weight0[4][64], weight1[4][64]','weight0[2][64], weight1[2][64]').replace('scale0[4], scale1[4]','scale0[2], scale1[2]')
block=block.replace('      for (unsigned pair = 0; pair < 4; ++pair) {','      for (unsigned pair_block = 0; pair_block < 2; ++pair_block) {\n      for (unsigned local_pair = 0; local_pair < 2; ++local_pair) {\n        const unsigned pair = 2 * pair_block + local_pair;')
decode_end=block.index('      for (unsigned work')
block=block[:decode_end].replace('weight0[pair]','weight0[local_pair]').replace('weight1[pair]','weight1[local_pair]').replace('scale0[pair]','scale0[local_pair]').replace('scale1[pair]','scale1[local_pair]')+block[decode_end:]
block=block.replace('work < 64','work < 32').replace('const unsigned pair = work >> 4;','const unsigned local_pair = work >> 4;\n        const unsigned pair = 2 * pair_block + local_pair;')
block=block.replace('weight0[pair]','weight0[local_pair]').replace('weight1[pair]','weight1[local_pair]').replace('scale0[pair]','scale0[local_pair]').replace('scale1[pair]','scale1[local_pair]')
block+='\n      }'
candidate=s[:begin]+block+s[end:]
candidate=candidate.replace('// M443: one 64-work pipeline per record; original per-output group order.','// M443 revision02: two 32-work pipelines; original per-output group order.')
for p in old.rglob('*'):
    if p.is_file() and p.suffix in ('.cpp','.h','.hpp'):
        atomic(new/p.relative_to(old),candidate.encode() if p.relative_to(old)==entry else p.read_bytes(),immutable=True)
tcl=(old/'run_m443_hls.tcl').read_text(encoding='utf-8').replace('m443_pair_pipeline_01','m443_pair_pipeline_02').replace('m443_hls_project_01','m443_hls_project_02')
atomic(new/'run_m443_hls.tcl',tcl.encode(),immutable=True)
atomic(new/'SOURCE.diff',''.join(difflib.unified_diff(s.splitlines(True),candidate.splitlines(True),fromfile='frozen01.cpp',tofile='independent02.cpp')).encode(),immutable=True)
record=dict(status='PREPARED_M443_RESOURCE_LEVEL_REVISION02',build_id='0x4D343433',failed_resource_guard_sha256=sha(out),original_source_sha256='de023abc5b849a56048d5e71bcefc67be1564fe150174607fdc89792905dbe6a',source_sha256=sha(new/entry),pair_blocks=2,contiguous_pair_work=32,MAC_work_per_record=64,no_math_or_group_order_change=True,board=False,performance=False,files=[dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p),bytes=p.stat().st_size) for p in sorted(new.rglob('*')) if p.is_file()])
dest=BASE/'runs/M443-pair-pipeline-preparation-02/RESULT.json'
atomic(dest,encoded(record),immutable=True)
sync('latest_m443_pair_pipeline_preparation02',dict(status=record['status'],result=dest.relative_to(ROOT).as_posix(),sha256=sha(dest),board=False),f'## M443资源本级02准备（2026-10-10）\n\nSHA {sha(dest)}；每record两段32-work，两个pair连续进入共享MAC，四pair总工作64，原group累计顺序/表达式不改。实际II/资源/数值尚待新HLS裁决，旧01不改。')
print(record['status'],sha(dest))
