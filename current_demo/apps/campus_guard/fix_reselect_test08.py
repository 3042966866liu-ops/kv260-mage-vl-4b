"""Match the real Choose button's clearing of same-file input; preserve07 failure."""
from pathlib import Path
HERE=Path(__file__).resolve().parent
text=(HERE/'qa_preparation07.cjs').read_text(encoding='utf-8').replace('preparation_software07','preparation_software08')
needle="assert.equal(uploaded,2);await page.locator('#video-file').setInputFiles"
assert text.count(needle)==1
text=text.replace(needle,"assert.equal(uploaded,2);await page.locator('#video-file').evaluate(e=>e.value='');await page.locator('#video-file').setInputFiles")
(HERE/'qa_preparation08.cjs').open('x',encoding='utf-8').write(text)
host=(HERE/'run_ui_reuse_check07.py').read_text(encoding='utf-8').replace('preparation_software07','preparation_software08').replace('ui_wait07','ui_wait08').replace('qa_preparation07.cjs','qa_preparation08.cjs');compile(host,'run_ui_reselect08.py','exec');(HERE/'run_ui_reselect08.py').open('x',encoding='utf-8').write(host)
print('07 original kept; 08 models actual file chooser same-file change event')
