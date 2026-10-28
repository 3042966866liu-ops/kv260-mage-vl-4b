"""Freeze a quality-first diagnostic after the user's scope correction."""
import ast
import hashlib
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT / 'scripts/optimization'), str(HERE)]
from generate_flap522 import read, sha
from m441_host_io08 import atomic
from m455456_workflow02 import synchronized

R = ROOT / 'deployment/mage_vl4b/optimization_v1/runs'
PREP = R / 'M522-quality-first-ablation-protocol-01'


def save(path, value):
    atomic(path, (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode(), immutable=True)


def replace_once(source, old, new):
    assert source.count(old) == 1, old[:120]
    return source.replace(old, new)


def main():
    assert not PREP.exists()
    # Read all authoritative recovery text; retain exact identities for this decision.
    docs = {}
    for name in ('CURRENT_STATE.md', 'docsMILESTONES.md', 'DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md'):
        path = ROOT / name
        text = path.read_text(encoding='utf-8-sig')
        docs[name] = dict(sha256=sha(path), characters=len(text), lines=len(text.splitlines()))
    board = read(ROOT / 'deployment/mage_vl4b/BOARD_GATE_RESULT.json')
    board_refs = {k: v for k, v in board.items() if k.startswith('latest_m522')}
    old_prep = R / 'M522-flap50-recovery-quality-protocol-01/RESULT.json'
    p = read(old_prep)
    failure = R / 'M522-flap50-recovery-quality-01/COLLECTION.json'
    failed = read(failure)
    assert failed['summary']['training']['newly_wrong'] == 1
    assert failed['summary']['development']['requests'] == 0
    assert read(R / 'M522-flap50-recovery-quality-host-01/COLLECT_EXIT.json')['original_rc'] == 0
    source = HERE / 'quality_recovery_flap522.py'
    s = source.read_text(encoding='utf-8')
    s = s.replace('M522-flap50-recovery-quality-protocol-01', 'M522-quality-first-ablation-protocol-01')
    s = s.replace('M522-flap50-recovery-quality-01', 'M522-quality-first-ablation-01')
    s = replace_once(s, "parents={name:model.get_submodule(name) for name in selected}",
        "parents={name:model.get_submodule(name) for name in selected}\n"
        "        kind_by_parent={id(parents[name]):row['kind'] for name,row in selected.items()}")
    s = replace_once(s, "for parent,attr,old,new in swaps:setattr(parent,attr,old if arm=='original' else new)",
        "assert arm=='original' or arm in p['arms']\n"
        "            active=set() if arm=='original' else set(p['arms'][arm]['pruned_kinds'])\n"
        "            for parent,attr,old,new in swaps:setattr(parent,attr,new if kind_by_parent[id(parent)] in active else old)")
    s = replace_once(s, "case=dict(id=row['id'],phase=row['phase']", "case=dict(arm=state['arm'],id=row['id'],phase=row['phase']")
    start = s.index("        select('candidate')\n")
    end = s.index("    except BaseException:", start)
    s = s[:start] + """        for arm in p['arms']:
            select(arm)
            for row in p['training_requests']:
                z,r=forward(row,OUT/arm/row['id'])
                compare(row,controls[row['id']],z,r)
        assert unaffected_digest()==unchanged
        summaries={}
        for arm in p['arms']:
            cases=[c for c in value['cases'] if c['arm']==arm]
            assert len(cases)==8
            summaries[arm]=dict(requests=8,newly_wrong=sum(c['newly_wrong'] for c in cases),
                                candidate_errors=sum(not c['candidate_correct'] for c in cases),
                                original_errors=sum(not c['original_correct'] for c in cases))
        value.update(status='COMPLETE_M522_QUALITY_FIRST_FAMILY_ABLATION',original_rc=0,
                     arm_summaries=summaries,unchanged_attention_norm_embedding_digest=unchanged,
                     development_evaluated=False,candidate_regression_eligible=False,
                     independent_quality_established=False,FPGA_numerical_or_performance_pass=False,
                     explanation_quality='Not measured: original M276 endpoint is one constrained binary observation',
                     original_training_controls_reused=8,new_quantization=False,
                     precision='CPU BF16 with original packed A8 input hooks; not exact FPGA accumulators')
""" + s[end:]
    ast.parse(s, feature_version=(3, 10))
    dest = HERE / 'quality_adaptive522.py'
    with dest.open('x', encoding='utf-8', newline='\n') as f:
        f.write(s)
    p.update(status='FROZEN_M522_QUALITY_FIRST_FAMILY_ABLATION',
             candidate_id='QUALITY_FIRST_DIAGNOSIS_V1',
             current_objective='Preserve task quality and demonstrate actual end-to-end KV260 speedup; 30s is a longer-term aspiration, not this release admission threshold',
             adjustment_policy='May restore sensitive layers, reduce pruning, and use nonuniform widths; no obligation to prune all layers',
             arms={'language_only': dict(pruned_kinds=['language'], restored_kinds=['vision']),
                   'vision_only': dict(pruned_kinds=['vision'], restored_kinds=['language'])},
             purpose='Distinguish language pruning, vision pruning and their interaction using the same frozen weights before choosing a gentler candidate',
             development_requests=[], maximum_training_forwards=17,
             maximum_development_forwards=0, test_requests=0,
             new_forward_budget=17, budget_s=1800,
             outcome_is_diagnostic_only=True,
             recovery_document_identities=docs,
             prior_m522_board_registry=board_refs)
    p['inputs'].pop(source.relative_to(ROOT).as_posix())
    p['inputs'].pop((HERE / 'workflow_quality_recovery522.py').relative_to(ROOT).as_posix())
    for f in (old_prep, failure, source, dest, Path(__file__), HERE / 'workflow_adaptive522.py'):
        p['inputs'][f.relative_to(ROOT).as_posix()] = sha(f)
    save(PREP / 'RESULT.json', p)
    h = sha(PREP / 'RESULT.json')
    synchronized('latest_m522_quality_first_policy01',
        dict(status=p['status'], result=(PREP / 'RESULT.json').relative_to(ROOT).as_posix(), sha256=h, board=False),
        '## M522用户调整为质量优先的渐进剪枝提速\n\n'
        '30s改为长期方向，当前先保证质量再验证完整板端提速；允许主动减轻剪枝、恢复敏感层和非均匀宽度，不要求全层都剪。'
        '全60半宽恢复后8训练仍新增1误报，原失败保留。下一以同一权重做仅语言/仅视觉两组训练诊断，'
        '各恢复另一部分为原版，定位单部分损伤或组合影响；不运行M521，不开开发/test，不改变板端。'
        '诊断后按真实错误和已有敏感性决定较温和候选，再做质量验证。\n\nRESULT SHA `' + h + '`。')
    print(p['status'], h, flush=True)


if __name__ == '__main__':
    main()
