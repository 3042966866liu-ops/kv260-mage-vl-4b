"""Saved upload receipts and assembly-only recovery; never repeats upload/gate."""
import json
import sys
from m351_workflow import ROOT,HERE,BASE,sha,atomic,encoded,sync
from m403_prepare import PKG,OLD


def check_receipts():
    m=json.loads((PKG/'PACKAGE_MANIFEST.json').read_bytes());prior={r['path']:r for r in json.loads((OLD/'PACKAGE_MANIFEST.json').read_bytes())['files']}
    names=['PACKAGE_MANIFEST.json']+[r['path'] for r in m['files'] if prior.get(r['path'])!=r]
    import re
    for n in names:
        stem='upload_'+n.replace('.','_');size=(PKG/n).stat().st_size;count=(size+899)//900
        final=ROOT/'tmp/m403'/(stem+'_final.log');text=final.read_text(encoding='utf-8-sig')
        assert 'M212_CHUNKED_FILE_PASS' in text and sha(PKG/n) in text
        paths=sorted((ROOT/'tmp/m403').glob(stem+'_chunk_*.log'));assert len(paths)==count
        for i,p in enumerate(paths,1):assert re.search(r'M212_CHUNK_PASS\s+'+str(i)+r'\s+'+str(count)+r'\s+'+str(min(i*900,size))+r'\s',p.read_text(encoding='utf-8-sig'))
    board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    for key in ('latest_m403_tail_performance_preparation','latest_m403_tail_performance_support03'):
        e=board[key];assert e['manifest_sha256']==sha(PKG/'PACKAGE_MANIFEST.json') and sha(ROOT/e['result'])==e['sha256']
        assert all(e['sha256'] in (ROOT/n).read_text(encoding='utf-8') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    support=json.loads((ROOT/board['latest_m403_tail_performance_support03']['result']).read_bytes())
    for n,h in support['source_sha256'].items():assert sha(HERE/n)==h
    print('M403_ALL_NEW_UPLOAD_RECEIPTS_PASS',len(names),sha(PKG/'PACKAGE_MANIFEST.json'))
    return len(names)


def record_block():
    count=check_receipts();log=ROOT/'tmp/m403/assembly_uart.log';text=log.read_text(encoding='utf-8-sig')
    assert 'sudo: a password is required' in text and '__M403_ASSEMBLY_RC_1__' in text
    value=dict(status='STOP_SUDO_EXPIRED_AFTER_ALL_UPLOADS',log=log.relative_to(ROOT).as_posix(),log_sha256=sha(log),manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),uploaded_files=count,new_file_SHA_verified=True,assembly_return_code=1,assembly_started=False,overlay_loaded=False,model_forward_calls=0,fpga_transactions=0,new_board_resources=False,performance_pass=False)
    out=BASE/'runs/M403-assembly-authorization-01/RESULT.json';atomic(out,encoded(value),immutable=True);h=sha(out)
    sync('latest_m403_authorization',dict(status=value['status'],result=out.relative_to(ROOT).as_posix(),sha256=h),f'## M403 全载荷上传后组装授权过期（2026-10-04）\n\nSHA {h}；manifest-first全部{count}新文件及900B全部回执/完整SHA严格通过。最终root组装sudo需要密码，原rc1，未执行assembler/Overlay/模型/FPGA，无新资源；旧日志/包不改。等待用户同COM3续期后，只用assembly-only恢复完成现有包，不重新上传或完整模型。')
    print(value['status'],h)


if __name__=='__main__':
    if sys.argv[1:]==['Check']:check_receipts()
    elif sys.argv[1:]==['RecordBlock']:record_block()
    else:raise SystemExit('Check | RecordBlock')
