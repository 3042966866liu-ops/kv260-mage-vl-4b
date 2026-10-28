from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
out=ROOT/'deployment/mage_vl4b/optimization_v1/runs/M544-disconnected-status-UI-06';out.mkdir(exist_ok=False)
p=HERE/'static/playback_live.js';s=p.read_text(encoding='utf-8');(out/'before_playback_live.js').open('xb').write(p.read_bytes())
old="inputNotice.textContent=w?.warm?'正在准备识别画面，准备完成后才能开始播放与推理。':'正在等待模型初始化，完成后继续准备视频画面。'"
new="inputNotice.textContent=!w?'板端工作器未连接，当前尚未开始识别。':w.warm?'正在准备识别画面，准备完成后才能开始播放与推理。':'正在等待模型初始化，完成后继续准备视频画面。'"
assert s.count(old)==1;s=s.replace(old,new)
old="scanning?'正在识别':preparing?'画面准备中'";assert s.count(old)==1;s=s.replace(old,"scanning?'正在识别':upload&&!w?'等待板卡连接':preparing?'画面准备中'")
old="preparing:state?.worker?'正在将画面准备到板端':'等待板卡准备就绪',waiting:preparing?'正在将画面准备到板端，完成后自动播放':'等待当前板端任务完成'"
new="preparing:!w?'等待板卡连接，当前尚未开始识别':!w.warm?'模型初始化中，尚未传输画面':'正在将画面准备到板端',waiting:!w?'等待板卡连接，当前尚未开始识别':!w.warm?'模型初始化中，尚未传输画面':preparing?'正在将画面准备到板端，完成后自动播放':'等待当前板端任务完成'"
assert s.count(old)==1;s=s.replace(old,new);p.write_text(s,encoding='utf-8')
p=HERE/'static/demo.html';(out/'before_demo.html').open('xb').write(p.read_bytes());s=p.read_text(encoding='utf-8');assert '?v=selected-input05' in s;p.write_text(s.replace('?v=selected-input05','?v=lifetime06'),encoding='utf-8')
print('Disconnected status fixed')
