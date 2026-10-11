"""Bind uploaded delta and board assembly verification before any Overlay."""
import json
import m351_workflow as w

def main():
    pkg=w.BASE/'candidates/M363-common-load-observer-01';manifest=pkg/'PACKAGE_MANIFEST.json';digest=w.sha(manifest)
    old=json.loads((w.BASE/'candidates/M362-common-load-observer-01/PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))
    oldhashes={x['sha256'] for x in old['files']};new=json.loads(manifest.read_text(encoding='utf-8'))
    logs=w.ROOT/'tmp/m363_board';delta=[]
    for row in [dict(path=manifest.name,sha256=digest,bytes=manifest.stat().st_size)]+[x for x in new['files'] if x['sha256'] not in oldhashes]:
        path=logs/('upload_'+row['path'].replace('.','_')+'_final.log')
        text=path.read_text(encoding='utf-8-sig')
        assert 'M212_CHUNKED_FILE_PASS /home/ubuntu/m363_common_load_observer_01/'+row['path']+' '+str(row['bytes'])+' '+row['sha256'] in text
        delta.append(dict(row,log_sha256=w.sha(path)))
    assembly=logs/'assembly.log';syntax=logs/'root_syntax.log'
    assert f'M363_ASSEMBLY_PASS manifest_sha256={digest} files={new["file_count"]} bytes={new["total_bytes"]}' in assembly.read_text(encoding='utf-8-sig')
    assert '__M363_ASSEMBLY_RC_0__' in assembly.read_text(encoding='utf-8-sig') and '__M363_SYNTAX_RC_0__' in syntax.read_text(encoding='utf-8-sig')
    correction=w.BASE/'runs/M363-correction-support-01/RESULT.json';assert json.loads(correction.read_text(encoding='utf-8'))['status']=='PASS_OFFLINE_ONE_TOKENIZER_CORRECTION'
    result=dict(status='PASS_M363_PACKAGE_TRANSFER_ONLY',manifest_sha256=digest,files=new['file_count'],bytes=new['total_bytes'],delta_uploads=delta,assembly_log_sha256=w.sha(assembly),syntax_log_sha256=w.sha(syntax),correction_support_sha256=w.sha(correction),all_payload_sha_verified_on_board=True,overlay_loaded=False,model_forward_calls=0,fpga_transactions=0)
    out=w.BASE/'runs/M363-transfer-01/RESULT.json';w.atomic(out,w.encoded(result),immutable=True);sha=w.sha(out)
    w.sync('latest_m363_transfer',dict(status=result['status'],sha256=sha,result=out.relative_to(w.ROOT).as_posix()),f'## M363 单次Tokenizer诊断包传输核对\n\n20载荷逐SHA及白名单/字节数、root bash-n通过；新增字节900B分块上传，其余从已核验M362包按SHA复制，旧包不改。前置解析对象复用/文件变化拒绝和17收集负例离线通过，生产源码不改。0Overlay/forward/FPGA；证据SHA `{sha}`。下一步仅A1/B1只加载，64MiB余量保持。')
    print(result['status'],sha)

if __name__=='__main__':main()
