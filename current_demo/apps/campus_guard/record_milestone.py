"""Record verified UI-only milestone without promoting hardware deployment."""
import hashlib,json,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'experiments/augmented_student_20261025'))
from common_joint import read,sha,save,relative,RUNS

def main():
    out=RUNS/'M528-AIoT-campus-web-01';assert not out.exists();out.mkdir()
    python='C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
    with (out/'test_stdout.raw').open('xb') as stdout,(out/'test_stderr.raw').open('xb') as stderr:
        rc=subprocess.run([python,'-X','utf8','-B',str(HERE/'test_server.py')],stdout=stdout,stderr=stderr,cwd=ROOT).returncode
    assert rc==0;browser=read(HERE/'qa/browser_result.json');assert browser['checks']==15 and browser['status']=='PASS_BROWSER_UI_WORKFLOW_NO_HARDWARE'
    names=['server.py','prepare_assets.py','test_server.py','qa_browser.cjs','catalog.json','README.md','COMPETITION_SCOPE.json','static/index.html','static/style.css','static/app.js']+[str(p.relative_to(HERE)).replace('\\','/') for p in sorted((HERE/'static/frames').glob('*.png'))]
    value=dict(status='PASS_LOCAL_CAMPUS_WEB_UI_NOT_LIVE_FPGA',source_sha256=sha(__file__),software_checks=7,software_checks_rc=rc,browser_checks=15,browser_result_sha256=sha(HERE/'qa/browser_result.json'),screenshots={relative(HERE/'qa'/n):sha(HERE/'qa'/n) for n in ('desktop.png','mobile.png','report.png')},files=[dict(path=relative(HERE/n),bytes=(HERE/n).stat().st_size,sha256=sha(HERE/n)) for n in names],fixed_demo_only=True,actual_board_commands=0,Overlay=0,DMA=0,live_worker_connected=False,MQTT_configured=False,recorded_board_evidence_sha256=read(HERE/'catalog.json')['evidence_sha256'],current_url='http://127.0.0.1:8765',known_limits=['网页侧实时队列与结果证据校验已实现，COM3持久工作器尚未接通','MQTT尚未配置','仅固定两视频四窗口，非校园实拍或泛化质量证明'],rejected_checks=['首次后端检查发现SQLite连接未关闭导致Windows临时目录清理失败；修正为显式contextmanager关闭后7项通过','默认Playwright headless shell未安装，复用已安装Chrome，不下载浏览器','浏览器截图发现提示条span选择器误命中图标；修正作用域后15项通过','Windows允许SO_REUSEADDR重复监听，已精确关闭两个本地网页进程并启用端口独占；未接触板进程'])
    save(out/'RESULT.json',value)
    sys.path.insert(0,str(ROOT/'scripts/optimization'));from m455456_workflow02 import synchronized
    h=sha(out/'RESULT.json');synchronized('latest_m528_campus_web01',dict(status=value['status'],result=relative(out/'RESULT.json'),sha256=h,board=False,hardware=False,live_worker_connected=False,production_promoted=False),'## M528传智杯AIoT固定演示网页首版与范围冻结\n\nRESULT SHA '+h+'；用户明确10月28日前，以固定视频/问题判断正确、TTFT低、展示效果为优先，不再扩Decode或泛化训练。本地校园安保值班台已完成两个模拟机位、四窗口实际截图/视频、旧实板记录/首次与热态分列、证据查看、人工处置/SQLite审计及JSON导出；7后端检查+15实际Chrome桌面/手机检查通过，截图逐SHA。当前http://127.0.0.1:8765为实板记录查看模式；网页侧实时串行队列与nonce/帧/模型/完整词表结果准入已实现，COM3持久工作器未接通，MQTT未配置。0本次板命令/Overlay/DMA，不当L7部署或新测速证据。M525实测4/4、热29.174秒保持旧头范围，M526全No失败不覆盖。下一接入原安全生命周期的持久工作器，固定四窗口重复实板与网页触发耗时核验后再冻结参赛包；10月27日安排最终录制与交付。')
    print(value['status'],h,flush=True)
if __name__=='__main__':main()
