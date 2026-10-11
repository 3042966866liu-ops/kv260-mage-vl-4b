"""Real temporary-file tests; parser/root are explicit offline fakes only."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch
import m351_workflow as w
import m363_tokenizer_once as t
import m363_assemble as a

def check():
    checks=[]
    with tempfile.TemporaryDirectory() as directory:
        root=Path(directory);p=root/'tokenizer';p.write_bytes(b'fixture')
        calls=[];obj=object();once=t.ValidatedTokenizerOnce(lambda path:calls.append(path) or obj)
        assert once.from_file(str(p)) is obj and once.cached is obj
        assert once.from_file(str(p)) is obj and once.cached is None and len(calls)==1
        try:once.from_file(str(p))
        except RuntimeError:pass
        else:raise AssertionError('Third parse accepted')
        checks.append('single parse, same original object, cache ownership transferred, third call rejects')
        once=t.ValidatedTokenizerOnce(lambda path:obj);once.from_file(str(p));p.write_bytes(b'changed fixture')
        try:once.from_file(str(p))
        except RuntimeError:pass
        else:raise AssertionError('Changed identity reused')
        checks.append('actual file changes reject reuse')
        def changed(path):p.write_bytes(b'changed again');return obj
        once=t.ValidatedTokenizerOnce(changed)
        try:once.from_file(str(p))
        except RuntimeError:pass
        else:raise AssertionError('Changed during parse accepted')
        assert once.parse_count==0 and once.cached is None
        checks.append('file changes during parse reject before cache ownership')
    with tempfile.TemporaryDirectory() as directory:
        root=Path(directory);old=root/'old';new=root/'new';old.mkdir();new.mkdir()
        (old/'unchanged').write_bytes(b'exact payload');(new/'delta').write_bytes(b'new payload')
        oldrows=[dict(path='unchanged',bytes=13,sha256=a.sha(old/'unchanged'))]
        (old/'PACKAGE_MANIFEST.json').write_text(json.dumps(dict(files=oldrows)),encoding='utf-8')
        newrows=[dict(path='copied',bytes=13,sha256=oldrows[0]['sha256']),dict(path='delta',bytes=11,sha256=a.sha(new/'delta'))]
        (new/'PACKAGE_MANIFEST.json').write_text(json.dumps(dict(files=newrows,file_count=2,total_bytes=24)),encoding='utf-8')
        oldsha=a.sha(old/'PACKAGE_MANIFEST.json');newsha=a.sha(new/'PACKAGE_MANIFEST.json')
        with patch.object(a,'PRIOR',old),patch.object(a,'TARGET',new),patch.object(a,'PRIOR_SHA',oldsha),patch.object(a.os,'geteuid',lambda:0,create=True),patch.object(sys,'argv',['assemble',newsha]):
            with contextlib.redirect_stdout(io.StringIO()):a.assemble()
            assert (new/'copied').read_bytes()==b'exact payload'
            checks.append('real SHA-based copy and exact new whitelist')
            for mutate,restore in [(lambda:(old/'unchanged').write_bytes(b'corrupt'),lambda:(old/'unchanged').write_bytes(b'exact payload')),(lambda:(new/'delta').unlink(),lambda:(new/'delta').write_bytes(b'new payload')),(lambda:(new/'extra').write_bytes(b'x'),lambda:(new/'extra').unlink())]:
                mutate()
                try:a.assemble()
                except RuntimeError:pass
                else:raise AssertionError('Invalid assembly accepted')
                restore()
                checks.append('assembly refuses corruption, missing new delta or extra entry')
    out=w.BASE/'runs/M363-correction-support-01/RESULT.json'
    result=dict(status='PASS_OFFLINE_ONE_TOKENIZER_CORRECTION',checks=checks,fake_parser_and_root_only=True,actual_temp_files=True,board_executed=False,capacity_proven=False,production_source_changed=False)
    w.atomic(out,w.encoded(result),immutable=True)
    print(result['status'],w.sha(out))

if __name__=='__main__':check()
