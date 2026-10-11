"""Draft balanced light video timing; cannot freeze before M368 numerical PASS."""
import ast
import symtable
import m351_workflow as w


def rep(t,a,b):
    if t.count(a)!=1:raise RuntimeError('Performance draft anchor differs:'+a[:90])
    return t.replace(a,b,1)


def main():
    old=w.BASE/'candidates/M368-staged-video-03'
    source=(old/'m368_staged_video_gate.py').read_text(encoding='utf-8')
    start=source.index('        policy.seal(allocations,int(TARGET_BUILD,16))')+len('        policy.seal(allocations,int(TARGET_BUILD,16))')
    end=source.index('    except CapacityRejected as exc:',start)
    prefix=source[:start]
    suffix=source[end:]
    prefix=rep(prefix,"    is_candidate=args.case.startswith('B')","    is_candidate=False  # Stable is always the first member of ABBABAAB")
    prefix=rep(prefix,'from m368_stage_policy import StagePolicy,SHAPES','from m369_light_policy import StagePolicy\nfrom m368_stage_policy import SHAPES\nfrom m369_trials import run_trials')
    a=prefix.index("        identity_path=Path('/home/ubuntu/m368_identity_preflight_01/RESULT.json')")
    b=prefix.index("        prior=json.loads((HERE/'STAGE_PREREQUISITE.json')",a)
    prefix=prefix[:a]+'''        numeric=json.loads((HERE/'NUMERIC_PREREQUISITE.json').read_text(encoding='utf-8'))
        if numeric['status']!='PASS_INDEPENDENT_VIDEO_CAPACITY_AND_NUMERICS' or not numeric['numerical_pass'] or numeric['raw_status']!='PASS_M368_FIXED_VIDEO_DIAGNOSTIC':raise RuntimeError('Synchronized actual-video numeric prerequisite differs')
'''+prefix[b:]
    prefix=rep(prefix,"                if result.get('vision_forward_calls',0):raise RuntimeError('Unexpected second visual forward')\n                result['vision_forward_calls']=1", "                result['vision_forward_calls']=result.get('vision_forward_calls',0)+1")
    prefix=rep(prefix,"                result['visual_features']=tensor(visual)\n",'')
    prefix=prefix.replace("EVIDENCE=Path('/home/ubuntu/m368_staged_video_02')/args.case","EVIDENCE=Path('/home/ubuntu/m369_light_video_01')")
    trial='''
        patch(tokenizers,'Tokenizer',original_tokenizer)
        result['build_id']='0x4D395832/0x4D333537'
        result['production_policy_changed']=False
        result['production_threshold_would_admit']=result['loaded_capacity']['meets_threshold']
        def new_board(variant,index):
            nonlocal runtime,policy,initialized,allocations
            global TARGET,TARGET_SHA,TARGET_BUILD
            if not runtime._m368_closed:raise RuntimeError('Previous runtime not safely closed')
            initialized=False;allocations=[]
            result['allocated_buffers']=[];result['released_buffers']=[];result['transactions']=[]
            TARGET=CANDIDATE if variant=='B' else STABLE
            TARGET_SHA=CAND_SHA if variant=='B' else STABLE_SHA
            TARGET_BUILD='0x4D333537' if variant=='B' else '0x4D395832'
            verify_frozen_package(TARGET,TARGET_SHA,legacy_manifest=variant=='A')
            envpath=EVIDENCE/('trial_environment_'+str(index)+'.json')
            checked=subprocess.run([sys.executable,'-B',str(HERE/'m120_board_env_preflight.py'),'--candidate',str(TARGET),'--expected-package-manifest-sha256',TARGET_SHA,'--result',str(envpath)],timeout=90)
            if checked.returncode:raise RuntimeError('Trial environment rejected; no overlay')
            patch(base,'BUILD_ID',int(TARGET_BUILD,16))
            patch(video_server,'BUILD_ID',TARGET_BUILD)
            runtime=OwnedBoard(STABLE/'overlay/m120_m89x2_t32.bit',config['weights_root']/'language_fourport',config['weights_root']/'lmhead_fourport',STABLE/'contracts/M126_LANGUAGE_RUNTIME_CONTRACT_RESULT.json',STABLE/'contracts/M126_LMHEAD_RUNTIME_CONTRACT_RESULT.json',weight_mode='staged-low-cma')
            policy=StagePolicy(result,lambda:runtime,base)
            policy.seal(allocations,int(TARGET_BUILD,16))
            return runtime,policy
        run_trials(engine,runtime,policy,base,CANDIDATE,HERE,result,new_board,patch)
        result['boot_unchanged']=sha256(boot)==before_boot
        result['cmdline_unchanged']=Path('/proc/cmdline').read_text(encoding='utf-8')==before_cmd
        if not result['boot_unchanged'] or not result['cmdline_unchanged']:raise RuntimeError('Protected identities changed')
        result['status']='PASS_M369_LIGHT_VIDEO_MEASUREMENTS'
'''
    # OwnedBoard's only close flag is diagnostic bookkeeping, retained unchanged.
    text=prefix+trial+suffix
    text=text.replace('M368','M369').replace('m368_staged_video_gate','m369_light_video_gate').replace('m368_export_result','m369_export_result')
    text=text.replace('PASS_M369_FIXED_VIDEO_DIAGNOSTIC','PASS_M369_LIGHT_VIDEO_MEASUREMENTS')
    # M368 prerequisite names and literal status must retain their actual provenance.
    text=text.replace("numeric['raw_status']!='PASS_M369_FIXED_VIDEO_DIAGNOSTIC'","numeric['raw_status']!='PASS_M368_FIXED_VIDEO_DIAGNOSTIC'")
    text=text.replace("numeric['raw_status']!='PASS_M369_LIGHT_VIDEO_MEASUREMENTS'","numeric['raw_status']!='PASS_M368_FIXED_VIDEO_DIAGNOSTIC'")
    text=text.replace("'independent-fixed159-video-capacity-diagnostic'","'balanced-fixed159-video-light-performance'")
    text=text.replace('elapsed > 900','elapsed > 3600').replace("performance'] > 900", "performance'] > 3600")
    text=text.replace("result['next_step'] = 'Independent video adjudication; balanced full-request performance only after exact output and lifecycle PASS synchronized'","result['next_step'] = 'Adjudicate all8 original full-request times and order variability; no automatic promotion'")
    text=text.replace('Independent actual159 video capacity diagnostic; production admission unchanged.','Balanced fixed159 video request timing; production admission unchanged.')
    ast.parse(text,feature_version=(3,10))
    symbols=next(t for t in symtable.symtable(text,'m369','exec').get_children() if t.get_name()=='main')
    assert next(t for t in symbols.get_children() if t.get_name()=='tracked_allocate').lookup('SHAPES').is_global()
    assert 'tensor(visual)' not in text
    assert "numeric['raw_status']!='PASS_M368_FIXED_VIDEO_DIAGNOSTIC'" in text
    assert text.index('engine.load()')<text.index("patch(video_server,'BUILD_ID',TARGET_BUILD)")
    w.atomic(w.HERE/'m369_light_video_gate.py',text.encode('utf-8'))
    print('M369_DRAFT_SYNTAX_SCOPE_PASS_NOT_FROZEN')


if __name__=='__main__':main()
