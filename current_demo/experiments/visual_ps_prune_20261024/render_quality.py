"""Reuse unchanged frozen natural-answer generator, with new feature inputs."""
import sys
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import *

def main():
    file=H/'quality.py';assert not file.exists()
    source=ROOT/'experiments/visual_early_pl_20261024/quality_native_features.py'
    s=source.read_text(encoding='utf-8')
    old="PREP=R/'M523-V12-native-feature-language-protocol-01/RESULT.json';OUT=R/'M523-V12-native-feature-language-01'"
    assert s.count(old)==1
    s=s.replace(old,"PREP=R/'M523-PS-V2-V3-V6-3072-protocol-01/RESULT.json';OUT=R/'M523-PS-V2-V3-V6-3072-quality-01'")
    old="    p=read(PREP)\n    for n,h in p['frozen'].items():assert sha(ROOT/n)==h,n"
    new="""    p=read(PREP)
    for n,h in p['frozen'].items():assert sha(ROOT/n)==h,n
    feature_root=R/'M523-PS-V2-V3-V6-3072-features-01'
    feature_result=read(feature_root/'RESULT.json')
    assert feature_result['original_rc']==0 and feature_result['feature_gate_pass'],'Complete feature gate must pass first'
    for row in feature_result['files']:assert sha(feature_root/row['path'])==row['sha256']
    for request in p['requests']:
        request['features']={arm:dict(path=(feature_root/arm/request['id']/'features_FP32.npy').relative_to(ROOT).as_posix(),sha256=sha(feature_root/arm/request['id']/'features_FP32.npy')) for arm in ('A','B')}
"""
    assert s.count(old)==1;s=s.replace(old,new)
    s=s.replace('V12_NATIVE_FEATURE','PS_V236_3072_FEATURE').replace('Actual native current22 A/B visual features','WSL actual PS runtime plus unchanged late M455 oracle current22/PS3072 A/B features')
    s=s.replace('native_feature_sha256','software_feature_sha256').replace('The vision evidence is real M455/A53.','The vision evidence is explicitly software PS plus late M455 oracle; native A53 validation is pending.')
    s=s.replace('injected actual native A/B visual features','injected new software A/B visual features')
    compile(s,str(file),'exec');file.write_bytes(s.encode())
    print('QUALITY_GENERATOR_RENDERED',sha(file),flush=True)
if __name__=='__main__':main()
