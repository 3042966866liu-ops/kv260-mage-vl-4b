"""Record successful current browser checks; all predictions are synthetic UI fixtures."""
import sys,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];APP=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def rel(p):return Path(p).relative_to(ROOT).as_posix()
def main():
    out=ROOT/'deployment/mage_vl4b/optimization_v1/runs/M528-AIoT-playback-alarm-web-04';out.mkdir(exist_ok=False)
    browser=json.loads((APP/'qa/playback/RESULT.json').read_bytes());assert browser['status']=='PASS_PLAYBACK_AUTOSTART_SILENT_NEGATIVE_SOFTWARE_ONLY' and browser['board_runs']==0
    names=['static/presentation.js','static/demo.html','qa_playback.cjs','README_PRESENTATION.md','server.py','test_server.py','record_playback.py']
    files={rel(APP/n):sha(APP/n) for n in names}
    files.update({rel(p):sha(p) for p in sorted((APP/'qa/playback').iterdir()) if p.suffix in ('.png','.json')})
    v=dict(status='PASS_PLAYBACK_AUTOSTART_SILENT_NEGATIVE_UI_NOT_LIVE_BOARD',files=files,browser_checks=browser,api_tests=10,api_rc=0,api_result_origin='实际工具调用test_server.py，10项通过；未另保存原stdout文件，不补造。',no_result_text=True,playback_autostart=True,actual_board_runs=0,actual_model_runs=0,board_worker_connected=False,uploaded_frame_channel_verified=False,old_stable_unchanged=True,new_media_quality_verified=False,software_rejected_attempts=['首轮浏览器测试在API route回调完成前检查计数，断言导致关闭页面；修正等待真实verify响应。','第二轮测试把页脚静态安全说明中的“无刀具”当作结果提示，改为断言结果行空且隐藏；最终通过。','首次多文件patch因既有HTML选项标签格式与预期不同拒绝，未写入；按实际文本修正，并恢复独立禁用的关系选项。'])
    result=out/'RESULT.json';result.open('x',encoding='utf-8').write(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
    sys.path.insert(0,str(ROOT/'scripts/optimization'));from m455456_workflow02 import synchronized
    h=sha(result);synchronized('latest_m528_playback_alarm_web04',dict(status=v['status'],result=rel(result),sha256=h,board=False,hardware=False,live_worker_connected=False),'## M528播放自动触发与无刀完全静默界面\n\nRESULT SHA '+h+'；上传/采样完成后真实play事件自动提交，不再另点识别；暂停/继续/已完成重播不重复模型任务。真实Yes后巨大红三角/红边框并锁存，No隐藏结果行且无结果文字/弹窗/声音，等待及Unknown仍显式非结果状态。修复既有HTML关系选项标签并保持未验收条件禁用。10后端测试及真实Chrome三段上传/5次合成接口响应、手机布局通过，报警截图明确软件样例水印；0板/模型，不当新视频识别已通过。新素材与旧实验室已收到；持久工作器/上传帧板端通道尚未接通，不继承旧29秒或4/4。30秒视频偏紧，45–60秒只是演示余量建议，不预设报警时点。旧稳定回滚不动，下一新素材实际验收及通道联调。')
    print(v['status'],h)
if __name__=='__main__':main()
