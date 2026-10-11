"""New full-chain decoder/oracle compared with the frozen M128 integer reference."""
import sys
sys.dont_write_bytecode=True
from pathlib import Path
import hashlib
import numpy as np
from m355_reference import full_reference,decode_records

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'deployment/mage_vl4b/m120_text4b_runtime'))
from m120_fixture import load_fixture,build_case,_decode_weights

def main():
    fixture=ROOT/'deployment/mage_vl4b/artifacts/m128_m120_real_record_csim_fixture.bin'
    assert hashlib.sha256(fixture.read_bytes()).hexdigest()=='f384f45eea4bc14110a7add49dd0944f0a025403aecc3360369ec999e28257d9'
    checks=0
    for case in load_fixture(fixture):
        count=len(case.descriptors);built=build_case(case,count);offset=0;descriptors=[]
        for d in case.descriptors:
            descriptors.append(dict(encoded_u64=hex(offset|(8<<32)|(case.bits<<42)),rows_per_shard=8))
            offset+=case.groups*d.words
            for raw in d.shard_records:
                records=np.frombuffer(raw,np.uint8).reshape(case.groups,17,16)[:,:d.words].copy()
                codes,scales=decode_records(records.tobytes(),case.groups,8,case.bits)
                for g in range(case.groups):
                    original,scale=_decode_weights(records[g],case.bits)
                    assert np.array_equal(codes[g],original)
                    assert np.array_equal(scales[g].astype(np.float32),scale)
        chain=dict(groups=case.groups,bits=case.bits,descriptors=descriptors,output_bytes=built['output_bytes'])
        expected=np.frombuffer(built['expected'],'<u2').copy()
        mask=((expected&0x7c00)==0)&((expected&0x03ff)!=0);expected[mask]&=np.uint16(0x8000)
        observed=full_reference(chain,built['weights'],0,built['packet'])
        assert observed==expected.tobytes(),case.ordinal
        checks+=1
    print('M355_REFERENCE_PASS frozen_real_record_full_cases='+str(checks))
    return checks

if __name__=='__main__':main()
