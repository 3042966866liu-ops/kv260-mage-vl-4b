"""Compare new host fixture to saved RTL traces, without rerunning simulation."""
import hashlib
from pathlib import Path
from decode_one_board_protocol import referenced_descriptor
from measurement import sha256, write_json

root=Path(__file__).resolve().parents[2]
tv=root/'tmp/op01_decode_one_rtl/hls/sim/tv'

def transactions(path,width):
    result={}; current=None
    with path.open(encoding='ascii') as stream:
        for line in stream:
            line=line.strip()
            if line.startswith('[[transaction]]'):
                current=int(line.split()[-1]); result[current]=bytearray()
            elif line=='[[/transaction]]': current=None
            elif line.startswith('0x'):
                if current is None: raise ValueError('Word outside transaction')
                result[current].extend(int(line,16).to_bytes(width,'little'))
    return {k:bytes(v) for k,v in result.items()}

def main():
    incoming=tv/'cdatafile/c.op01_decode_one_kernel.autotvin_tx_V_data_V.dat'
    outgoing=tv/'rtldatafile/rtl.op01_decode_one_kernel.autotvout_rx_V_data_V.dat'
    tx,rx=transactions(incoming,16),transactions(outgoing,8)
    cases=[]
    for index,mode in [(0,False),(2,True)]:
        fixture=referenced_descriptor(decode_one=mode)
        if fixture['packet']!=tx[index]: raise ValueError('TX mismatch')
        if fixture['expected_output']!=rx[index]: raise ValueError('RX mismatch')
        cases.append(dict(transaction=index,decode_one=mode,input_bytes=len(tx[index]),
            output_bytes=len(rx[index]),output_sha256=hashlib.sha256(rx[index]).hexdigest()))
    out=root/'deployment/mage_vl4b/optimization_v1/runs/OP01-decode-one-board-fixture'
    if out.exists(): raise RuntimeError('Refuse existing evidence')
    out.mkdir()
    write_json(out/'result.json',dict(status='PASS_HOST_FIXTURE_MATCHES_SAVED_RTL',cases=cases,
        sources={str(p.relative_to(root)):sha256(p) for p in [incoming,outgoing,Path(__file__),Path(__file__).with_name('decode_one_board_protocol.py')]},
        board_deployed=False,performance_pass=False))
    for p in [Path(__file__),Path(__file__).with_name('decode_one_board_protocol.py'),Path(__file__).with_name('test_decode_one_board_protocol.py')]:
        (out/p.name).write_bytes(p.read_bytes())
    print('HOST_FIXTURE_SAVED_RTL_MATCH_PASS cases=2 (not board evidence)')

if __name__=='__main__': main()
