"""Independent saved-full-logits audit. No model, optimizer, or board actions."""
import csv,io,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common_ablation import *
AUDIT=RUNS/'M537-V4-matched-ablation-audit-01'
ARMS=['parent4096','exact_crop','reexport_crop','clean_recovery','harder_recovery']
LABELS={'parent4096':'父模型4096','exact_crop':'3584只裁剪原码','reexport_crop':'3584未训练W4重导出','clean_recovery':'3584清晰恢复','harder_recovery':'3584较难学生恢复'}
def logits(row):
    f=ROOT/row['source_payload'];assert sha(f)==row['source_sha256']
    if f.suffix=='.npz':
        with np.load(f,allow_pickle=False) as a:z=a['logits'].copy()
    else:z=np.load(f,allow_pickle=False)
    assert z.shape==(151936,) and z.dtype==np.float32 and np.isfinite(z).all()
    assert digest(z)==row['logits_raw_sha256'] and int(z.argmax())==row['token_id']
    assert abs(metrics(z,row['expected'])-row['correct_direction_pp'])<1e-10
    assert row['correct']==(row['actual']==row['expected'])
    return z
def score(rows):
    return dict(n=len(rows),correct=sum(r['correct'] for r in rows),
        positives=sum(r['expected']=='Yes' for r in rows),negatives=sum(r['expected']=='No' for r in rows),
        true_yes=sum(r['actual']==r['expected']=='Yes' for r in rows),true_no=sum(r['actual']==r['expected']=='No' for r in rows),
        false_no=sum(r['actual']=='No' and r['expected']=='Yes' for r in rows),
        false_yes=sum(r['actual']=='Yes' and r['expected']=='No' for r in rows),
        invalid=sum(r['actual']=='Invalid' for r in rows),
        invalid_positive=sum(r['actual']=='Invalid' and r['expected']=='Yes' for r in rows),
        invalid_negative=sum(r['actual']=='Invalid' and r['expected']=='No' for r in rows))
def main():
    p=verify();reuse=read(REUSE/'RESULT.json');new=read(OUT/'RESULT.json')
    assert reuse['primary_rc']==new['primary_rc']==0
    for stage,source in [('reuse',REUSE),('evaluate',OUT)]:
        h=read(RUNS/('M537-V4-'+stage+'-host-01')/'RESULT.json')
        assert h['host_rc']==0 and h['native_sha256']==sha(source/'RESULT.json')
    rows=reuse['parent']+reuse['child']+new['samples'];assert len(rows)==60
    assert len({(r['arm'],r['case']) for r in rows})==60
    assert len(new['samples'])==new['frozen_head_calls']==len(p['todo'])==40
    assert sum(r['reused'] for r in rows)==20
    index={(r['arm'],r['case']):r for r in rows};cases={r['key']:r for r in p['cases']}
    arrays={}
    for r in rows:
        assert r['arm'] in ARMS and r['case'] in cases
        c=cases[r['case']];assert (r['id'],r['expected'],r['role'])==(c['id'],c['expected'],c['role'])
        arrays[(r['arm'],r['case'])]=logits(r)
        if not r['reused']:
            assert r['cache_before']==r['cache_after_clear']==r['decode_calls']==0
            assert r['tokens']==128 and r['views']==2 and r['visual_slots']==98 and r['cache_layer_count']==18
            assert r['parameter_versions_unchanged'] and r['frame_raw_sha256']==digest(np.load(ROOT/c['frame'],allow_pickle=False))
    # Every retained fc1 integer code, scale, bias and original group identity is exactly shared.
    weights={}
    for arm,v in reuse['variants'].items():
        folder=ROOT/v['package'];assert sha(folder/'PACKAGE_MANIFEST.json')==v['manifest_sha256']
        for item in read(folder/'PACKAGE_MANIFEST.json')['files']:assert sha(folder/item['path'])==item['sha256']
        with np.load(folder/'weights.npz',allow_pickle=False) as a:weights[arm]={k:a[k].copy() for k in a.files}
    for arm in p['new_arms']:
        for key in ['fc1_codes','fc1_scales','bias1','kept_original_groups']:
            assert np.array_equal(weights[arm][key],weights['exact_crop'][key])
        assert len(weights[arm]['kept_original_groups'])==56
    fit=read(FIT/'RESULT.json');learned={r['name']:r for r in fit['variants'] if r.get('steps')}
    assert learned['clean_control']['steps']==learned['paired_harder_student']['steps']==128
    assert learned['clean_control']['trajectory'][:64]==learned['paired_harder_student']['trajectory'][:64]
    for arm,oldname in [('clean_recovery','clean_control'),('harder_recovery','paired_harder_student')]:
        old=learned[oldname];f=ROOT/old['payload'];assert sha(f)==old['sha256']
        with np.load(f,allow_pickle=False) as a:
            assert all(np.array_equal(a[k],weights[arm][k]) for k in a.files)
    summaries={}
    for arm in ARMS:
        selected=[r for r in rows if r['arm']==arm];assert len(selected)==12
        summaries[arm]={role:score([r for r in selected if r['role']==role]) for role in ['fixed-demo','reserved-cal','hard-dev']}
        summaries[arm]['all']=score(selected)
    comparisons={}
    for reference,candidate in [('parent4096','harder_recovery'),('exact_crop','reexport_crop'),
        ('exact_crop','clean_recovery'),('reexport_crop','clean_recovery'),('clean_recovery','harder_recovery')]:
        pairs=[]
        for key in cases:
            a=index[reference,key];b=index[candidate,key]
            pairs.append(dict(case=key,role=a['role'],expected=a['expected'],reference_actual=a['actual'],candidate_actual=b['actual'],
                reference_raw=a['raw_token'],candidate_raw=b['raw_token'],reference_correct=a['correct'],candidate_correct=b['correct'],
                new_failure=a['correct'] and not b['correct'],recovered=not a['correct'] and b['correct'],shared_failure=not a['correct'] and not b['correct'],
                full_logits_equal=bool(np.array_equal(arrays[reference,key],arrays[candidate,key])),
                reference_correct_direction_pp=a['correct_direction_pp'],candidate_correct_direction_pp=b['correct_direction_pp']))
        comparisons[reference+'_vs_'+candidate]=dict(reference=reference,candidate=candidate,pairs=pairs,
            new_failures=[r['case'] for r in pairs if r['new_failure']],recovered=[r['case'] for r in pairs if r['recovered']],
            decision_changes=[r['case'] for r in pairs if r['reference_actual']!=r['candidate_actual']])
    AUDIT.mkdir(exist_ok=False)
    v=dict(status='AUDITED_M537_MATCHED_V4_SOFTWARE_CAUSALITY_STUDY',primary_rc=0,
        protocol_sha256=sha(PROTO),reuse_sha256=sha(REUSE/'RESULT.json'),quality_sha256=sha(OUT/'RESULT.json'),
        audit_source_sha256=sha(Path(__file__)),counts=dict(total=60,reused=20,new_full_prefills=40,new_optimizer_updates=0,board_commands=0),
        summaries=summaries,comparisons=comparisons,rows=rows,same56groups_fc1_codes_scales_bias=True,
        frozen_head=True,both_recovery_arms_same128_update_budget=True,first64_clean_training_trajectories_equal=True,
        trained_weight_exports_unchanged=True,original_M536_board_gate_FAIL_preserved=True,heldout_opened=False,
        limitations=['Software full-vocabulary first-step judgments, not new board verification or TTFT.',
        'Fixed-demo and hard-dev sources overlap training. Hard-dev perturbations unused for V4 fitting but used for older output-head validation.',
        'Reserved calibration is development evidence, not independent test. Six original heldout clips remain closed.',
        'AI-generated pilot, limited source-group independence. Single final checkpoint/seed per recovery arm.',
        'Invalid output remains invalid and is not converted to No. No explanation/Decode test or production quality promotion.',
        'Raw exact integer slicing differs from final learned W4 quantization; separate untrained reexport control records that confound.'])
    save(AUDIT/'RESULT.json',v)
    buf=io.StringIO(newline='');fields=['arm','case','role','expected','actual','raw_token','token_id','correct','correct_direction_pp','reused','source_payload','source_sha256']
    writer=csv.DictWriter(buf,fieldnames=fields,extrasaction='ignore');writer.writeheader();writer.writerows(sorted(rows,key=lambda r:(ARMS.index(r['arm']),r['case'])))
    (AUDIT/'ANSWERS.csv').write_text('\ufeff'+buf.getvalue(),encoding='utf8',newline='')
    table=['| 同通道配置 | 固定清晰4 | 预留清晰4 | 较难开发4 | 合计12 | 无效输出 |','|---|---:|---:|---:|---:|---:|']
    for arm in ARMS:
        s=summaries[arm];table.append('| '+LABELS[arm]+' | '+' | '.join(str(s[k]['correct'])+'/4' for k in ['fixed-demo','reserved-cal','hard-dev'])+' | '+str(s['all']['correct'])+'/12 | '+str(s['all']['invalid'])+' |')
    reserved=['| 预留窗口 | 标签 | 父模型4096 | 较难恢复3584 |','|---|---|---|---|']
    for c in p['cases']:
        if c['role']!='reserved-cal':continue
        a=index['parent4096',c['key']];b=index['harder_recovery',c['key']]
        reserved.append('| '+c['id']+' | '+c['expected']+' | '+a['actual']+' ('+repr(a['raw_token'])+') | '+b['actual']+' ('+repr(b['raw_token'])+') |')
    causal=[]
    for key,c in comparisons.items():
        causal.append('- '+LABELS[c['reference']]+' → '+LABELS[c['candidate']]+'：原正确变错误 '+str(len(c['new_failures']))+' 条 '+str(c['new_failures'])+'；原错误变正确 '+str(len(c['recovered']))+' 条 '+str(c['recovered'])+'。')
    local=[]
    for oldname in ['clean_control','paired_harder_student']:
        m=learned[oldname]['metrics'];local.append(dict(name=oldname,aggregate=m['aggregate'],hard_metrics=m.get('hard',m.get('hard_fit',m.get('hard_training')))))
    body='''# M537 V4 同通道恢复消融与父／子错误归因

本轮仅离线复用与补齐判断，不扩层、不重新训练、不改输出头、不上板。

'''+ '\n'.join(table)+'\n\n'+ '\n'.join(reserved)+'\n\n'+ '\n'.join(causal)+'''

父模型复用依据：12条旧独立完整前向的151936维FP32 logits都能用同一冻结A/B输出头从旧捕获逐位重组；其中4条与M536最新父模型控制的全logits逐位相等。图像逐像素、128个输入ID、保留层编号及头权重SHA均相同。旧父记录use_cache=False，当前M536使用初始空DynamicCache；这一区别保留在来源字段，不把旧证据包装成新板测。

四种3584配置的56组通道、fc1整数码、scale、bias完全一致。清晰/较难恢复均复用同一次实验的128步最终导出，前64步训练轨迹逐项相等；量化器、更新预算、训练来源与冻结头一致，没有按本轮答案重新选轮次。只裁剪原码组保留原fc2偏置、没有R1；未训练W4重导出组用于分开量化重导出效应。二者均0训练步，不宣称其预算等于有学习组。

共60条配置/输入观察，20条复用、40条新增完整首步推理；新推理逐条核验全词表argmax、完整logits文件SHA、128输入/98视觉槽/双视图、18层缓存前空后清、保留视觉/语言层实际调用及参数版本。Invalid单独统计，不转为No。具体逐条答案、正确方向概率间隔与原始证据在ANSWERS.csv和RESULT.json；间隔不是校准置信度。

输入组成是8条清晰（固定4＋reserved-cal4）加4条旧moderate_check扰动，并非6个来源的12条清晰请求。扰动与M536训练增强逐像素不同，但此前参与过输出头验证，不能视作独立泛化证据；固定源也参与训练。6个原test/heldout视频继续封闭，AI生成pilot和来源独立性限制保留。

本轮不产生新TTFT。M536原板端8请求全部完成后的计数断言FAIL及原退出码1保持，不因本次离线审计改为正式门禁通过。当前只支持被测开发样本的观察，不保证新校园视频正确，也不自动选择下一层或晋级发布版本。
'''
    (AUDIT/'REPORT.md').write_text(body,encoding='utf8')
    sys.path.insert(0,str(ROOT/'scripts/optimization'));from m455456_workflow02 import synchronized
    h=sha(AUDIT/'RESULT.json')
    note='## M537 V4同通道消融完成\n\nRESULT SHA '+h+'；60条观察=20复用+40新软件完整prefill，0新训练/板/heldout。\n\n'+'\n'.join(table)+'\n\n'+'\n'.join(causal)+'\n\n父/子预留错误已逐条归因，Invalid保持无效；仅当前开发集，较难扰动此前参与旧head验证，不是独立泛化。报告 '+rel(AUDIT/'REPORT.md')+'。不扩层、不自动晋级，M536原正式板门禁FAIL/rc1保持；无新TTFT。'
    synchronized('latest_m537_v4_matched_ablation_audit01',dict(status=v['status'],result=rel(AUDIT/'RESULT.json'),sha256=h,
        report=rel(AUDIT/'REPORT.md'),board=False,promoted=False),note)
    print(json.dumps(dict(result=rel(AUDIT/'RESULT.json'),sha256=h,summaries=summaries,
        comparisons={k:dict(new_failures=c['new_failures'],recovered=c['recovered']) for k,c in comparisons.items()}),ensure_ascii=False,indent=2))
if __name__=='__main__':main()
