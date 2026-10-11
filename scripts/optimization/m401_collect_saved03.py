"""Saved-only host destination repair. No UART, gate or board execution."""
import ast
import json
from m351_workflow import ROOT,HERE,BASE,sha,atomic,encoded,sync
from m401_collect02 import decode

def main():
    log=ROOT/'tmp/m40102/component_uart.log'
    assert sha(BASE/'runs/M401-tail-text-board-01/BOARD_RESULT.json')=='9530a03974a7b330be21f39e07eaea1ef4c1eb53eacc86f89a155054994d9ca9'
    text=log.read_text(encoding='utf-8-sig')
    digest,raw,r=decode(text)
    assert digest=='e4ffe98c1deed4863701a783a90f2b1272cbbd7eb71136f37e0a38238d52da85'
    assert 'M401_DONE case=B1 gate_rc=0 export_rc=0' in text and '__M401_COMPONENT_RC_0__' in text
    assert r['common_runner_sha256']==sha(BASE/'candidates/M401-tail-text-02/m401_tail_text_gate.py')
    out=BASE/'runs/M401-tail-text-board-02/BOARD_RESULT.json'
    atomic(out,raw,immutable=True)
    # Freeze the original log and recovery receipt before synchronizing the gate.
    atomic(out.parent/'ORIGINAL_UART.log',log.read_bytes(),immutable=True)
    receipt=dict(status='PASS_SAVED_ONLY_HOST_COLLECTION_PATH_REPAIR',raw_sha256=digest,original_uart_sha256=sha(log),
        source_decoder_sha256=sha(HERE/'m401_collect02.py'),recovery_source_sha256=sha(HERE/'m401_collect_saved03.py'),
        corrected_destination=out.relative_to(ROOT).as_posix(),original_failed_result_unchanged=True,
        gate_rc=0,export_rc=0,hardware_reexecuted=False,board_commands_sent=0)
    path=BASE/'runs/M401-tail-text-collection-repair-03/RESULT.json';atomic(path,encoded(receipt),immutable=True)
    sync('latest_m401_tail_text_board',dict(status=r['status'],result=out.relative_to(ROOT).as_posix(),sha256=digest,fixed_text_numerical_pass=True,performance_pass=False,formal_promotion_allowed=False),
        f'## M401 末层候选完整固定文本结果02（2026-10-04）\n\nBuild0x4D333537，gate/export rc0，raw `{digest}`。1230块≤900B全部顺序/原SHA及严格数值decode通过：154family、151936logits、72KV、Token17/3重试，162逻辑/165模型物理加minimal166。scope/弱引用/七DMA安全释放与稳定恢复核对。原收集器目标仍指向board01而被拒绝，仅本地保存已收齐原日志到新board02，未重跑硬件。只固定30文本，无新视频/性能或生产晋级；下一步本级闭合。')
    sync('latest_m401_tail_text_collection_repair',dict(status=receipt['status'],result=path.relative_to(ROOT).as_posix(),sha256=sha(path),raw_sha256=digest),
        f'## M401 已保存结果主机路径修复（2026-10-04）\n\n{sha(path)}。旧collector完成严格decode后原子写入仍指向旧失败目录，被immutable检查拒绝。新saved-only收集只修本地目标，原01/02包与控制器/旧collector不改，无UART或硬件重执行；raw `{digest}` 已同步。')
    print(json.dumps(receipt))

if __name__=='__main__':main()
