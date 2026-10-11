"""Derive measured development metrics from collected full board evidence only."""
import argparse
from collections import defaultdict
import json
import math
from pathlib import Path
from measurement import sha256,write_json


def summarize(board):
    result=dict(status='INCOMPLETE',scope='Single development request; not formal statistics',
        achieved_level=None,numerical_acceptance=False,quality_acceptance=False,
        errors=board.get('errors',[]),metrics=None)
    request=board.get('request',{});generation=request.get('generation',{})
    if board.get('status')!='PROVISIONAL' or request.get('status')!='PASS':return result
    if board.get('timing_eligible') is False or request.get('timing_eligible') is False:
        result['status']='DIAGNOSTIC_NOT_PERFORMANCE';return result
    if not board.get('fpga_execution_verified') or not board.get('boot_unchanged') or not board.get('cmdline_unchanged'):
        raise ValueError('Missing hardware/rollback proof')
    if not board.get('cleanup',{}).get('buffers_released'):raise ValueError('Missing safe cleanup')
    if generation.get('status')!='PASS' or generation.get('cpu_linear_fallback') is not False:
        raise ValueError('Generation/fallback check failed')
    stages=generation['top_level_stages'];start=generation['start_ns'];end=generation['end_ns']
    cursor=start;total=0;times=defaultdict(float)
    for stage in sorted(stages,key=lambda r:r['start_ns']):
        begin,finish=stage['start_ns'],stage['end_ns']
        if begin<cursor or finish<begin or finish>end:raise ValueError('Invalid/overlapping stage')
        total+=finish-begin;times[stage['name']]+=(finish-begin)/1e9;cursor=finish
    wall=(end-start)/1e9
    if abs(total/1e9-wall)>max(.1,.01*wall):raise ValueError('Stage closure mismatch')
    valid=[e for e in generation['raw_token_events'] if e['kind']=='valid']
    if not valid:raise ValueError('No valid output')
    if any(b['ready_ns']<=a['ready_ns'] for a,b in zip(valid,valid[1:])):raise ValueError('Nonmonotonic token time')
    ttft=(valid[0]['ready_ns']-start)/1e9
    decode_interval=(valid[-1]['ready_ns']-valid[0]['ready_ns'])/1e9
    tps=(len(valid)-1)/decode_interval if len(valid)>1 else None
    if ttft<0 or valid[-1]['ready_ns']>end:raise ValueError('Token outside request')
    if len(valid)!=generation['output_tokens'] or not math.isclose(ttft,generation['ttft_s'],abs_tol=1e-9):
        raise ValueError('Token count/TTFT differs from raw events')
    reported=generation['decode_tps']
    if ((tps is None)!=(reported is None) or
        (tps is not None and not math.isclose(tps,reported,rel_tol=1e-12,abs_tol=1e-12))):
        raise ValueError('Decode metric differs from raw events')
    evidence=board['board_evidence'];transactions=board['transactions']
    if evidence['host_calls']!=len(transactions) or any(t['ap_return']!=0x4D395832 for t in transactions):
        raise ValueError('Physical transaction identity mismatch')
    if evidence['host_calls']!=evidence['logical_calls']+evidence['scale_retry_count']:
        raise ValueError('Physical/logical/retry accounting mismatch')
    waits=defaultdict(float)
    for item in transactions:
        key=str(item['current'].get('family','unknown'))
        waits[key]+=item['elapsed_ns']/1e9
    result.update(status='MEASURED_DEVELOPMENT',metrics=dict(ttft_s=ttft,decode_tps=tps,
        output_tokens=len(valid),request_wall_s=wall,load_s=board.get('load_s'),
        stage_seconds=dict(times),stage_closure_error_s=abs(total/1e9-wall),
        physical_calls=len(transactions),logical_calls=evidence['logical_calls'],
        scale_retries=evidence['scale_retry_count'],device_wait_seconds_by_family=dict(waits),
        peak_rss_mib=board.get('resources_after',{}).get('peak_rss_mib')),
        answer=request.get('answer'),input_sha256=request.get('input_sha256'),
        prompt_token_count=request.get('prompt_token_count'),valid_128_tokens=generation.get('valid_128_tokens',False),
        phase_profile_note='Async pack/parse/transfer counters may overlap; do not add them as exclusive percentages',
        formal_request_count=0)
    return result


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--revision',type=int,required=True);args=parser.parse_args()
    root=Path(__file__).resolve().parents[2];base=root/'deployment/mage_vl4b/optimization_v1'
    source=base/f'gates/G01-SYS-development/attempt_{args.revision:02d}/board_result.json'
    out=base/f'runs/OP01-SYS-{args.revision:02d}-summary/result.json'
    if out.exists():raise RuntimeError('Immutable summary exists')
    result=summarize(json.loads(source.read_text()))
    result.update(board_result_sha256=sha256(source),source=str(source.relative_to(root)))
    write_json(out,result);print(json.dumps(result))


if __name__=='__main__':main()
