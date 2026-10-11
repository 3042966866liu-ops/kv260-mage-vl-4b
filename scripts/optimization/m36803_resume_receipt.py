"""Close transfer-only missing dependency; preserve original failed assembly."""
import json
import m351_workflow as w
from m36803_collect import PKG


def main():
    old=w.ROOT/'tmp/m36803/assembly.log';a=w.ROOT/'tmp/m36803/assembly_resume.log';s=w.ROOT/'tmp/m36803/root_syntax_resume.log'
    assert '__M368_ASSEMBLY_RC_1__' in old.read_text(encoding='utf-8-sig')
    assert 'M368_ALL_PAYLOAD_SHA_VERIFIED_NO_GATE' in a.read_text(encoding='utf-8-sig') and '__M368_ASSEMBLY_RC_0__' in a.read_text(encoding='utf-8-sig') and '__M368_SYNTAX_RC_0__' in s.read_text(encoding='utf-8-sig')
    r=dict(status='PASS_M368_STAGE_PACKAGE_TRANSFER_ONLY',manifest_sha256=w.sha(PKG/'PACKAGE_MANIFEST.json'),original_failed_assembly_sha256=w.sha(old),assembly_log_sha256=w.sha(a),syntax_log_sha256=w.sha(s),board_gate_executed=False,overlay_loads=0,rejected_transfer='Compressed reference expansion ran before copying identical compressed dependency from02; original03 assembly rc1, no gate. Transfer frozen compressed payloads explicitly, then same immutable assembler verifies all files; no source/reference changes.')
    out=w.BASE/'runs/M368-video-transfer-02';w.atomic(out/'RESULT.json',w.encoded(r),immutable=True);d=w.sha(out/'RESULT.json')
    w.sync('latest_m368_stage_transfer',dict(status=r['status'],sha256=d,result=(out/'RESULT.json').relative_to(w.ROOT).as_posix(),manifest_sha256=r['manifest_sha256']),f'## M368 03依赖传输闭合\n\n原组装rc1在压缩依赖复制顺序，0Overlay/门禁；旧日志保存。只补传两份已冻结压缩文件，原限长解压/逐文件SHA/白名单及root bash-n通过，包原字节不变。证据SHA `{d}`。下一步只实际纯PS加载身份顺序检查，PASS同步后才能新视频。')
    print(json.dumps(r))


if __name__=='__main__':main()
