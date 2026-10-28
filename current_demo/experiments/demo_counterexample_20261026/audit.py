"""Audit actual exported full-model judgments and deliver exact candidate components."""
import sys,zipfile,shutil,csv,io
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common_fix import *
def main():
    p=verify();fit=read(FIT/'RESULT.json');q=read(RELOAD/'RESULT.json');capture=read(CAP/'RESULT.json')
    assert fit['primary_rc']==q['primary_rc']==0 and q['all_correct'] and q['correct']==q['n']==25
    assert q['new_temporal_correct']==q['new_temporal_n']==12 and fit['selected_arm']=='harder_student'
    hosts={}
    for stage,source in [('fit',FIT),('reload',RELOAD)]:
        f=RUNS/('M542-demo-counterexample-'+stage+'-host-01/RESULT.json');h=read(f)
        assert h['host_rc']==0 and h['native_sha256']==sha(source/'RESULT.json');hosts[rel(f)]=sha(f)
    arms=fit['arms'];assert arms['clean_control']['history'][:64]==arms['harder_student']['history'][:64]
    for arm,r in arms.items():
        assert len(r['history'])==400 and r['fit_correct']==r['fit_n']==37 and r['padded_interface_verified']
        assert all(h['batch_rows']==37 for h in r['history'])
        assert all(not h['hard_views'] or arm=='harder_student' and h['step']>=64 for h in r['history'])
    assert fit['new_temporal_checks_used_for_gradient_or_selection'] is False
    cap={r['key']:r for r in capture['student']};checks={r['key']:r for r in p['new_checks']}
    assert not set(checks)&set(fit['fit_row_keys'])
    for r in q['samples']:
        assert sha(ROOT/r['frame'])==r['frame_sha256'] and sha(ROOT/r['payload'])==r['sha256']
        with np.load(ROOT/r['payload'],allow_pickle=False) as a:
            z=a['logits'];assert z.shape==(151936,) and z.dtype==np.float32 and np.isfinite(z).all()
            assert int(z.argmax())==r['token_id']==r['target'] and digest(z)==r['logits_raw_sha256']
            assert a['features'].shape==(98,2560)
            if r['key'] in cap:
                assert r['prior_base_and_hidden_exact'] is True
                with np.load(ROOT/cap[r['key']]['source'],allow_pickle=False) as b:assert np.array_equal(a['x'],b['x']) and np.array_equal(a['base_logits'],b['z'])
        assert classify(r['raw_token'])==r['actual'] and r['correct']
        assert r['tokens']==128 and r['views']==2 and r['visual_slots']==98 and r['cache_layers']==18
        assert r['cache_before']==r['cache_after_clear']==r['decode_calls']==0 and r['parameters_unchanged']
    selected=arms[fit['selected_arm']];head=ROOT/selected['package'];assert sha(head/'PACKAGE_MANIFEST.json')==selected['manifest_sha256']
    for f in read(head/'PACKAGE_MANIFEST.json')['files']:
        file=head/f['path'];assert sha(file)==f['sha256'] and file.stat().st_nlink==1 and not file.is_symlink()
    assert np.load(head/'A.npy',allow_pickle=False).shape==(8,2560) and np.load(head/'B.npy',allow_pickle=False).shape==(151936,8)
    groups={
        'known_knife3':lambda r:r['role']=='known-demo-regression' and r['target']==9454,
        'phone4':lambda r:r['role']=='known-demo-regression' and r['id'].startswith('campus12'),
        'same_video_no2':lambda r:r['role']=='known-demo-regression' and r['id'].startswith('campus03') and r['target']==2753,
        'old_fit4':lambda r:r['role']=='legacy-fit',
        'new_clean6':lambda r:r['role']=='new-temporal-check' and r['view']=='clean',
        'new_hard6':lambda r:r['role']=='new-temporal-check' and r['view']=='hard-check'}
    tests={k:dict(n=sum(fn(r) for r in q['samples']),correct=sum(r['correct'] for r in q['samples'] if fn(r))) for k,fn in groups.items()}
    assert [tests[k]['n'] for k in groups]==[3,4,2,4,6,6]
    out=RUNS/'M542-demo-counterexample-final-audit-01';out.mkdir(exist_ok=False)
    oldfail=RUNS/'M540-campus03-demo-media-selection-01/RESULT.json';first=RUNS/'M541-demo-adaptation-fit-01/RESULT.json'
    assert not read(oldfail)['semantic_quality_pass'] and read(first)['selected_arm'] is None
    v=dict(status='VERIFIED_M542_DEMONSTRATION_REPAIR_SOFTWARE25_NOT_BOARD',primary_rc=0,
        protocol_sha256=sha(PROTO),fit_sha256=sha(FIT/'RESULT.json'),reload_sha256=sha(RELOAD/'RESULT.json'),
        original_0of3_failure_sha256=sha(oldfail),unaccepted_M541_fit_sha256=sha(first),unaccepted_M541_scores=dict(clean=18,harder=19,n=21),
        selected_arm=fit['selected_arm'],head_package=selected['package'],head_manifest_sha256=sha(head/'PACKAGE_MANIFEST.json'),
        unchanged_body_package=rel(BODY),unchanged_body_manifest_sha256=sha(BODY/'PACKAGE_MANIFEST.json'),
        matched_final_arms={k:dict(steps=400,fit_correct=r['fit_correct'],fit_n=r['fit_n'],minimum_fit_target_gap=r['minimum_fit_target_gap']) for k,r in arms.items()},
        tests=tests,full_reload_count=25,new_temporal_clean_hard_checks=12,all_actual_full_vocab_argmax_correct=True,
        minimum_reload_target_gap=min(r['target_gap'] for r in q['samples']),same_body_hidden_base_exact_on13_references=True,
        training_scope='Only original rank8 full-vocabulary residual head. Full-batch all37 prior demonstration cases explicitly become fit;clean/hard matched400 final checkpoints,clean64 prefix same. Clean teacher8 reused for matching16rows;legacy4 KD;other17labelCE.',
        original_reserved_test_not_in_training=True,new_checks_not_in_training_or_selection=True,
        inference=dict(visual_blocks=10,language_blocks=18,V4_width=3584,head_rank=8,head_extra_MACs=1235968,views=2,visual_slots=98,tokens=128,T32_batches=4,extra_network=False),
        limitations=['Demonstration-domain adaptation,not independent-source generalization. Same AI-generated videos and labels from assistant visual review.',
            'Original M540 failed frames now fit regression,not heldout. New12 timestamps/perturbations remain same source groups.',
            'Both M542 heads fit37/37;this doesnot prove augmentation universally better. Preferharder selected by training gate before new12evaluation.',
            'M541two final checkpoints failed18/21 and19/21;all original rejected captures/sources preserved. M542is a new declared objective,counterexamples and full-batch replay,not revised old scores.',
            'No new board/Web acceptance or TTFT;structure/head size unchanged doesnot prove latency preserved. M536 formal gateFAIL/rc1unchanged.'],
        host_results=hosts,board_accepted=False,web_accepted=False,new_TTFT=False,production_promoted=False,
        next_step='A53 exact head padded interface admission and fixed-frame physical board validation,then exact browser RGB/current-frame event matching. Never alarm from filename or prerecorded labels.')
    save(out/'RESULT.json',v)
    names={'known_knife3':'原漏判持刀画面','phone4':'手机无刀画面','same_video_no2':'同片未见刀画面','old_fit4':'工厂／厨师回归','new_clean6':'未进本轮训练的新时点','new_hard6':'新时点的困难增强'}
    table=['| 检查组 | 实际完整模型结果 |','|---|---:|']+[f"| {names[k]} | {r['correct']}/{r['n']} |" for k,r in tests.items()]
    report='''# M542 固定校园演示漏判与误报修复

当前候选在独立进程重新加载完整10V18L学生后，25条软件首判断全部匹配画面复核；原三条持刀No已全部转为真实Yes，手机和同片空画面均No。没有按片名/预设时间报警、没有限制二元词表或改标签。

'''+ '\n'.join(table)+'''

第一轮M541清晰18/21、较难19/21均未验收。虽然已修原三持刀，但空楼宇误报与新姿态漏判仍存在；两个失败终点和日志保持，未部署。第二轮M542在新协议中明确把原37个展示样本全部转为fit，包含这些反例；每一步使用完整平衡批次，较难臂同时保留清晰与困难样本，解决只换成困难图后遗忘清晰反例的问题。两臂同原头初始化、相同37行/400步终点，前64清晰轨迹相同；清晰臂用对应清晰输入替代增强行，较难臂后336步使用清晰＋困难完整回放。

8条较深低比特教师清晰输出此前全部正确，仍只对对应16条clean/hard学生行做KL；4条旧fit回放分布保持，另外17条是标签CE，不冒充全都做了教师蒸馏。教师不是原始未量化checkpoint。只更新已有rank8头A/B，主体V4恢复3584及所有层、位宽、128输入/98视觉槽/双视图/四T32不改，不增加推理网络或矩阵尺寸。

两个M542最终头都在37展示fit上全对，最低目标对其它完整词表logit余量clean约4.19、harder约6.47。按事前仅看fit的规则选择harder，再检查此前未参与梯度或选头的6个新时点及6份新增强。它们和13旧回归合计25次完整新模型前向；全151936FP32 logits/argmax、参数版本、18KV前空后清已核。13已有参考的隐藏和基础logits逐位一致。新增12条来自相同视频，不是独立来源测试；两个头fit全对也不足以证明增强普遍优于普通训练。

本轮是用户指定两段AI生成素材的展示域恢复，原失败窗口已成为训练回归，不能把25/25作为泛化准确率或保证其它校园视频正确。原六test及原reserved没有用于训练/选轮次。M541数值采集01/02拒绝、25隔离数组、直接加载9逐位基准与旧4语义参考分列均保留，没有放宽板端容差或抹去失败。

尚无本候选新的实板结果、Web上传验收或TTFT。原M536正式计数gateFAIL/退出码1保持。矩阵尺寸与结构开销相同，不等于已测时延不变。下一需A53接口/实板固定帧验收，再处理真实浏览器采样与事件绑定。原（3）号只有10秒且开头无刀，不能只取第一帧预测后续，也不能在真实Yes返回前预置红警；页面不显示TTFT。
'''
    (out/'REPORT.md').open('x',encoding='utf8').write(report)
    buf=io.StringIO(newline='');writer=csv.writer(buf);writer.writerow(['key','role','view','expected','actual','raw_token','target_gap','input_sha256','logits_sha256'])
    for r in q['samples']:writer.writerow([r['key'],r['role'],r['view'],r['expected'],r['actual'],r['raw_token'],r['target_gap'],r['frame_sha256'],r['logits_raw_sha256']])
    (out/'ANSWERS.csv').write_text('\ufeff'+buf.getvalue(),encoding='utf8',newline='')
    stage=ROOT/'outputs/m542_fixed_demo_repaired_components';stage.mkdir(exist_ok=False);files=[]
    for name,pkg in [('head',head),('body',BODY)]:
        for r in read(pkg/'PACKAGE_MANIFEST.json')['files']:
            source=pkg/r['path'];assert sha(source)==r['sha256'];dest=stage/name/r['path'];dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,dest);files.append(dest)
        dest=stage/name/'PACKAGE_MANIFEST.json';shutil.copyfile(pkg/'PACKAGE_MANIFEST.json',dest);files.append(dest)
    for name in ['RESULT.json','REPORT.md','ANSWERS.csv']:
        dest=stage/name;shutil.copyfile(out/name,dest);files.append(dest)
    for source,name in [(oldfail,'ORIGINAL_M540_FAIL.json'),(first,'ORIGINAL_M541_UNACCEPTED_FIT.json')]:
        dest=stage/name;shutil.copyfile(source,dest);files.append(dest)
    readme=stage/'README.txt';readme.write_text('Fixed-demonstration research components,not standalone firmware or deployed system. Requires unchanged10V18L/128 dual-view runtime and current V4_3584 body. Use body/V4_PLAN.json and head/HEAD_MANIFEST.json with their unchanged native classes. New rank8 head software25/25:oldfailedwindows nowtrainingregression,new12same-video checks not independent generalization. No new board/Web/TTFT acceptance. Originalfailures retained. Never use filenames or prerecorded answers to raise alarms.\n',encoding='utf8');files.append(readme)
    assert set(files)=={f for f in stage.rglob('*') if f.is_file()}
    entries=[dict(path=f.relative_to(stage).as_posix(),bytes=f.stat().st_size,sha256=sha(f)) for f in sorted(files)]
    save(stage/'DELIVERY_MANIFEST.json',dict(files=entries,file_count=len(entries),total_bytes=sum(r['bytes'] for r in entries)))
    archive=ROOT/'outputs/M542_fixed_demo_repaired_components.zip'
    with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED) as z:
        for f in sorted(stage.rglob('*')):
            if f.is_file():assert f.suffix!='.pyc' and '__pycache__' not in f.parts;z.write(f,arcname=f.relative_to(stage).as_posix())
    with zipfile.ZipFile(archive) as z:
        assert set(z.namelist())=={r['path'] for r in entries}|{'DELIVERY_MANIFEST.json'}
        for r in entries:assert hashlib.sha256(z.read(r['path'])).hexdigest()==r['sha256']
    save(out/'DELIVERY.json',dict(path=rel(archive),sha256=sha(archive),bytes=archive.stat().st_size,files=len(entries)+1))
    sys.path.insert(0,str(ROOT/'scripts/optimization'));from m455456_workflow02 import synchronized
    h=sha(out/'RESULT.json');synchronized('latest_m542_fixed_demo_repair_audit01',dict(status=v['status'],result=rel(out/'RESULT.json'),sha256=h,report=rel(out/'REPORT.md'),
        head_package=selected['package'],archive=rel(archive),archive_sha256=sha(archive),board=False,promoted=False),
        '## M542固定校园演示恢复候选：完整软件25/25\n\nRESULT SHA '+h+'；M541旧18/21与19/21失败保留。新全批次37展示fit显式含旧反例，clean/harder各400同初值/首64同轨均37/37，依fit门选择harder后，再验12未进本轮训练新时点/增强与13回归，共25完整首判断全对。原3持刀Yes、手机4No、同片2No、旧fit4、新清晰6与新困难6均通过；13原参考hidden/base逐位、全151936argmax/18KV/参数核验。只原rank8头更新，原身体10V18L/V43584/128双视图和位宽保持，不增推理模块。固定AI素材适配、同源开发非独立泛化，原reserved/test未训练。无新板/Web/TTFT，M536正式FAIL保持；精确候选包 '+rel(archive)+' SHA '+sha(archive)+'。下一A53接口与固定帧实板验收、浏览器事件绑定，不能先称已部署。')
    for n in ['CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json']:assert h in (ROOT/n).read_text(encoding='utf-8-sig')
    print(dict(status=v['status'],sha256=h,tests=tests,min_gap=v['minimum_reload_target_gap'],archive=rel(archive),archive_sha256=sha(archive)))
if __name__=='__main__':main()
