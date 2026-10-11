"""Bind verified transfer markers before any staged-layer execution."""
import json
import m351_workflow as w
from m36603_collect import PKG
def main():
    a=(w.ROOT/'tmp/m36603/assembly.log').read_text(encoding='utf-8-sig');s=(w.ROOT/'tmp/m36603/root_syntax.log').read_text(encoding='utf-8-sig')
    assert 'M366_ALL_PAYLOAD_SHA_VERIFIED_NO_GATE' in a and '__M366_ASSEMBLY_RC_0__' in a and '__M366_SYNTAX_RC_0__' in s
    result=dict(status='PASS_M366_STAGE_PACKAGE_TRANSFER_ONLY',manifest_sha256=w.sha(PKG/'PACKAGE_MANIFEST.json'),assembly_log_sha256=w.sha(w.ROOT/'tmp/m36603/assembly.log'),syntax_log_sha256=w.sha(w.ROOT/'tmp/m36603/root_syntax.log'),board_gate_executed=False,overlay_loads=0)
    out=w.BASE/'runs/M366-staged-text-transfer-02';w.atomic(out/'RESULT.json',w.encoded(result),immutable=True);digest=w.sha(out/'RESULT.json')
    w.sync('latest_m366_stage_transfer',dict(status=result['status'],sha256=digest,result=(out/'RESULT.json').relative_to(w.ROOT).as_posix(),manifest_sha256=result['manifest_sha256']),f'## M366 固定文本诊断包传输\n\nmanifest-first/900B新字节，已冻结M366-02同SHA依赖只读复制，全部载荷白名单/大小/逐SHA及root bash-n通过，0Overlay/forward/FPGA。证据SHA `{digest}`。下一步只一次固定文本诊断，原结果存在Collect，不自动文本/视频。')
    print(result['status'],digest)
if __name__=='__main__':main()
