"""Record upload/alarm UI evidence; never claim board integration is complete."""
import sys,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];TASK=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'experiments/augmented_student_20261025'))
from common_joint import read,sha,save,relative,RUNS

def main():
    out=RUNS/'M528-AIoT-upload-alarm-web-03';assert not out.exists();out.mkdir()
    python='C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
    with (out/'test_stdout.raw').open('xb') as stdout,(out/'test_stderr.raw').open('xb') as stderr:rc=subprocess.run([python,'-X','utf8','-B',str(TASK/'test_server.py')],cwd=ROOT,stdout=stdout,stderr=stderr).returncode
    assert rc==0;browser=read(TASK/'qa/presentation/RESULT.json');assert browser['status']=='PASS_UPLOAD_AND_ALARM_UI_SOFTWARE_ONLY' and browser['checks']==16 and browser['visible_TTFT'] is False
    names=['server.py','test_server.py','qa_presentation.cjs','README_PRESENTATION.md','RELATIONAL_EXPERIMENT.json','static/demo.html','static/presentation.js','static/demo.css','static/presentation.css','static/style.css']
    v=dict(status='PASS_UPLOAD_ALARM_WEB_SOFTWARE_NEW_MEDIA_PENDING',files={relative(TASK/n):sha(TASK/n) for n in names},source_sha256=sha(__file__),api_tests=10,api_tests_rc=rc,browser_tests=16,browser_result_sha256=sha(TASK/'qa/presentation/RESULT.json'),screenshots={relative(f):sha(f) for f in sorted((TASK/'qa/presentation').glob('*.png'))},TTFT_visible=False,Yes_large_warning=True,No_popup_or_sound=False,new_video_upload_and_actual_RGB_sampling=True,frame_upload_board_channel_verified=False,persistent_worker_connected=False,new_demo_media_received=False,relational_question_verified=False,relational_question_UI_enabled=False,board_commands=0,model_forwards=0,heldout_opened=False,rejected_software_test='首次浏览器No分支替换视频后测试样例仍引用旧case列表，组件失败；修正测试为实际新上传帧绑定。无板端影响，未重跑模型。')
    save(out/'RESULT.json',v)
    sys.path.insert(0,str(ROOT/'scripts/optimization'));from m455456_workflow02 import synchronized
    h=sha(out/'RESULT.json');synchronized('latest_m528_upload_alarm_web03',dict(status=v['status'],result=relative(out/'RESULT.json'),sha256=h,board=False,hardware=False,live_worker_connected=False),'## M528上传视频与巨大刀具警示展示页；无TTFT展示\n\nRESULT SHA '+h+'；用户最新要求上传另外准备的视频、板端识别、Yes显示巨大红三角/警示、No不弹不响不显示警示，网页不显示TTFT或性能图。已实现100MiB有界视频上传、真实浏览器解码抽1–3张448RGB/安全NPY保存、上传帧/任务nonce绑定与能力准入；10接口检查及16真实Chrome检查通过。Yes/No报警截图为明确水印的软件测试样例，不当模型证据。当前http://127.0.0.1:8765仍未接通持久板端工作器/新帧传输门禁，按钮据实禁用；0新板/模型，旧稳定保持。用户新视频尚未提供，旧固定4/4不扩到新素材。同图两问题的三画面×两题草案已记录，待真实素材/人工可见性确认后冻结实际token；关系条件界面禁用且服务端拒绝，未自动训练/prompt搜索/开heldout。下一取得新演示视频或本机绝对路径，再做新输入教师/学生/补偿及板端验收。')
    print(v['status'],h,flush=True)
if __name__=='__main__':main()
