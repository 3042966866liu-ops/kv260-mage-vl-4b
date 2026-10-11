"""Actual frozen loader checks only; no Overlay, allocation, or inference."""
import argparse
import importlib.abc
import json
import os
from pathlib import Path
import sys
import traceback
from measurement import sha256,write_json
from m341_build_id_gate import verify_self,service_stopped,STABLE
from frozen_video_identity import module_paths,RELEASE
HERE=Path(__file__).resolve().parent
OUT=Path('/home/ubuntu/m368_identity_preflight_01/RESULT.json')


class NoPynq(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0]=='pynq':raise RuntimeError('Loader identity check forbids PYNQ')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('manifest_sha');parser.add_argument('--enable',action='store_true');args=parser.parse_args()
    if not args.enable or OUT.exists():raise RuntimeError('Disabled/immutable; collect only')
    r=dict(status='FAIL_LOADER_IDENTITY_SEQUENCE',manifest_sha256=args.manifest_sha,gate_return_code=1,errors=[],overlay_loads=0,allocations=0,forward_calls=0,fpga_transactions=0)
    blocker=NoPynq();sys.meta_path.insert(0,blocker)
    server=None
    try:
        if os.geteuid()!=0:raise RuntimeError('Same-terminal root required')
        verify_self(HERE,args.manifest_sha);r['service']=service_stopped()
        closure=json.loads((HERE/'SOURCE_CLOSURE.json').read_text(encoding='utf-8'))
        for row in closure['files']:
            if sha256(RELEASE/row['path'])!=row['sha256']:raise RuntimeError('Source identity drift')
        sys.path[:0]=[str(p) for p in module_paths()]
        import m276_m254_video_server
        import video_server as server
        for name,relative in closure['modules'].items():
            if name in sys.modules and Path(sys.modules[name].__file__).resolve()!=(RELEASE/relative).resolve():raise RuntimeError('Resolved module drift:'+name)
        if server.BUILD_ID!='0x4D395832':raise RuntimeError('Original release identity differs')
        d=RELEASE/'deployment/mage_vl4b'
        config=server.make_config(d/'m181_m120_video_board_candidate',STABLE,RELEASE/'external_assets/weights',RELEASE/'tmp/m223_realtime/m223_realtime_delta/M223_PREDECESSOR_SUMMARY.json')
        first=server.offline_preflight(config)
        if first['status']!='PASS' or not all(first['checks'].values()):raise RuntimeError('Original stable loader preflight rejected')
        server.BUILD_ID='0x4D333537';bad=server.offline_preflight(config)
        expected={'m120_fixed_text_board_e2e','m198_optimized_ps_vision','m208_selected_real_board_vision','clean_m120_video_candidate','candidate_manifest_external_hash','m175_text_runtime_package'}
        if bad['status']!='FAIL' or {k for k,v in bad['checks'].items() if not v}!=expected:raise RuntimeError('Early-patch failure not exactly reproduced')
        server.BUILD_ID='0x4D395832';restored=server.offline_preflight(config)
        if restored!=first:raise RuntimeError('Release preflight restoration differs')
        r.update(original=first,early_candidate_patch_rejected=bad,restored=restored,no_PYNQ_import='pynq' not in sys.modules,actual_preflight_source_sha256=sha256(Path(server.__file__)),status='PASS_ACTUAL_LOADER_IDENTITY_SEQUENCE',gate_return_code=0)
    except BaseException as exc:r['errors'].append(type(exc).__name__+': '+str(exc));r['traceback']=traceback.format_exc()
    finally:
        if server is not None:server.BUILD_ID='0x4D395832'
        sys.meta_path.remove(blocker);write_json(OUT,r)
    return r['gate_return_code']


if __name__=='__main__':raise SystemExit(main())
