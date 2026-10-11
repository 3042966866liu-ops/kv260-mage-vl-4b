"""Offline integration repair only; leave frozen/run package03 untouched."""
import ast
import m351_workflow as w
from m358_prepare_capacity import generate
from owned_buffer_release import OwnedBufferRelease

source=generate()
assert 'Duplicate original-buffer free refused' not in source
assert 'buffer.freebuffer=OwnedBufferRelease(original_free,release_proven,' in source
ast.parse(source,feature_version=(3,10))
calls=[]
def prove():
    calls.append('MMIO')
    assert 'free' not in calls,'Stale MMIO after freed allocation'
    return True
hook=OwnedBufferRelease(lambda:calls.append('free'),prove,lambda:calls.append('record'))
hook()
for _ in range(7):hook()
assert calls==['MMIO','free','record']
package=w.BASE/'candidates/M358-m357-load-only-03'
assert w.sha(package/'PACKAGE_MANIFEST.json')=='9069628e668a98ec0965f0638a85c369ea80587b844075e72e25a710efdd4eb3'
out=w.BASE/'runs/M358-future-release-hook-fix-01/RESULT.json'
r=dict(status='PASS_OFFLINE_FUTURE_RELEASE_HOOK_REPAIR_ONLY',build_id='0x4D333537',
 original_failure_raw_sha256='b079a82a89fe01f7131fca275ba1482f381cca814a23683ad6b9358497ea514e',
 generator_sha256=w.sha(w.HERE/'m358_prepare_capacity.py'),helper_sha256=w.sha(w.HERE/'owned_buffer_release.py'),
 test='One proven backend release followed by seven destructor calls; no second MMIO/backend/record',
 old_package_untouched=True,new_package_prepared=False,board_reexecuted=False,
 cause='Legacy M352 guarded_free copied despite recorded destructor-hook rejection; human-visible acknowledgment preserved.',
 next_step='Capacity failure still blocks model; this offline hook repair does not unlock hardware or memory.')
w.atomic(out,w.encoded(r),immutable=True);digest=w.sha(out)
note=f'## M358 已知析构钩子模式误复用：仅离线修复\n\nM358复用了M352复盘已拒绝的重复free抛异常包装，原7条退出警告保留，这是操作疏漏。后续生成器改用已验证OwnedBufferRelease，释放后先幂等返回，不再读取MMIO或调用后端；真实一次释放后模拟7次析构，MMIO/free/record均仅一次，Python3.10语法通过。原03包/结果不改，没有新包或硬件重跑，容量门禁未解锁。证据SHA `{digest}`。'
w.sync('latest_m358_future_release_hook_fix',dict(status=r['status'],sha256=digest,result=out.relative_to(w.ROOT).as_posix()),note)
p=w.ROOT/'DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md';s=p.read_text(encoding='utf-8-sig')
if digest not in s:
 first,rest=s.split('\n',1)
 w.atomic(p,(first+'\n\n'+note+'\n\n后续诊断禁止从旧M352包直接复用guarded_free。所有拥有缓冲的释放包装必须在首次完成后幂等返回，返回必须早于安全回调/MMIO读取。对历史包修复仅生成新离线版本；收集原结果时不得重跑原gate。\n\n'+rest).encode('utf-8'))
print(r['status'],digest)
