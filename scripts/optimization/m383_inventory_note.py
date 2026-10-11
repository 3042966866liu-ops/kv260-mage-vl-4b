"""Correct a copied prose file count; immutable transfer/package bytes unchanged."""
from m351_workflow import ROOT,BASE,sha,atomic,encoded,sync
import json
pkg=BASE/'candidates/M383-ps-descriptor-01/PACKAGE_MANIFEST.json';m=json.loads(pkg.read_text(encoding='utf-8'))
assert m['file_count']==27 and m['total_bytes']==189346
for name in ('CURRENT_STATE.md','docsMILESTONES.md'):
    p=ROOT/name;value=p.read_text(encoding='utf-8-sig');a=value.index('## M383 PS单descriptor诊断包传输核对');b=value.find('\n## ',a+4)
    if b<0:b=len(value)
    section=value[a:b];assert '26载荷' in section
    value=value[:a]+section.replace('26载荷','27载荷')+value[b:];atomic(p,value.encode('utf-8'))
out=BASE/'runs/M383-inventory-note-01/RESULT.json';r=dict(status='CORRECTED_COPIED_PROSE_FILE_COUNT',manifest_sha256=sha(pkg),actual_files=27,actual_payload_bytes=189346,old_prose_files=26,package_changed=False,transfer_raw_changed=False,hardware_rerun=False)
atomic(out,encoded(r),immutable=True);d=sha(out)
sync('latest_m383_inventory_note',dict(status=r['status'],result=out.relative_to(ROOT).as_posix(),sha256=d),f'## M383 包数量文字核对\n\nmanifest/板端assembly实际27文件、189,346B；复制模板的传输说明误写26已纠正，两份记录同步。原包和transfer raw未改，没有硬件重跑。核对SHA {d}。')
print(d)
