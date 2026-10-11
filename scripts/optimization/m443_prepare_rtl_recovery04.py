"""Preserve pre-tool fixture error and version a corrected isolated preparation."""
from m351_workflow import ROOT,BASE,HERE,encoded,sha,sync
from m441_host_io08 import atomic
err=BASE/'runs/M443-RTL-preparation-error-03/RESULT.json'
partial=ROOT/'tmp/m443_sim_coverage_03'
r=dict(status='FAIL_M443_RTL_PREPARATION03_BEFORE_TOOL',explanation='已转换W2原夹具再次进入W4到W2转换器断言。0工具/RTL/板端；原03部分准备文件保持，新04直接核对复用原W2夹具和原chain。',generator_sha256=sha(HERE/'m443_prepare_rtl03.py'),partial_files=[dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p)) for p in sorted(partial.rglob('*')) if p.is_file()],tool_started=False,board=False)
atomic(err,encoded(r),immutable=True)
sync('latest_m443_rtl_preparation_error03',dict(status=r['status'],result=err.relative_to(ROOT).as_posix(),sha256=sha(err),board=False),'## M443 RTL准备03夹具转换错误（2026-10-10）\n\nSHA '+sha(err)+'；'+r['explanation'])
t=(HERE/'m443_prepare_rtl03.py').read_text(encoding='utf-8')
for a,b in [('tmp/m443_sim_coverage_03','tmp/m443_sim_coverage_04'),('M443-W2-W4-pair-pipeline-RTL-03','M443-W2-W4-pair-pipeline-RTL-04'),('m443_sim_evidence03','m443_sim_evidence04'),('m443_sim_control03','m443_sim_control04'),('m443_coverage03','m443_coverage04'),('CONTROL_POLICY03','CONTROL_POLICY04'),('latest_m443_pair_pipeline_rtl','latest_m443_pair_pipeline_rtl04'),('NEW_DUT_W2_W4_BOUNDED_RTL03','NEW_DUT_W2_W4_BOUNDED_RTL04')]:t=t.replace(a,b)
assert t.count("if name=='W2_max':chain=write_max_W2(folder)")==1
t=t.replace("if name=='W2_max':chain=write_max_W2(folder)","if name=='W2_max':\n            chain=original['chain']\n            from m441_sim_coverage19 import values,PREFIX\n            assert values(folder/'tv/cdatafile'/(PREFIX+'autotvin_tx_V_data_V.dat'))[:10]==[0xa0000000000]*10\n            assert chain['bits']==2 and chain['output_words64']==327680\n            assert (folder/'golden.bin').read_bytes()==bytes(2621440)")
atomic(HERE/'m443_prepare_rtl04.py',t.encode('utf-8'),immutable=True)
print('PREPARE04_GENERATOR_FROZEN',sha(HERE/'m443_prepare_rtl04.py'))
