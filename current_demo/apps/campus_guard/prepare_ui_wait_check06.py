"""Render software browser check against an isolated local DB/port, no active worker interference."""
from pathlib import Path
HERE=Path(__file__).resolve().parent
text=(HERE/'qa_live.cjs').read_text(encoding='utf-8').replace("base='http://127.0.0.1:8766'","base='http://127.0.0.1:8767'").replace('qa/live_software','qa/preparation_software06')
text=text.replace("let mock=await", "let inputReady=false;let mock=await").replace('d.board_prepared=true','d.board_prepared=inputReady')
old="  await upload('data/campus_demo_20261025/source/campus_03.mp4');await waitCalls(1);"
new="  await upload('data/campus_demo_20261025/source/campus_03.mp4');await page.locator('#input-preparation-notice').waitFor({state:'visible'});assert(await page.locator('#start-button').isDisabled());assert.equal(await page.locator('#start-button').innerText(),'画面准备中');assert.equal(calls,0);await page.locator('#video-player').evaluate(v=>v.play().catch(()=>{}));await page.waitForTimeout(300);assert(await page.locator('#video-player').evaluate(v=>v.paused));assert.equal(calls,0);await page.screenshot({path:path.join(out,'input_wait_TEST_ONLY.png'),fullPage:true});inputReady=true;await waitCalls(1);"
assert text.count(old)==1;text=text.replace(old,new).replace("'real play triggers job'","'input wait visible above video and button named','early native play pauses with zero model submission','real play triggers job'")
(HERE/'qa_preparation06.cjs').open('x',encoding='utf-8').write(text)
print('Prepared isolated UI regression')
