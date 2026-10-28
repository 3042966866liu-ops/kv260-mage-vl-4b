"""ctypes bridge with frozen-parser metadata checks; never opens hardware."""
import ctypes
from pathlib import Path
import numpy as np


class GateUpNative:
    def __init__(self, library=None):
        if library is None:library=Path(__file__).with_name('libgate_up_native.so')
        self.library=ctypes.CDLL(str(Path(library).resolve()))  # releases GIL per call
        self.library.m455_parser_abi.restype=ctypes.c_uint32
        if self.library.m455_parser_abi()!=0x20261024:raise RuntimeError('Parser ABI mismatch')
        fn=self.library.m455_parse_descriptor
        fn.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_void_p,ctypes.c_size_t,ctypes.c_size_t,
                     ctypes.c_uint,ctypes.c_uint,ctypes.c_uint,ctypes.c_uint]
        fn.restype=ctypes.c_int
        self.fn=fn

    def parse(self,chain,payload,targets,token_start,token_count,output_scale_shift):
        # Keep the original identity/geometry/alias/write-plan checks. Validate
        # every descriptor and the full-destination reshape before any C write.
        if not isinstance(output_scale_shift,int) or not 0<=output_scale_shift<=10:
            raise ValueError('output_scale_shift must be an integer in [0, 10]')
        if not 1<=token_count<=32 or token_start<0:raise ValueError('invalid token slice')
        if chain.get('output_abi')!='m455-dense-fp16-block-token-shard-pair-v1' or chain.get('expected_build_id')!=0x4D343535:
            raise ValueError('Dense ABI identity required')
        raw=memoryview(payload).cast('B')
        if len(raw)!=int(chain['output_bytes']):raise RuntimeError('M455 dense output packet size mismatch')
        plan=[];cursor=0
        for descriptor in chain['descriptors']:
            rows=int(descriptor['rows_per_shard']);size=int(descriptor['output_bytes'])
            valid=int(descriptor['valid_rows']);start=int(descriptor['row_start'])
            name=descriptor.get('module','lm_head')
            if rows<=0 or rows>4096 or rows%8 or size!=32*4*rows*2:raise RuntimeError('M455 dense descriptor geometry mismatch')
            if not 0<valid<=4*rows or start<0 or cursor+size>len(raw):raise RuntimeError('M455 dense descriptor bounds mismatch')
            target=targets.get(name)
            if not isinstance(target,np.ndarray) or target.dtype!=np.float32 or target.ndim!=2 or not target.flags.writeable or target.shape[0]<token_start+token_count or target.shape[1]<start+valid or min(target.strides)<=0:
                raise RuntimeError('M455 dense preallocated target is incomplete or unsafe')
            source=np.frombuffer(raw[cursor:cursor+size],dtype=np.uint8)
            if np.may_share_memory(source,target):raise RuntimeError('M455 dense DMA packet aliases final output')
            destination=target[token_start:token_start+token_count,start:start+valid]
            if valid==4*rows:
                view=destination.reshape(token_count,4,rows//8,4,2)
                expected=(destination.strides[0],rows*destination.strides[1],8*destination.strides[1],2*destination.strides[1],destination.strides[1])
                if view.ctypes.data!=destination.ctypes.data or any(n>1 and actual!=wanted for n,actual,wanted in zip(view.shape,view.strides,expected)):
                    raise RuntimeError('M455 dense full destination reshape unexpectedly copied')
            else:
                for shard in range(4):
                    count=min(rows,max(0,valid-shard*rows));whole=count//8
                    if whole:
                        slice_=destination[:,shard*rows:shard*rows+whole*8]
                        view=slice_.reshape(token_count,whole,4,2)
                        expected=(destination.strides[0],8*destination.strides[1],2*destination.strides[1],destination.strides[1])
                        if view.ctypes.data!=slice_.ctypes.data or any(n>1 and actual!=wanted for n,actual,wanted in zip(view.shape,view.strides,expected)):
                            raise RuntimeError('M455 dense destination reshape unexpectedly copied')
            plan.append((source,destination,rows,valid));cursor+=size
        if cursor!=len(raw) or not plan:raise RuntimeError('M455 dense output cursor mismatch')
        finite=True
        for source,destination,rows,valid in plan:
            value=self.fn(source.ctypes.data,source.nbytes,destination.ctypes.data,*destination.strides,rows,valid,token_count,output_scale_shift)
            if value<0:raise RuntimeError('Native descriptor rejected validated plan')
            finite=bool(value) and finite
        return finite
