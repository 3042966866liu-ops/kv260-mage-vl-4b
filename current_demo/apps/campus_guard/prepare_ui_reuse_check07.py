"""Add identical-input reselect regression to the isolated browser fixture."""
from pathlib import Path
HERE=Path(__file__).resolve().parent
text=(HERE/'qa_preparation06.cjs').read_text(encoding='utf-8').replace('preparation_software06','preparation_software07')
text=text.replace('let inputReady=false;let mock=await','let uploaded=0;page.on(\'request\',r=>{if(r.url()===base+\'/api/uploads\'&&r.method()===\'POST\')uploaded++});let inputReady=false;let mock=await')
needle="  await page.locator('#start-button').click();await waitCalls(3);"
replacement="  assert.equal(uploaded,2);await page.locator('#video-file').setInputFiles(path.join(root,'data/campus_demo_20261026/campus_12.mp4'));await waitCalls(3);await page.waitForFunction(()=>document.querySelector('#recognition-status').hidden);assert.equal(uploaded,2,'same exact video reuses prepared pixels, not a new upload');\n  await page.locator('#start-button').click();await waitCalls(4);"
assert text.count(needle)==1;text=text.replace(needle,replacement).replace("assert.equal(calls,3,'explicit replay","assert.equal(calls,4,'explicit replay").replace('await waitCalls(4);await page.waitForFunction(()=>document.querySelector(\'#status-text\')','await waitCalls(5);await page.waitForFunction(()=>document.querySelector(\'#status-text\')').replace('assert.equal(calls,4);assert(await page.locator(\'#knife-warning\')','assert.equal(calls,5);assert(await page.locator(\'#knife-warning\')').replace("'explicit replay fresh job'","'identical input reselect reuses bytes but creates fresh model job','explicit replay fresh job'")
(HERE/'qa_preparation07.cjs').open('x',encoding='utf-8').write(text)
host=(HERE/'run_ui_wait_check06.py').read_text(encoding='utf-8').replace('preparation_software06','preparation_software07').replace('ui_wait06','ui_wait07').replace('qa_preparation06.cjs','qa_preparation07.cjs');compile(host,'run_ui_reuse_check07.py','exec');(HERE/'run_ui_reuse_check07.py').open('x',encoding='utf-8').write(host)
print('Prepared isolated same-input reuse regression')
