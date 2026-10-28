"""Restart only the fresh TCP/CIM-confirmed project-owned local web process."""
from pathlib import Path
import ctypes,hashlib,json,subprocess,sys,time,urllib.request
from ctypes import wintypes
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];out=HERE/'var/live/launcher/boot07'
before=json.loads((out/'before.json').read_bytes());pid=int(before['ProcessId']);exe=Path(sys.executable).resolve()
assert 'apps/campus_guard/live_server.py --port 8766' in before['CommandLine'].replace(chr(92),'/') and Path(before['ExecutablePath']).resolve()==exe
with urllib.request.urlopen('http://127.0.0.1:8766/api/state',timeout=3) as r:s=json.load(r)
assert s['worker'] is None and s['web_source_sha256']==hashlib.sha256((HERE/'live_server.py').read_bytes()).hexdigest()
k=ctypes.WinDLL('kernel32',use_last_error=True);k.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD];k.OpenProcess.restype=wintypes.HANDLE
k.QueryFullProcessImageNameW.argtypes=[wintypes.HANDLE,wintypes.DWORD,wintypes.LPWSTR,ctypes.POINTER(wintypes.DWORD)];k.QueryFullProcessImageNameW.restype=wintypes.BOOL
k.TerminateProcess.argtypes=[wintypes.HANDLE,wintypes.UINT];k.TerminateProcess.restype=wintypes.BOOL;k.WaitForSingleObject.argtypes=[wintypes.HANDLE,wintypes.DWORD];k.WaitForSingleObject.restype=wintypes.DWORD;k.CloseHandle.argtypes=[wintypes.HANDLE]
handle=k.OpenProcess(0x100000|0x1000|1,False,pid)
if not handle:raise ctypes.WinError(ctypes.get_last_error())
try:
 buf=ctypes.create_unicode_buffer(32768);n=wintypes.DWORD(len(buf));assert k.QueryFullProcessImageNameW(handle,0,buf,ctypes.byref(n)) and Path(buf.value).resolve()==exe
 (out/'RESTART_INTENT.json').open('x').write(json.dumps(dict(pid=pid,exe=str(exe),board_actions=0)))
 if not k.TerminateProcess(handle,0):raise ctypes.WinError(ctypes.get_last_error())
 assert k.WaitForSingleObject(handle,5000)==0
finally:k.CloseHandle(handle)
with (out/'server.out').open('xb') as stdout,(out/'server.err').open('xb') as stderr:child=subprocess.Popen([str(exe),'-X','utf8','-B','apps/campus_guard/live_server.py','--port','8766'],cwd=ROOT,stdout=stdout,stderr=stderr,creationflags=subprocess.CREATE_NO_WINDOW)
binding=json.loads((HERE/'LIVE_BINDING.json').read_bytes())
for _ in range(50):
 try:
  with urllib.request.urlopen('http://127.0.0.1:8766/api/state',timeout=2) as r:s=json.load(r)
  if s['worker_package_sha256']==binding['package_manifest_sha256']:break
 except OSError:pass
 time.sleep(.1)
else:raise RuntimeError('New server binding not observed')
(out/'RESULT.json').open('x').write(json.dumps(dict(status='RESTARTED_EXACT_OWNED_LOCAL_SERVER06',pid=child.pid,old_pid=pid,manifest=binding['package_manifest_sha256'],board_actions=0)))
print('OWNED_SERVER06_READY',child.pid)
