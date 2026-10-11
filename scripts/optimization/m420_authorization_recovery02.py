"""Limit the recovery diff to the transfer default; keep component evidence02."""
from pathlib import Path
source=Path(__file__).with_name('m420_authorization_recovery.py').read_text(encoding='utf-8')
old="neww=oldw.replace('tmp/m42001','tmp/m42002');assert neww.replace('tmp/m42002','tmp/m42001')==oldw"
new="neww=oldw.replace(\"folder=ROOT/'tmp/m42001'\",\"folder=ROOT/'tmp/m42002'\");assert neww.replace(\"folder=ROOT/'tmp/m42002'\",\"folder=ROOT/'tmp/m42001'\")==oldw"
assert source.count(old)==1
source=source.replace(old,new).replace("'m420_authorization_recovery.py','m420_control02.ps1'","'m420_authorization_recovery02.py','m420_control02.ps1'")
exec(compile(source,str(Path(__file__)), 'exec'))
