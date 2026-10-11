"""Saved package metadata recovery only; no reconstruction or board calls."""
import ast,json
from pathlib import Path
from m351_workflow import ROOT,BASE,HERE,encoded,sha,sync
from m441_host_io08 import atomic
from m441_prepare_layer09 import verify_package

def record(key,path,value,note):
    atomic(path,encoded(value),immutable=True)
    sync(key,dict(status=value['status'],result=path.relative_to(ROOT).as_posix(),sha256=sha(path),board=False),note+'\n\nSHA '+sha(path)+'；'+value.get('explanation',''))

err=BASE/'runs/M442-live-parser-video-preparation-error-01/RESULT.json'
record('latest_m442_video_preparation_error01',err,dict(status='FAIL_M442_VIDEO_PREPARATION_METADATA_ONLY01',explanation='evidence字符串遮蔽同名函数；全部冻结包/控制器已写，准备记录尚未写。0COM3/Overlay/事务。保留原脚本和包，仅核对原字节补写准备元数据。',generator_sha256=sha(HERE/'m442_prepare_video01.py'),board=False),'## M442视频准备元数据错误（2026-10-10）')
pkg=BASE/'candidates/M442-live-parser-video-01';boot=BASE/'candidates/M442-live-parser-video-transfer-01'
verify_package(pkg);verify_package(boot)
prior=BASE/'runs/M442-live-parser-text-board-01/BOARD_RESULT.json';p=json.loads(prior.read_bytes());d=sha(prior)
assert p['status']=='PASS_M442T_FIXED_TEXT_DIAGNOSTIC'
assert (pkg/'STAGE_PREREQUISITE.json').read_bytes()==prior.read_bytes()
for name in ('m442_video_decoder01.py','m442_video_workflow01.py'):ast.parse((HERE/name).read_bytes(),feature_version=(3,10))
files=[dict(path=(HERE/name).relative_to(ROOT).as_posix(),sha256=sha(HERE/name)) for name in ('m442_video_decoder01.py','m442_video_workflow01.py','m442_video_control01.ps1')]
r=dict(status='PREPARED_M442_LIVE_PARSER_FIXED159_VIDEO01',manifest_sha256=sha(pkg/'PACKAGE_MANIFEST.json'),bootstrap_manifest_sha256=sha(boot/'PACKAGE_MANIFEST.json'),prior_text_raw_sha256=d,kernel_build='0x4D343431',hardware_unchanged=True,original_visual_policy_and_math=True,parser_workers=1,seven_DMA_resident=True,expected_language_physical=781,expected_visual_physical=286,total_with_minimal=1068,board=False,performance=False,files=files,metadata_recovery_error_sha256=sha(err),package_rebuilt=False)
out=BASE/'runs/M442-live-parser-video-preparation-01/RESULT.json'
record('latest_m442_live_parser_video_preparation',out,r,'## M442新解析视频准备原字节恢复01（2026-10-10）')
print(r['status'],sha(out))
