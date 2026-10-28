"""Record actual local UI/CPU checks, explicitly excluding pending board Web E2E."""
import hashlib,json,sys,urllib.request
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
rel=lambda p:Path(p).relative_to(ROOT).as_posix()
def main():
    out=ROOT/'deployment/mage_vl4b/optimization_v1/runs/M544-live-presentation-software-02';out.mkdir(exist_ok=False)
    browser=json.loads((HERE/'qa/live_software/RESULT.json').read_bytes());assert browser['FPGA_runs']==0 and browser['fake_predictions'] is True
    stop=ROOT/'deployment/mage_vl4b/optimization_v1/runs/M544-live-worker-COM3-import-stop-01/RESULT.json';v=json.loads(stop.read_bytes());assert v['Import_not_executed'] and v['model_forwards']==0
    with urllib.request.urlopen('http://127.0.0.1:8766/api/state',timeout=5) as r:state=json.load(r)
    assert state['web_source_sha256']==sha(HERE/'live_server.py') and state['worker'] is None
    names=['live_server.py','live_protocol.py','live_uart.ps1','run_live_worker.py','save_live_result02.py','start_demo.ps1','stop_demo_worker.ps1','启动演示.cmd','check_host_scripts.ps1','test_live_server.py','qa_live.cjs','static/demo.html','static/playback_live.js','static/demo.css','static/presentation.css','static/style.css','LIVE_BINDING.json','README_LIVE.md','record_live_ui.py']
    files={rel(HERE/n):sha(HERE/n) for n in names}
    files.update({rel(p):sha(p) for p in sorted((HERE/'qa/live_software').iterdir()) if p.suffix in ['.png','.json']})
    result=dict(status='PASS_M544_LIVE_PRESENTATION_SOFTWARE_ONLY_A53_WEB_E2E_PENDING',files=files,API_tests_passed=12,actual_PowerShell_script_parses=3,actual_DotNet_packet_roundtrip=True,actual_DotNet_rejected_packets=3,browser_checks=browser,actual_test_exit_codes=[0,0,0],test_log_origin='实际工具stdout已核；未另捕获原进程日志，不补造。',preview='http://127.0.0.1:8766/',worker_online=False,board_commands_in_this_record=0,model_forwards=0,actual_Web_board_E2E_pass=False,waiting_for_human_root_shell_confirmation=True,Import_stop_sha256=sha(stop),No_result_region_hidden=True,TTFT_not_rendered=True,actual_play_triggers_fresh_job=True,filename_or_history_cannot_answer=True,one_representative_frame_per_playback=True,new_worker_session_cancels_stale_jobs=True,ordinary_stop_only_no_signals=True,software_rejected_attempts=['Chrome测试初版未等verify回调完便关闭页面，已修测试生命周期；没有板端影响。','原重新演示时视频仍播放导致没有新play事件，已修为pause再seek/play，真实Chrome复测通过。','提前点击原生播放可能使准备结束时不再触发play，已在输入准备期暂停并复测。'],scope='网页界面/本地数据接口/桥协议CPU。原M543固定帧实板证据保持，不冒充M544新网页到板已经完成。')
    p=out/'RESULT.json';p.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');h=sha(p)
    (out/'REPORT.md').write_text('# M544 本地演示网页软件核验\n\n视频播放触发新任务；实际Yes才报警，No隐藏判断和报警区域，页面不显示TTFT。12后端测试、实际.NET压缩/哈希往返及3坏包、真实Chrome播放/重播/静默/异常/手机布局通过。截图带软件样例水印，不作为新增实板识别证据。\n\n当前预览 http://127.0.0.1:8766/ ，双击 apps/campus_guard/启动演示.cmd。一个代表画面每次真实推理，非整视频连续扫描；已知视频固定源帧仅绑定输入，无预置答案。\n\nCOM3未确认root，M544实际A53 Import和网页实板E2E未执行。0新板命令/模型/信号；等待已发送的唯一人工就绪答复，之后只续Import、不重Install或旧模型测试。稳定回滚保持。\n\nRESULT SHA '+h+'\n',encoding='utf-8')
    sys.path.insert(0,str(ROOT/'scripts/optimization'));from m455456_workflow02 import synchronized
    synchronized('latest_m544_live_presentation_software02',dict(status=result['status'],result=rel(p),sha256=h,board=False,hardware=False,live_worker_connected=False,promoted=False),'## M544本地播放触发与报警网页软件完成\n\nRESULT SHA '+h+'；12数据接口检查、实际.NET ZLib/SHA往返与3坏包、Chrome播放/重新演示/No隐藏/异常/移动布局通过；仅软件样例截图，0新模型/板命令。8766本地预览及双击启动入口完成，真实play新nonce，实际Yes红色大警示、No无结果、不显示TTFT；每播放一张明确代表帧，非连续逐帧。新会话取消旧排队任务，正常data-stop无信号。M544真实Import因COM3未确认shell尚未执行，待唯一人工root就绪答复后只续本级；不重Install、不伪装Web板测完成，原M543实板/稳定回滚保持。')
    print(result['status'],h)
if __name__=='__main__':main()
