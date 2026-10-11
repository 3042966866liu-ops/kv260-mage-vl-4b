"""Versioned bounded compressed transfer; original reference bytes unchanged."""
import ast
import json
import shutil
import zlib
import m351_workflow as w


def main():
    old=w.BASE/'candidates/M368-staged-video-01';pkg=w.BASE/'candidates/M368-staged-video-02';out=w.BASE/'runs/M368-video-support-02'
    if pkg.exists() or out.exists():raise RuntimeError('Immutable compact preparation exists')
    for p in old.iterdir():
        if p.name not in ('SHA256SUMS','PACKAGE_MANIFEST.json'):pkg.mkdir(exist_ok=True);shutil.copyfile(p,pkg/p.name)
    refs=('VIDEO_EXPECTED.json','VISUAL_EXPECTED.json')
    for name in refs:w.atomic(pkg/(name+'.zlib'),zlib.compress((pkg/name).read_bytes(),9))
    source=(pkg/'m368_assemble.py').read_text(encoding='utf-8')
    source=source.replace('import sys','import sys\nimport zlib\nimport os')
    anchor="        if not target.exists():\n            srcrow=bysha.get(row['sha256'])"
    replacement="""        if not target.exists() and row['path'] in ('VIDEO_EXPECTED.json','VISUAL_EXPECTED.json'):
            compressed=ROOT/(row['path']+'.zlib')
            compressed_row=next(r for r in new['files'] if r['path']==compressed.name)
            if sha(compressed)!=compressed_row['sha256'] or compressed.stat().st_size!=compressed_row['bytes']:raise RuntimeError('Compressed reference identity differs')
            decoder=zlib.decompressobj();raw=decoder.decompress(compressed.read_bytes(),row['bytes']+1)
            if len(raw)!=row['bytes'] or not decoder.eof or decoder.unused_data or decoder.unconsumed_tail or hashlib.sha256(raw).hexdigest()!=row['sha256']:raise RuntimeError('Reference expansion bounds/SHA differs')
            temporary=target.with_name(target.name+'.expand-part')
            with temporary.open('wb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
            os.replace(temporary,target)
        if not target.exists():
            srcrow=bysha.get(row['sha256'])"""
    assert source.count(anchor)==1;source=source.replace(anchor,replacement)
    ast.parse(source,feature_version=(3,10));w.atomic(pkg/'m368_assemble.py',source.encode('utf-8'))
    for name in refs:
        raw=(pkg/name).read_bytes();compressed=(pkg/(name+'.zlib')).read_bytes()
        d=zlib.decompressobj();got=d.decompress(compressed,len(raw)+1)
        assert got==raw and d.eof and not d.unused_data and not d.unconsumed_tail and w.sha(pkg/name)==w.sha(old/name)
    rows=[dict(path=p.name,bytes=p.stat().st_size,sha256=w.sha(p)) for p in sorted(pkg.iterdir())]
    w.atomic(pkg/'SHA256SUMS',''.join(x['sha256']+'  '+x['path']+'\n' for x in rows).encode('ascii'))
    rows.append(dict(path='SHA256SUMS',bytes=(pkg/'SHA256SUMS').stat().st_size,sha256=w.sha(pkg/'SHA256SUMS')))
    w.atomic(pkg/'PACKAGE_MANIFEST.json',w.encoded(dict(schema='m368-independent159-video-capacity-v2',files=rows,file_count=len(rows),total_bytes=sum(x['bytes'] for x in rows))))
    control=(w.HERE/'m368_control.ps1').read_text(encoding='utf-8').replace('M368-staged-video-01','M368-staged-video-02').replace('M368-video-support-01','M368-video-support-02').replace('m368_staged_video_candidate_01','m368_staged_video_candidate_02')
    control=control.replace('$_.sha256 -notin $taskOldHashes',"$_.sha256 -notin $taskOldHashes -and $_.path -notin @('VIDEO_EXPECTED.json','VISUAL_EXPECTED.json')")
    w.atomic(w.HERE/'m368_control.ps1',control.encode('utf-8'))
    collect=(w.HERE/'m368_collect.py').read_text(encoding='utf-8').replace('M368-staged-video-01','M368-staged-video-02').replace('独立固定文本容量诊断','独立固定视频容量诊断');w.atomic(w.HERE/'m368_collect.py',collect.encode('utf-8'))
    prior=w.BASE/'runs/M368-video-support-01/RESULT.json';r=json.loads(prior.read_text(encoding='utf-8'));r['manifest_sha256']=w.sha(pkg/'PACKAGE_MANIFEST.json');r['prior_support_sha256']=w.sha(prior)
    r['rejected_transfer_draft']='01 not uploaded/executed; uncompressed references395KiB inefficient on UART.02 identical gate/reference bytes, bounded zlib expansion validated before assembly SHA; original01 preserved.'
    r['compressed_reference_bytes']={name:(pkg/(name+'.zlib')).stat().st_size for name in refs}
    r['decompressed_reference_sha_unchanged']=True
    w.atomic(out/'RESULT.json',w.encoded(r),immutable=True);d=w.sha(out/'RESULT.json')
    w.sync('latest_m368_video_support',dict(status=r['status'],sha256=d,result=(out/'RESULT.json').relative_to(w.ROOT).as_posix(),manifest_sha256=r['manifest_sha256']),f'## M368 视频诊断02传输组织\n\n01未上传执行，仅参考JSON传输较大；02保留门禁/预算/全部参考原字节，压缩传输后限长解压、eof/尾数据/原SHA核对，再执行逐文件白名单验证。支持SHA `{d}`，前级31项规则及同SHA硬件/完整head观察器复用。稳定核输入政策保持，尚未视频上板。')
    print(json.dumps(r))


if __name__=='__main__':main()
