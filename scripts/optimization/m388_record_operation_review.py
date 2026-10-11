"""Document metadata/selector mistakes after final saved-only closure."""
import json
from m351_workflow import ROOT,BASE,sha,atomic,encoded,sync
def main():
    board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_text(encoding='utf-8'));latest=board['latest_m388_ps_performance_closure'];assert sha(ROOT/latest['result'])==latest['sha256']
    records=[board['latest_m387_transfer_selector_offline_rejection'],board['latest_m387_authorization_recovery_support'],board['latest_m387_metadata_recovery_preparation'],board['latest_m387_ps_video_closure']]
    for r in records:assert sha(ROOT/r['result'])==r['sha256']
    path=ROOT/'DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md';old=path.read_text(encoding='utf-8-sig');old_sha=sha(path);title='## M387 两源传输选择与回收元数据前缀（2026-10-03）'
    assert title not in old
    note=title+'\n\n- 两源依赖复用的PowerShell选择先合并字典，主源同名不同SHA覆盖了可用的次源条目。完整assembly本身严格，但控制器会多传文件；在任何上传前的最后离线真实清单核对中拒绝。原控制及recovered01保留，独立recovered02改为任一来源完整路径/SHA/字节匹配可复用，实际PowerShell选择与assembly白名单一致。原包不改。拒绝SHA `'+records[0]['sha256']+'`，修复支持SHA `'+records[1]['sha256']+'`。\n- collector生成器只替换大写M386，同步键仍为latest_m386_ps_video_board；严格数值decode、原字节和完整SHA无变化。原collector与支持保留，独立saved-only collector只修复同步键，用已保存UART原字节同步latest_m387_ps_video_board，闭合后才准备性能。没有重跑视频。修复准备SHA `'+records[2]['sha256']+'`，视频原SHA `'+board['latest_m387_ps_video_board']['sha256']+'`。\n- 新生成器必须核对实际控制器的两源选择、最终BOARD键和本级ID/路径，不仅做Python语法或原数字参考负例；相同文件名、不同主源SHA、精确次源匹配必须覆盖。元数据失败只能修回收及同步，不重新执行硬件；原错误代码、日志和证据不可覆盖。\n\n'
    heading,rest=old.split('\n',1);atomic(path,(heading+'\n\n'+note+rest.lstrip('\n')).encode('utf-8'))
    value=dict(status='PASS_OPERATION_REVIEW_METADATA_AND_SELECTOR_APPEND',review_previous_sha256=old_sha,review_updated_sha256=sha(path),source_receipts=records,video_raw_unchanged=True,hardware_rerun=False,performance_closure_sha256=latest['sha256'])
    p=BASE/'runs/M388-operation-review-update-01/RESULT.json';atomic(p,encoded(value),immutable=True);d=sha(p)
    sync('latest_m388_operation_review_update',dict(status=value['status'],result=p.relative_to(ROOT).as_posix(),sha256=d),f'## M388 操作复盘补齐\n\nM387两源选择离线拒绝和元数据同步键修复补入部署复盘，原代码/日志/包/raw保留，不重复硬件。复盘SHA {value["review_updated_sha256"]}，核对SHA {d}；M388最终裁决以已闭合性能证据为准。')
    print('M388_OPERATION_REVIEW_UPDATED',d)
if __name__=='__main__':main()
