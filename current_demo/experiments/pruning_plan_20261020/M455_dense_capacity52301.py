"""Explicit constructor capacity adapter; never changes runtime or safety flags.

The dense M120 constructor asks for half-sized output. Its returned buffer has
the original larger shape, which the unmodified M236 constructor then uses for
the seventh alternate output. All allocation/release stays in the real ledger.
"""
SHAPES=(6963200,)*4+(389152,2621440,2621440)

class DenseOriginalCapacity:
    def __init__(self,ledger,dtype,result):
        self.ledger=ledger;self.dtype=dtype;self.result=result
        result['dense_constructor_capacity_requests']=[]
    def __call__(self,*args,**kwargs):
        index=len(self.ledger.buffers)
        if self.ledger.closed or self.ledger.sealed or self.ledger.allocating_unknown or index>=7:
            raise RuntimeError('Original allocation ledger sealed/unresolved')
        expected=SHAPES[index]//2 if index==5 else SHAPES[index]
        if args!=((expected,),) or set(kwargs)!={'dtype'} or kwargs['dtype'] is not self.dtype:
            raise RuntimeError('Exact original dense constructor request sequence differs')
        row=dict(index=index,requested_bytes=expected,reserved_bytes=SHAPES[index],
            output_capacity_only=index==5,allocated=False)
        self.result['dense_constructor_capacity_requests'].append(row)
        buffer=self.ledger.allocate((SHAPES[index],),dtype=self.dtype)
        row['allocated']=True
        return buffer
