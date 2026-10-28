"""Resume only unsubmitted Web checks after input preparation timeout; keep original worker."""
import json,sqlite3
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];RUNS=ROOT/'deployment/mage_vl4b/optimization_v1/runs'
failure=json.loads((RUNS/'M544-live-browser-board-03/FAILURE.json').read_bytes());assert failure['results']==[]
c=sqlite3.connect(HERE/'var/live/events.sqlite');count=c.execute("SELECT COUNT(*) FROM events WHERE kind='live'").fetchone()[0];assert count==0,'Do not repeat a submitted task'
uid=c.execute('SELECT id FROM uploads WHERE sha256=? ORDER BY created DESC LIMIT 1',('cc9598b288f4f4a0d0edb0d91364dffdbcb05d7a3b715fc4c18de69e6f28b3d8',)).fetchone()[0];c.close()
text=(HERE/'qa_live_board03.cjs').read_text(encoding='utf-8').replace('M544-live-browser-board-03','M544-live-browser-board-04').replace('240000','600000')
old="   await page.locator('#video-file').setInputFiles(path.join(root,item.file));const response=await requested;"
assert text.count(old)==1
new="   if(item.id==='campus03'){await page.goto(base+'/?upload="+uid+"',{waitUntil:'networkidle'})}else{await page.locator('#video-file').setInputFiles(path.join(root,item.file))}const response=await requested;"
text=text.replace(old,new);(HERE/'qa_live_board04.cjs').open('x',encoding='utf-8').write(text)
print('Prepared only the two still-unsubmitted checks; original worker/input retained',uid)
