"""Bind successful manifest-first UART file receipts without touching board."""
import json
import m351_workflow as w
from m362_collect_load_comparison import PKG

def main():
    m=json.loads((PKG/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))
    files=[dict(path='PACKAGE_MANIFEST.json',bytes=(PKG/'PACKAGE_MANIFEST.json').stat().st_size,sha256=w.sha(PKG/'PACKAGE_MANIFEST.json'))]+m['files']
    logs=[]
    for row in files:
        name=row['path'].replace('.','_');log=w.ROOT/f'tmp/m362_board/upload_{name}_final.log'
        text=log.read_text(encoding='utf-8-sig');marker=f"M212_CHUNKED_FILE_PASS /home/ubuntu/m362_common_load_observer_01/{row['path']} {row['bytes']} {row['sha256']}"
        assert marker in text and '__M75C_UART_RC_0__' in text
        logs.append(dict(path=log.relative_to(w.ROOT).as_posix(),sha256=w.sha(log)))
    syntax=w.ROOT/'tmp/m362_board/root_syntax.log';assert '__M362_SYNTAX_RC_0__' in syntax.read_text(encoding='utf-8-sig')
    r=dict(status='PASS_UART_TRANSFER_AND_ROOT_BASH_SYNTAX_ONLY',files=len(files),bytes=sum(x['bytes'] for x in files),manifest_sha256=w.sha(PKG/'PACKAGE_MANIFEST.json'),logs=logs,syntax_log_sha256=w.sha(syntax),manifest_first=True,chunk_bytes=900,hardware_gate_executed_by_this_receipt=False,fpga_transactions=0)
    out=w.BASE/'runs/M362-transfer-01/RESULT.json';w.atomic(out,w.encoded(r),immutable=True);digest=w.sha(out)
    w.sync('latest_m362_transfer',dict(status=r['status'],sha256=digest,result=out.relative_to(w.ROOT).as_posix()),f'## M362 只加载观察包传输核对\n\nCOM3 manifest-first、18文件逐SHA与root bash-n通过，900B分块；仅传输核对，非容量或模型/数值/性能。证据SHA `{digest}`。')
    print(r['status'],digest)

if __name__=='__main__':main()
