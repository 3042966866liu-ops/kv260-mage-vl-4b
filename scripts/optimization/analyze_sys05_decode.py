"""Analyze collected SYS05 only; never run inference or fabricate missing spans."""
import json
from pathlib import Path
from measurement import sha256,write_json
from summarize_decode_trace import summarize


def analyze(board):
    if board['status']!='PROVISIONAL' or board.get('timing_eligible') is not False:
        raise ValueError('Expected completed diagnostic-only request')
    if not board['fpga_execution_verified'] or not board['cleanup']['buffers_released']:
        raise ValueError('Missing execution/cleanup proof')
    diagnosis=board['decode_diagnostic']
    if len(diagnosis['steps'])!=1:raise ValueError('Expected exactly one Decode')
    record=diagnosis['steps'][0];result=summarize(record)
    if len(result['families'])!=154 or {f['layer'] for f in result['families']}!=set(range(36)):
        raise ValueError('Incomplete 36-layer family trace')
    if result['counters']['logical_calls']!=162:raise ValueError('Wrong Decode call plan')
    generation=board['request']['generation']
    if generation['kv_lengths']!=[852,853] or generation['valid_token_ids'][0]!=1291:
        raise ValueError('Fixed-input Decode identity changed')
    if generation['prefill_count']!=1 or generation['decode_count']!=1:
        raise ValueError('Not one prefill and one incremental Decode')
    checkpoint=diagnosis['checkpoint']
    if checkpoint['status']!='RECORDED' or checkpoint['next_token']!=1291:
        raise ValueError('Missing matching Prefill checkpoint')
    if len(checkpoint['files'])!=72 or len(checkpoint['geometry']['layers'])!=36:
        raise ValueError('Incomplete real KV checkpoint')
    stages=[r for r in generation['top_level_stages'] if r['name']=='decode_1']
    if len(stages)!=1:raise ValueError('Missing outer Decode boundary')
    outer=(stages[0]['end_ns']-stages[0]['start_ns'])/1e9
    if outer<result['decode_call_s']:raise ValueError('Inner time exceeds outer boundary')
    physical=result['counters']['host_calls']
    transactions=board['transactions'][-physical:]
    if len(transactions)!=physical or any(r['ap_return']!=0x4D395832 for r in transactions):
        raise ValueError('Wrong physical Decode identity')
    result.update(outer_decode_s=outer,wrapper_outside_inner_s=outer-result['decode_call_s'],
                  recorded_wait_s=sum(r['elapsed_ns'] for r in transactions)/1e9,
                  checkpoint_save_s=checkpoint['save_ns']/1e9,
                  checkpoint_files=72,original_SYS02_decode_s=97.141342925,
                  comparison_scope='Instrumented rerun; no speedup claim, checkpoint can perturb file cache',
                  phase_ms_delta_may_overlap=record.get('phase_ms_delta',{}))
    return result


if __name__=='__main__':
    root=Path(__file__).resolve().parents[2];base=root/'deployment/mage_vl4b/optimization_v1'
    source=base/'gates/G01-SYS-development/attempt_05/board_result.json'
    output=base/'runs/OP01-SYS05-decode-attribution/result.json'
    if output.exists():raise RuntimeError('Immutable attribution already exists')
    result=analyze(json.loads(source.read_text()))
    result['source_sha256']=sha256(source)
    write_json(output,result)
    print(json.dumps(result))
