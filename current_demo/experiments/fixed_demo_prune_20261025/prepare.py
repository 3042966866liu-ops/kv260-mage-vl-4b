"""Freeze the user's explicit fixed-video/answer-only demonstration scope."""
from demo_common import *
def main():
    assert not PREP.exists() and not OUT.exists()
    old=read(R/'M523-whole-layer-joint-128-protocol-01/RESULT.json');semantic=read(R/'M523-whole-layer-semantic-128-protocol-01/RESULT.json')
    assert read(SEMANTIC/'RESULT.json')['original_rc']==1 and 'KeyboardInterrupt' in read(SEMANTIC/'RESULT.json')['traceback']
    assert read(R/'M523-whole-layer-demo-128-transition-01/RESULT.json')['signal_sends']==1
    frozen=dict(old['frozen'])
    def add(f):frozen[rel(f)]=sha(f)
    for f in H.glob('*.py'):compile(f.read_text(encoding='utf-8'),str(f),'exec');add(f)
    add(PREVIOUS/'runtime.py');add(PREVIOUS/'common.py');add(SEMANTIC/'RESULT.json')
    add(R/'M523-whole-layer-demo-128-transition-01/RESULT.json')
    recovery={}
    for name in ('CURRENT_STATE.md','docsMILESTONES.md','DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'):
        f=ROOT/name;f.read_text(encoding='utf-8-sig');recovery[name]=sha(f)
    sources=[];feature_sources=[];seen=set()
    def source(v,l,folder,paths,features,bank=None):
        for name,path in paths.items():add(ROOT/path)
        for name,path in features.items():add(ROOT/path)
        sources.append(dict(vision=v,language=l,logits=paths,features=features,summary=folder,bank=bank or {}))
        key=mask(v)
        if key not in seen and len(features)>=4:feature_sources.append(dict(vision=v,features=features,bank=bank or {}));seen.add(key)
    for f in OLDSEARCH.glob('*/SUMMARY.json'):
        a=read(f);add(f)
        source(a['vision'],a['language'],rel(f),{name:rel(f.parent/name/'first_logits.npy') for name in a['features']},a['features'],a['bank'])
    for start in SEMANTIC.glob('trials/*/START.json'):
        a=read(start);add(start);paths={};features={};bank={}
        summary=start.parent/'SUMMARY.json'
        if summary.exists():s=read(summary);bank=s.get('bank',{});add(summary)
        for f in start.parent.glob('*/RESULT.json'):
            c=read(f);paths[c['request_id']]=rel(f.parent/'logits.npy');features[c['request_id']]=c['feature_path'];add(f)
        source(a['vision'],a['language'],rel(start),paths,features,bank)
    for arm in ('parent','candidate'):
        cases=[c for c in read(OLDQUALITY/'RESULT.json')['cases'] if c['arm']==arm]
        a=cases[0]
        source(a['vision'],a['language'],rel(OLDQUALITY/'RESULT.json'),{c['request_id']:rel(OLDQUALITY/arm/c['request_id']/'logits.npy') for c in cases},{c['request_id']:rel(OLDQUALITY/arm/c['request_id']/'features.npy') for c in cases})
    ids=['cal_04_t0','cal_00_t0','cal_04_t1','cal_00_t1'];demo=[r for r in old['requests'] if r['id'] in ids]
    assert len(demo)==4 and len({r['source_group'] for r in demo})==2
    clips=[]
    for n in ('00','04'):
        f=R/('M464-video-calibration-capture-01/clip_'+n+'/METADATA.json');m=read(f);add(f)
        video=ROOT/m['source'];assert sha(video)==m['video_sha256'];add(video)
        clips.append(dict(source=m['source'],video_sha256=m['video_sha256'],frame_indices=m['sampled_frame_indices'],timestamps_ms=m['sampled_timestamp_ms'],label='No' if n=='00' else 'Yes'))
    assert decision('False')=='No' and decision(' TRUE')=='Yes' and decision('None')=='Invalid' and decision(' involved')=='Invalid'
    p=dict(status='FROZEN_FIXED_DEMO_ANSWER_CORRECTNESS_SPEED_SEARCH',original_rc=0,runtime_protocol=old,frozen=frozen,recovery_full_read=recovery,
        demo_ids=ids,requests=old['requests'],demo_clips=clips,token_ids=old['token_ids'],costs=semantic['costs'],base_bank=semantic['base_bank'],
        sources=sources,feature_sources=feature_sources,parent_hot_TTFT_s=59.6703845925,
        user_update='Fixed demonstration videos and fixed knife question; ensure displayed answer correct, other quality constraints relaxed. Applies prospectively to this version; prior failures preserved.',
        output_contract='Unrestricted full-vocabulary argmax. Decode actual first model token; exact normalized Yes/No/True/False => display 有刀/无刀. Host stops after this decision token. Other tokens mean no unambiguous answer and reject. No forced output, vocabulary mask, canned answer or EOS claim.',
        acceptance='All4 predeclared fixed-demo requests must return the correct actual decision. No extra explanation/EOS/feature-L2/margin gate. Previously registered remaining8 calibration requests reported separately after winner freeze, not used to select it. No heldout videos opened.',
        structural_scope='All visual/language Transformer blocks eligible, at least1 per branch retained. Patch embedding, positions/RoPE, visual merger, final norms, token embedding and LM head remain. Original code/scale/bitwidth/R1 on retained blocks unchanged; no new fitting.',
        strategy='Reuse every saved matching full first-logit vector and visual feature. Evaluate all preexisting configurations on fixed4; choose fastest time-model passing seed. Up to12 rounds: per-branch top4 residual/cost plus3 highest-cost single-block deletions; try up to4 passing deletions together then3/pairs; if no singleton passes try up to12 two-block combinations from the top6 candidates, then up to8 positive-gain restore1/delete2 exchanges. Never repeat a completed same-prefix forward. No hard target depth. Stop and measure if modelled TTFT<=26s, leaving4s target margin; no speed guarantee.',
        budgets=dict(trials=320,new_decision_sequences=1024,new_vision_forwards=640,wall_seconds=14400,saved_array_bytes=8<<30),
        model_time='Visual saved whole-layer wall times plus a heuristic proportional allocation of26.0998s language time. Used to rank only; actual fastest requires matched board timing.',
        AI_generated_pilot=True,source_group_independence_limited=True,heldout_opened=0,board_commands=0,new_R1=False,new_quantization=False,parameter_updates=0,
        production_quality_claim=False,TTFT_under30_pass=False)
    save(PREP/'RESULT.json',p)
    from m455456_workflow02 import synchronized
    h=sha(PREP/'RESULT.json');synchronized('latest_m523_fixed_demo_protocol01',dict(status=p['status'],result=rel(PREP/'RESULT.json'),sha256=h,board=False),
        '## M523按人类新要求固定两段视频答案正确优先的剪枝搜索\n\nRESULT SHA '+h+'；固定原cal00工厂无刀/cal04厨师有刀各4s/8s共4请求，128同问题。真实全词表argmax首token为Yes/No/True/False才展示判断并由应用停止，不强制答案/不冒充自然EOS。4/4正确为门，解释/尾句截断/特征/概率不再单独否决，其他8cal另列、6test封闭；原通用12V16L失败保留。旧严格搜索经本机WSL核身份单INT保存退出1是用户标准切换，不是板故障；已完成所有prefix/特征复用。最多320配置/1024新首token，Transformer首尾层也可试但embedding/merger/norm/head保留，0新板/R1/量化/梯度；时间模型不当实测。')
    print(p['status'],h,len(sources),flush=True)
if __name__=='__main__':main()
