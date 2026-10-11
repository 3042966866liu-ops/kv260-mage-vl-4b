#!/usr/bin/env python3
import base64,hashlib,os,sys,termios
from pathlib import Path

A={
 Path('/home/ubuntu/tellme_m120_m89x2_20260901/m166_delta_01/auxiliary/M77_TEXT_AUX_MANIFEST.json'):(25926,'122d2d9ba268802b86422d1d888855c5f2f30e4851adcc450cf3736a17669d2a'),
 Path('/home/ubuntu/tellme_m120_m89x2_20260901/m166_delta_01/auxiliary/m77_text_aux_fp16.npz'):(315138,'7f2dfc14ae47cb537e148cafc9b1c6cc285e1fe546dec901275a4078a8458ffd'),
}
E='__M166_UART_FILE_EOF__'
def H(p):return hashlib.sha256(p.read_bytes()).hexdigest()
p=Path(sys.argv[1]).resolve();n=int(sys.argv[2]);h=sys.argv[3];me=sys.argv[4]
if H(Path(__file__))!=me:raise RuntimeError('M166 receiver self hash mismatch')
if p not in A:raise RuntimeError('M166 receiver path mismatch')
if (n,h)!=A[p]:raise RuntimeError('M166 receiver declared identity mismatch')
if p.exists():
 if p.stat().st_size==n and H(p)==h:
  print('M166_UART_FILE_ALREADY_VERIFIED',flush=True);print('M166_UART_FILE_RECEIVE_PASS',flush=True);raise SystemExit(0)
 raise RuntimeError('M166 existing member identity mismatch')
t=Path(str(p)+'.partial')
if t.exists():raise RuntimeError('M166 partial exists')
a=termios.tcgetattr(0);q=a.copy();q[3]&=~termios.ECHO;termios.tcsetattr(0,termios.TCSANOW,q)
x=[];print('M166_UART_FILE_RECEIVER_READY',flush=True)
try:
 while True:
  s=sys.stdin.readline()
  if not s:raise RuntimeError('M166 UART closed')
  s=s.strip()
  if s==E:break
  x.append(s)
finally:termios.tcsetattr(0,termios.TCSANOW,a)
d=base64.b64decode(''.join(x),validate=True)
if len(d)!=n or hashlib.sha256(d).hexdigest()!=h:raise RuntimeError('M166 stream identity mismatch')
p.parent.mkdir(parents=True,exist_ok=True)
try:t.write_bytes(d);os.chmod(t,0o755);os.replace(t,p)
finally:
 if t.exists():t.unlink()
print('M166_UART_FILE_VERIFIED',n,h,flush=True);print('M166_UART_FILE_RECEIVE_PASS',flush=True)
