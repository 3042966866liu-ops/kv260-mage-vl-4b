"""Real file bytes with explicitly simulated root ownership in offline fixtures."""
import hashlib,io,json,tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np

def component():
    import m427_saved_baseline as helper
    from m414_quality import tensor
    checks=[]
    def reject(name,fn):
        try:fn()
        except (ValueError,RuntimeError):checks.append(name)
        else:raise AssertionError('Invalid baseline accepted '+name)
    with tempfile.TemporaryDirectory() as directory:
        folder=Path(directory);x=np.arange(24,dtype=np.float32).reshape(4,6)
        output=io.BytesIO();np.save(output,x,allow_pickle=False);raw=output.getvalue();p=folder/'original_visual.npy';p.write_bytes(raw)
        real=Path.lstat
        def owner(path,*a,**kw):
            s=real(path,*a,**kw);return SimpleNamespace(**{name:getattr(s,name) for name in ('st_dev','st_ino','st_size','st_mtime_ns','st_ctime_ns','st_mode','st_nlink')},st_uid=0)
        with patch.object(Path,'lstat',owner):
            assert np.array_equal(helper.array(p.name,tensor(x),hashlib.sha256(raw).hexdigest(),folder),x)
            reject('file-SHA',lambda:helper.array(p.name,tensor(x),'0'*64,folder))
            wrong=tensor(x);wrong['sha256']='0'*64;reject('tensor-SHA',lambda:helper.array(p.name,wrong,folder=folder))
            reject('whitelist',lambda:helper.array('../wrong',tensor(x),folder=folder))
            reject('size',lambda:helper.read_owned(p,1))
            calls=[0]
            def changed(path,*a,**kw):
                s=owner(path,*a,**kw);calls[0]+=1
                if calls[0]%2==0:s.st_mtime_ns+=1
                return s
            with patch.object(Path,'lstat',changed):reject('identity-during-read',lambda:helper.read_owned(p,len(raw)))
            r=dict(status='REJECT_M426_ALL22_FEATURE_RANGE',gate_return_code=0,original_reference_pass=True,bindings_restored=True,visual_owner_closed=True,selected_layers=list(range(2,24)),overlay_loaded=False,dma_allocations=0,fpga_transactions=0)
            def source(value):
                b=json.dumps(value).encode('utf-8');(folder/'BOARD_RESULT.json').write_bytes(b)
                with patch.object(helper,'BASELINE',folder):return helper.source(dict(baseline_raw_bytes=len(b),baseline_raw_sha256=hashlib.sha256(b).hexdigest()))
            assert source(r)==r
            reject('source-status',lambda:source(dict(r,status='PASS_OTHER')))
            reject('source-rc-bool',lambda:source(dict(r,gate_return_code=False)))
            reject('source-owner-live',lambda:source(dict(r,visual_owner_closed=False)))
        def nonroot(path,*a,**kw):
            s=owner(path,*a,**kw);s.st_uid=1000;return s
        with patch.object(Path,'lstat',nonroot):reject('non-root-owner',lambda:helper.read_owned(p,len(raw)))
    assert len(checks)==9
    return dict(real_fixture_file_bytes=True,ownership_explicitly_simulated_offline=True,strict_board_root_ownership_required=True,negative_checks=checks)
