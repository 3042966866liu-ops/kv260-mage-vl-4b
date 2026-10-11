"""Strict original-byte layer recovery, including exact new-bit configuration proof."""
import argparse
import json
from pathlib import Path
import m351_workflow as w
from m441_host_io08 import atomic
from m443_configuration01 import validate_record

PKG = w.BASE/'candidates/M443-fixed-text-01'
PREP = w.BASE/'runs/M443-fixed-text-preparation-01/RESULT.json'
SOURCE_SHA = None


def decode(log):
    prep = json.loads(PREP.read_bytes())
    source = (w.HERE/'m36603_collect.py').read_text(encoding='utf-8')
    # The support receipt freezes this shared decoder's exact source as well.
    source = source[:source.index('\ndef collect(')]
    source = source.replace('M366-staged-text-03','M443-fixed-text-01').replace('M366','M443T').replace('0x4D333537','0x4D343433').replace('0x4d333537','0x4d343433')
    namespace = {'__name__': '_m443_proven_layer_decoder01'}
    exec(compile(source,'<derived-proven-layer-decoder01>','exec'),namespace)
    digest,raw,r = namespace['decode'](log)
    if r['status'] == 'PASS_M443T_FIXED_TEXT_DIAGNOSTIC':
        if r.get('prior_board_sha256') != prep['prior_raw_sha256'] or r.get('configuration_application_build_raw_sha256') != prep['configuration_build_raw_sha256']:
            raise ValueError('Actual complete chain/configuration origin differs')
        if r.get('source_compatibility_checked_before_overlay') is not True or r.get('additional_cma_requests_allowed') is not False:
            raise ValueError('Source check or allocation seal absent')
        if r.get('configuration_application_accepted') is not True or r.get('unknown_configuration_ownership') is not False:
            raise ValueError('Actual configuration incomplete/unknown')
        if r.get('prior_single_layer_raw_sha256') != prep['prior_single_layer_raw_sha256'] or r.get('head_AST_checked_before_overlay') is not True:
            raise ValueError('Actual layer/head AST admission differs')
        application_sha = w.sha(PKG/'CONFIGURATION_APPLICATION.json')
        validate_record(r['configuration_record'],application_sha,prep['candidate_manifest_sha256'])
        for name,key,status in (('M443_BUILD_CONFIGURATION_PROOF.json','configuration_build_raw_sha256','PASS_M443_BUILDID'),
                                ('M443_CHAIN_PREREQUISITE.json','prior_raw_sha256','PASS_M443_CHAIN')):
            p=PKG/name; proof=json.loads(p.read_bytes())
            if w.sha(p)!=prep[key] or proof['status']!=status or proof['gate_return_code']!=0:
                raise ValueError('Frozen actual board prerequisite differs')
            validate_record(proof['configuration_record'],application_sha,prep['candidate_manifest_sha256'])
    return digest,raw,r


def collect(path):
    digest,raw,r=decode(path.read_text(encoding='utf-8-sig'))
    out=w.BASE/'runs/M443-fixed-text-board-01'
    atomic(out/'BOARD_RESULT.json',raw,immutable=True)
    atomic(out/'COLLECTION.json',w.encoded(dict(raw_sha256=digest,log_path=path.relative_to(w.ROOT).as_posix(),log_sha256=w.sha(path),collector_sha256=w.sha(Path(__file__)),gate_return_code=r['gate_return_code'],reexecuted=False)),immutable=True)
    w.atomic=atomic
    w.sync('latest_m443_fixed_text_board01',dict(status=r['status'],result=(out/'BOARD_RESULT.json').relative_to(w.ROOT).as_posix(),sha256=digest,build_id='0x4D343433',numerical_pass=r['numerical_pass'],performance_pass=False),
           '## M443独立固定文本板端闭合01（2026-10-11）\n\n'+r['status']+'；原rc'+str(r['gate_return_code'])+'，raw SHA '+digest+'；完整原runtime驻留/七缓冲、原30token/36层/154family/151936logits/72KV/retry原逐位参考及物理提交核对；新bit独立同PID配置原trace、安全完成释放及稳定恢复。PS预算和原累计计数不改，非完整模型/视频/性能或晋级；失败只停本级，PASS后下一步独立固定文本支持准备。')
    print(r['status'],digest,'released',len(r['released_buffers']),'unsafe',r['unsafe_buffers_retained'])
    return r['gate_return_code']


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('log',type=Path);a=p.parse_args();raise SystemExit(collect(a.log.resolve()))
