"""Close observed collection failure; no inference or board action."""
import m351_workflow as w
import json

def main():
    recovery=w.BASE/'runs/M368-result-recovery-01/RESULT.json'
    r=json.loads(recovery.read_text(encoding='utf-8'));assert r['status']=='PASS_ORIGINAL_RAW_RECOVERED_NO_GATE'
    out=w.BASE/'runs/M368-uart-closure-01'
    source=w.ROOT/'scripts/m75c_uart_command.ps1';text=source.read_text(encoding='utf-8')
    assert '$serial.ReadBufferSize = 65536' in text and '$match = [regex]::Match($taskMarkerWindow, $taskMarkerPattern)' in text
    value=dict(status='PASS_SAVED_RESULT_RECOVERY_AND_BOUNDED_MARKER_RECEIVER',recovery_sha256=w.sha(recovery),original_raw_sha256=r['raw_sha256'],uart_source_sha256=w.sha(source),missing_or_damaged_chunks=len(r['supplemented_chunks']),read_buffer_bytes=65536,marker_overlap_chars=512,marker_all_split_positions_codes_0_17_pass=True,echoed_unexpanded_marker_rejected=True,full_log_preserved=True,hardware_rerun=False,root_cause_proven=False)
    w.atomic(out/'RESULT.json',w.encoded(value),immutable=True);digest=w.sha(out/'RESULT.json')
    note='''## M368 多MiB串口结果截断（2026-10-02）

真实视频门禁在板端完成并保存原SHA，但2975个900B分块的首次串口日志出现缺失/截断共142块。硬件返回PASS不能替代原字节核对。只用哈希/白名单锁定的新导出组件读取已保存结果，补齐指定块并严格检查完整顺序和原SHA；没有重新执行视频/FPGA事务。

串口接收器保存完整日志，但退出标记改为新字节加512字符重叠扫描，避免日志增大后每次复制/扫描全文；接收缓冲增大到65536B。离线覆盖长输入、所有分割位置、rc0/17及未展开命令回显，后续真实传输rc0确认正常。这个调整降低接收积压风险，不宣称已证明截断的唯一根因。后级证据采用有节奏的900B导出。

禁止硬件重跑补日志、接受缺失块、拼接未知来源或跳过原SHA。原日志冻结，补块集合及顺序严格一致，完整SHA闭合并同步后才进入性能。
'''
    review=w.ROOT/'DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md'
    if note.splitlines()[0] not in review.read_text(encoding='utf-8-sig'):w.atomic(review,(review.read_text(encoding='utf-8-sig').rstrip()+'\n\n'+note).encode('utf-8'))
    w.sync('latest_m368_uart_receiver_closure',dict(status=value['status'],sha256=digest,result=(out/'RESULT.json').relative_to(w.ROOT).as_posix()),f'## M368 已保存结果回收与接收器闭合\n\n证据SHA `{digest}`。缺失/损坏142块仅补取原字节，完整SHA已闭合，未硬件重跑；接收器完整日志保留、512字符重叠识别原rc、65536B接收缓冲，长输入/全部切分/rc0与17/回显负例检查通过。未证明唯一根因，复盘已更新。')
    print(json.dumps(value))

if __name__=='__main__':main()
