"""Own isolated Python UI fixture server + Chrome test; never reaches live board port."""
import hashlib,json,subprocess,sys,time,urllib.request
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def main():
    out=HERE/'qa/preparation_software06';out.mkdir(parents=True,exist_ok=False)
    raw=(out/'server.stdout').open('xb');err=(out/'server.stderr').open('xb')
    child=subprocess.Popen([sys.executable,'-X','utf8','-B',str(HERE/'live_server.py'),'--port','8767','--database',str(HERE/'var/ui_wait06/events.sqlite')],cwd=ROOT,stdout=raw,stderr=err,creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        for _ in range(50):
            try:
                with urllib.request.urlopen('http://127.0.0.1:8767/api/state',timeout=1) as r:s=json.load(r)
                assert s['worker'] is None;break
            except OSError:time.sleep(.1)
        else:raise RuntimeError('Isolated fixture server not ready')
        with (out/'browser.stdout').open('xb') as f:rc=subprocess.run(['C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe',str(HERE/'qa_preparation06.cjs')],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT).returncode
        print('Isolated browser original rc',rc,(out/'browser.stdout').read_text(encoding='utf-8-sig')[-1200:]);return rc
    finally:
        child.terminate();child.wait(timeout=5);raw.close();err.close()
if __name__=='__main__':raise SystemExit(main())
