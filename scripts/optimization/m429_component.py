"""Streamed PL orchestration fixture; fake submit, not hardware evidence."""
import ast, json, subprocess, sys
from m351_workflow import ROOT, BASE, HERE, atomic, encoded, sha, sync
STAGE=ROOT/'tmp/m42901/component_stage'
REF=BASE/'candidates/M417-layer13-saved-reference-02'

def prepare():
    if STAGE.exists():raise RuntimeError('Immutable stage exists')
    for row in json.loads((REF/'PACKAGE_MANIFEST.json').read_bytes())['files']:assert sha(REF/row['path'])==row['sha256']
    STAGE.mkdir(parents=True)
    for name in ('m429_pl_range.py','m411_mlp_binding.py','m426_range02.py'):atomic(STAGE/name,(HERE/name).read_bytes(),immutable=True)
    old=(HERE/'test_m426_range.py').read_text(encoding='utf-8')
    code=old[:old.index('    with torch.inference_mode():')].replace('from m426_range import','from m426_range02 import')
    code=code.replace('layers.append(p(b(inner,dtype,torch.bfloat16),index=i,','layers.append(p(inner if i<2 else b(inner,dtype,torch.bfloat16),index=i,')
    code+='''    import copy
    from m429_pl_range import PLRangeScope,SavedWireCheck,SELECTED as late
    wire={};rejected=[]
    class CaptureScope(RangeScope):
        def before(self,index):
            if self.active is not None or index!=len(self.seen):raise RuntimeError('Order differs')
            if index in self.selected:
                case=self.load_case(index)
                binding=SoftwareMLPBinding(torch,targets[index].mlp,case['chains'],case['windows'],initial,
                    host.pack_chain_input,host.parse_chain_output,
                    raw_sink=lambda part,start,shift,packet,raw:wire.__setitem__((index,part,start,shift),(packet,raw)))
                self.active=(index,binding);binding.__enter__();self.peak_live_layer_scopes=1
    with torch.inference_mode():
        with RangeScope(torch,layers,targets,late,'original',load,initial,host,sink,lambda x:None):original=forward()
        before=tuple(boundary);boundary.clear();loads.clear()
        with CaptureScope(torch,layers,targets,late,'software',load,initial,host,sink,lambda x:None) as oracle:expected=forward()
        references=copy.deepcopy(oracle.batches);expected_boundaries=tuple(boundary)
        assert oracle.complete and clean() and len(wire)==286
        submits=[];stages=[]
        def submit(index,part,chain,start,shift,packet):
            key=(index,part,start,shift);assert packet==wire[key][0];submits.append(key);return wire[key][1]
        guard=SavedWireCheck(references,submit);boundary.clear();loads.clear()
        with PLRangeScope(torch,layers,targets,load,initial,host,sink,lambda x:None,
                          lambda i,p,c:stages.append((i,p)),guard) as scope:actual=forward()
        guard.require_complete()
        assert torch.equal(actual,expected) and tuple(boundary)==expected_boundaries and tuple(boundary[:13])==before[:13]
        assert clean() and scope.restored and scope.complete and scope.peak_live_layer_scopes==1
        assert loads==list(late) and stages==[(i,p) for i in late for p in ('fc1','fc2')] and len(submits)==286
    def reject(label,fn):
        try:fn()
        except (ValueError,RuntimeError):rejected.append(label)
        else:raise AssertionError('Invalid accepted '+label)
        assert clean()
    for label,edit in [('missing-layer',lambda r:r.pop('13')),('extra-layer',lambda r:r.__setitem__('12',r['13'])),
            ('missing-part',lambda r:r['13'].pop('fc2')),('short-part',lambda r:r['13']['fc1'].pop()),
            ('wrong-start',lambda r:r['13']['fc1'][0].__setitem__('start',32)),
            ('wrong-tail',lambda r:r['13']['fc1'][-1].__setitem__('rows',32)),
            ('retry',lambda r:r['13']['fc1'][0].__setitem__('physical_reference_attempts',2)),
            ('initial',lambda r:r['13']['fc1'][0].__setitem__('initial_shift',-1)),
            ('bool-shift',lambda r:r['13']['fc1'][0].__setitem__('selected_shift',True)),
            ('zero-bytes',lambda r:r['13']['fc1'][0].__setitem__('input_bytes',0)),
            ('bad-SHA',lambda r:r['13']['fc1'][0].__setitem__('raw_sha256','g'*64))]:
        ref=copy.deepcopy(references);edit(ref);reject(label,lambda ref=ref:SavedWireCheck(ref,submit))
    key=(13,'fc1',0,references['13']['fc1'][0]['selected_shift']);packet,raw=wire[key];chain=cases[13]['chains']['fc1']
    def attempt(callback=submit,packet_value=packet,part='fc1',start=0,chain_value=chain):
        g=SavedWireCheck(references,callback);return g(13,part,chain_value,start,key[3],packet_value)
    count=len(submits)
    reject('packet-byte',lambda:attempt(packet_value=bytes([packet[0]^1])+packet[1:]))
    reject('packet-short',lambda:attempt(packet_value=packet[:-1]))
    reject('part-order',lambda:attempt(part='fc2'));reject('batch-order',lambda:attempt(start=32))
    reject('output-geometry',lambda:attempt(chain_value=dict(chain,output_bytes=1)))
    assert len(submits)==count
    reject('output-byte',lambda:attempt(callback=lambda *x:bytes([raw[0]^1])+raw[1:]))
    reject('output-short',lambda:attempt(callback=lambda *x:raw[:-1]))
    reject('incomplete',lambda:SavedWireCheck(references,submit).require_complete())
    def fail_second(index,part,chain,start,shift,packet):
        if index==14:raise RuntimeError('Explicit completed fake transaction failure')
        return submit(index,part,chain,start,shift,packet)
    def interrupted():
        with torch.inference_mode(),PLRangeScope(torch,layers,targets,load,initial,host,sink,lambda x:None,
              lambda *x:None,SavedWireCheck(references,fail_second)):forward()
    reject('second-layer-restoration',interrupted)
    return dict(full_output_exact=True,all24_boundaries_exact=True,unchanged_prefix_through12=True,
        complete_wire_batches=286,staged_windows=22,peak_live_layer_scopes=1,restored=clean(),
        actual_frozen_wrappers_encoder_M207_and_PL_binding=True,synthetic_narrow_weights_and_attention=True,
        fake_PL_submit=True,no_DMA_or_Overlay=True,negative_checks=rejected,model_quality_or_performance=False)
'''
    ast.parse(code,feature_version=(3,10));atomic(STAGE/'test_m429_range.py',code.encode('utf-8'),immutable=True)
    entry="""import sys,json
from pathlib import Path
assert sys.flags.isolated
root=Path('/mnt/c/Users/30429/Desktop/TeLLMe_FPGA_2026')
stage=root/'tmp/m42901/component_stage'
ref=root/'deployment/mage_vl4b/optimization_v1/candidates/M417-layer13-saved-reference-02'
sys.path[:0]=[str(stage),str(ref)]
import torch
torch.set_num_threads(1)
from test_m429_range import component
print('M429_COMPONENT='+json.dumps(component(root)),flush=True)
"""
    atomic(STAGE/'entry.py',entry.encode('utf-8'),immutable=True);print('M429_COMPONENT_STAGE_READY')

def run():
    folder=ROOT/'tmp/m42901'/('component02' if len(sys.argv)>2 and sys.argv[2]=='authorized02' else 'component')
    if folder.exists():raise RuntimeError('Immutable component logs exist')
    cp=subprocess.run(['wsl.exe','-d','Ubuntu-24.04','--','/home/lyy/projects/qwen_baseline/.venv/bin/python','-I','-B',
        '/mnt/c/Users/30429/Desktop/TeLLMe_FPGA_2026/tmp/m42901/component_stage/entry.py'],capture_output=True,timeout=180)
    atomic(folder/'stdout.bin',cp.stdout,immutable=True);atomic(folder/'stderr.bin',cp.stderr,immutable=True)
    if cp.returncode:raise RuntimeError('Component rejected; inspect immutable raw byte logs')
    lines=[x.split('=',1)[1] for x in cp.stdout.decode('utf-8').splitlines() if x.startswith('M429_COMPONENT=')];assert len(lines)==1
    value=json.loads(lines[0]);assert len(value['negative_checks'])==20 and value['complete_wire_batches']==286 and value['restored']
    record=dict(status='PASS_M429_STREAMED_PL_SCOPE_FIXTURE_ONLY',component=value,
        stdout_sha256=sha(folder/'stdout.bin'),stderr_sha256=sha(folder/'stderr.bin'),staged_sources={p.name:sha(p) for p in STAGE.iterdir()},
        frozen_reference_manifest_sha256=sha(REF/'PACKAGE_MANIFEST.json'),board_run=False,hardware_visual_numerics_pass=False,performance_pass=False,temperature_measurement_enabled=False)
    out=BASE/'runs/M429-streamed-scope-component-01/RESULT.json';atomic(out,encoded(record),immutable=True)
    sync('latest_m429_streamed_scope_component',dict(status=record['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out)),
         f'## M429 后11层流式PL scope离线组件（2026-10-06）\n\nSHA {sha(out)}；实际冻结PL binding、包装及encoder，明确合成窄权重/Attention与fake PL submit；286完整输入/输出wire SHA、24边界及最终输出逐位相同，一次只保留一层窗口，20项拒绝与异常恢复通过。未上板，未证明实际视觉PL数值或提速，不测温。')
    print('M429_COMPONENT_SYNC',sha(out))

if __name__=='__main__':{'prepare':prepare,'run':run}[sys.argv[1]]()
