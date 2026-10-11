import json
import m351_workflow as w

def main():
    pkg=w.BASE/'candidates/M369-light-video-01';m=json.loads((pkg/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))
    old=json.loads((w.BASE/'candidates/M368-staged-video-03/PACKAGE_MANIFEST.json').read_text(encoding='utf-8'));hashes={r['sha256'] for r in old['files']}
    names=['PACKAGE_MANIFEST.json']+[r['path'] for r in m['files'] if r['sha256'] not in hashes]
    logs={}
    for name in names:
        p=w.ROOT/'tmp/m369'/('upload_'+name.replace('.','_')+'_final.log')
        text=p.read_text(encoding='utf-8-sig')
        if 'M212_CHUNKED_FILE_PASS' not in text or w.sha(pkg/name) not in text:raise RuntimeError('Upload receipt incomplete: '+name)
        logs[name]=dict(path=p.relative_to(w.ROOT).as_posix(),sha256=w.sha(p))
    assembly=w.ROOT/'tmp/m369/assembly.log';syntax=w.ROOT/'tmp/m369/root_syntax.log'
    if 'M369_ALL_PAYLOAD_SHA_VERIFIED_NO_GATE' not in assembly.read_text(encoding='utf-8-sig') or '__M369_SYNTAX_RC_0__' not in syntax.read_text(encoding='utf-8-sig'):raise RuntimeError('Assembly/syntax incomplete')
    out=w.BASE/'runs/M369-light-video-transfer-01'
    r=dict(status='PASS_MANIFEST_AND_ALL_PAYLOAD_SHA_NO_GATE',manifest_sha256=w.sha(pkg/'PACKAGE_MANIFEST.json'),uploaded=names,logs=logs,assembly_sha256=w.sha(assembly),syntax_sha256=w.sha(syntax),file_count=m['file_count'],total_bytes=m['total_bytes'],board_executed=False)
    w.atomic(out/'RESULT.json',w.encoded(r),immutable=True);digest=w.sha(out/'RESULT.json')
    w.sync('latest_m369_light_video_transfer',dict(status=r['status'],sha256=digest,result=(out/'RESULT.json').relative_to(w.ROOT).as_posix(),manifest_sha256=r['manifest_sha256']),f'## M369 上板包传输核对\n\n证据SHA `{digest}`；manifest-first 900B分块，全部{m["file_count"]}载荷SHA/字节/白名单和root bash-n通过。仅包传输，下一步唯一一次ABBABAAB原请求测量。')
    print(json.dumps(r))

if __name__=='__main__':main()
