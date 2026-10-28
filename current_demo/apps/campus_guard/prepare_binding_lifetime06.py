"""Render binding/restart steps; they remain gated on actual Import06."""
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
s=(HERE/'bind_boot05.py').read_text(encoding='utf-8')
for a,b in [('M544-campus-live-worker-preparation-05','M544-campus-live-worker-preparation-06'),('M544-campus-live-worker-board-05','M544-campus-live-worker-board-06'),('M544-live-binding-current-boot-05','M544-live-binding-current-boot-06'),('LIVE_BINDING_before05','LIVE_BINDING_before06'),('BOUND_M544_CURRENT_BOOT05_AFTER_A53_IMPORT','BOUND_M544_SIX_HOUR_SESSION06_AFTER_A53_IMPORT'),('latest_m544_binding05','latest_m544_binding06')]:s=s.replace(a,b)
needle="assert v['primary_rc']==0 and v['package_manifest_sha256']==p['manifest_sha256'] and v['CPU_components']['live_frame_protocol']['negative_cases']==13"
assert s.count(needle)==1;s=s.replace(needle,needle+"\nassert v['CPU_components']['live_frame_protocol']['session_lifetime']['six_hour_absolute_bound']\nassert p['expected_boot']=='f425c270-dc5e-4a1d-98de-025c85938620'")
s=s.replace("'server_restart_required=True'","'server_restart_required=True'")
compile(s,'bind_lifetime06.py','exec');(HERE/'bind_lifetime06.py').open('x',encoding='utf-8').write(s)
s=(HERE/'restart_owned_boot05.ps1').read_text(encoding='utf-8-sig').replace('launcher/boot05','launcher/boot06')
s=s[:s.index('Stop-Process -Id $ownerId')]+"& $python -X utf8 -B apps/campus_guard/restart_from_record06.py\nexit $LASTEXITCODE\n"
(HERE/'restart_owned_boot06.ps1').open('x',encoding='utf-8').write(s)
print('Prepared bound restart06, no changes to live binding yet')
