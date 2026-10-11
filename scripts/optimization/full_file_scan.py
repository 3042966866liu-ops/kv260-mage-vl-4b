"""Two bounded Decode-order weight scans, without model/FPGA allocation."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import time


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def window(layout,chain):
    tiles={(m['module'],int(t['tile_index'])):t for m in layout['modules'] for t in m['tiles']}
    intervals=[]
    for d in chain['descriptors']:
        t=tiles[(d.get('module','lm_head'),int(d['tile_index']))]
        offsets=list(map(int,t['shard_offsets']));size=int(t['record_bytes_per_shard'])
        if len(offsets)!=4 or len(set(offsets))!=1 or offsets[0]%16 or size<=0 or size%16:
            raise RuntimeError('Unsupported tile window')
        if int(d['offset_words'])*16!=offsets[0]:raise RuntimeError('Offset identity mismatch')
        intervals.append((offsets[0],offsets[0]+size))
    return min(a for a,b in intervals),max(b for a,b in intervals)


def unique_bytes(rows):
    total=0
    for path in {r['path'] for r in rows}:
        end=0
        for row in sorted((r for r in rows if r['path']==path),key=lambda r:r['offset']):
            begin=row['offset'];stop=begin+row['bytes']
            total+=max(0,stop-max(begin,end));end=max(end,stop)
    return total


def main():
    script_sha,plan_sha=sys.argv[1:];here=Path(__file__).resolve().parent
    if digest(__file__)!=script_sha or digest(here/'plan.json')!=plan_sha:raise RuntimeError('Probe/plan identity')
    plan=json.loads((here/'plan.json').read_text());dep=here/'file_cache_probe.py'
    if digest(dep)!=plan['probe_dependency_sha256']:raise RuntimeError('Dependency identity')
    spec=importlib.util.spec_from_file_location('file_cache_probe',dep);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    out=here/'result.json'
    if out.exists():raise RuntimeError('Immutable result exists')
    result=dict(status='FAIL',scope='Idle process two full Decode-order file scans; not inference or resident-model proof',
                plan_sha256=plan_sha,script_sha256=script_sha,passes=[],errors=[],
                overlay_loaded=False,model_executed=False,cache_evicted=False)
    try:
        root=Path('/home/ubuntu/tellme_m120_m89x2_20260901');rows=[];order=[]
        for contract in plan['contracts']:
            path=root/'m175_m120_fixed_text_candidate/contracts'/contract['name']
            if digest(path)!=contract['sha256']:raise RuntimeError('Contract hash')
            c=json.loads(path.read_text());layoutroot=root/'m120_fulltext_weights_0x4D395832'/contract['kind']
            manifest=layoutroot/'SIXPORT_LAYOUT_MANIFEST.json'
            if digest(manifest)!=c['source_manifest_sha256']:raise RuntimeError('Layout hash')
            layout=json.loads(manifest.read_text())
            if len(layout['files'])!=4:raise RuntimeError('Shard count')
            for chain in c['chains']:
                order.append(dict(chain_index=chain['chain_index'],layer=chain.get('layer'),family=chain.get('family','lm_head')))
                begin,end=window(layout,chain)
                if not 0<end-begin<=8*1024*1024:raise RuntimeError('Chunk bound')
                for shard,item in enumerate(layout['files']):
                    path=layoutroot/item['path']
                    if item['path']!=f'weights{shard}.bin' or path.stat().st_size!=item['bytes'] or end>item['bytes']:
                        raise RuntimeError('Shard identity/size')
                    rows.append(dict(path=str(path),offset=begin,bytes=end-begin,chain=len(order)-1,shard=shard))
        if order!=plan['expected_order'] or len(rows)!=648 or sum(r['bytes'] for r in rows)!=plan['expected_stage_bytes']:
            raise RuntimeError('Observed Decode order/byte count differs')
        result.update(total_bytes_per_pass=sum(r['bytes'] for r in rows),unique_bytes_per_pass=unique_bytes(rows),
            read_calls_per_pass=len(rows),minimum_chunk_bytes=min(r['bytes'] for r in rows),maximum_chunk_bytes=max(r['bytes'] for r in rows),
            windows=rows,meminfo_before=Path('/proc/meminfo').read_text())
        hashes=[]
        for iteration in range(2):
            records=[];wall=time.perf_counter_ns()
            for index,row in enumerate(rows):
                path=Path(row['path']);before_resident=module.resident(path,row['offset'],row['bytes'])
                before=module.snapshot();start=time.perf_counter_ns()
                with path.open('rb',buffering=0) as stream:
                    stream.seek(row['offset']);payload=stream.read(row['bytes'])
                read_ns=time.perf_counter_ns()-start;after=module.snapshot()
                if len(payload)!=row['bytes']:raise RuntimeError('Short read')
                hash_start=time.perf_counter_ns();actual=hashlib.sha256(payload).hexdigest();hash_ns=time.perf_counter_ns()-hash_start
                if iteration==0:hashes.append(actual)
                elif hashes[index]!=actual:raise RuntimeError('Repeated scan byte mismatch')
                del payload
                records.append(dict(index=index,read_ns=read_ns,hash_ns=hash_ns,sha256=actual,
                    residency_before=before_resident,io_delta={k:after[k]-before[k] for k in before}))
                if index%128==0:print(f'FULL_SCAN_PROGRESS pass={iteration} windows={index}/{len(rows)}',flush=True)
            result['passes'].append(dict(iteration=iteration,wall_s=(time.perf_counter_ns()-wall)/1e9,
                read_s=sum(r['read_ns'] for r in records)/1e9,hash_s=sum(r['hash_ns'] for r in records)/1e9,
                storage_read_bytes=sum(r['io_delta']['read_bytes'] for r in records),rchar=sum(r['io_delta']['rchar'] for r in records),
                records=records,meminfo_after=Path('/proc/meminfo').read_text()))
        result['status']='MEASURED'
    except Exception as exc:result['errors'].append(repr(exc))
    temporary=out.with_suffix('.partial');temporary.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');os.replace(temporary,out)
    summary={k:v for k,v in result.items() if k not in ('windows','meminfo_before','passes')}
    summary['passes']=[{k:v for k,v in p.items() if k not in ('records','meminfo_after')} for p in result['passes']]
    summary['result_sha256']=digest(out)
    print('FULL_SCAN_JSON_BEGIN');print(json.dumps(summary));print('FULL_SCAN_JSON_END',flush=True)
    return 0 if result['status']=='MEASURED' else 1


if __name__=='__main__':raise SystemExit(main())
