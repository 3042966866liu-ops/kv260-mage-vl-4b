"""Transparent diagnostic wrappers. No asset reads, allocations or cache edits."""
from pathlib import Path

ROLES=('staged_weights_port_0','staged_weights_port_1','staged_weights_port_2','staged_weights_port_3','input_buffer','output_buffer','output_buffer_alt')

def observe_call(original, name, mark, events):
    def call(*args, **kwargs):
        # Never retain tensor/buffer arguments or results in diagnostic records.
        row=dict(name=name,first_path=str(args[0]) if args and isinstance(args[0],(str,Path)) else None)
        row['before']=mark(name+':before')
        try:
            value=original(*args,**kwargs)
        except BaseException as exc:
            row['exception']=type(exc).__name__+': '+str(exc)
            raise
        else:
            if isinstance(value,str) and len(value)==64 and all(c in '0123456789abcdef' for c in value):row['returned_sha256']=value
            return value
        finally:
            row['after']=mark(name+':after');events.append(row)
    return call

def tokenizer_proxy(original, wrapped):
    class Forward(type):
        def __getattr__(cls, name):return getattr(original,name)
        def __call__(cls,*a,**kw):return original(*a,**kw)
    class ObservedTokenizer(metaclass=Forward):
        from_file=staticmethod(wrapped)
    return ObservedTokenizer

def array_info(array):
    return dict(type=type(array).__name__,shape=[int(x) for x in array.shape],dtype=str(array.dtype),nbytes=int(array.nbytes),owns_data=bool(array.flags.owndata),filename=str(getattr(array,'filename','')))

def retained_inventory(engine,runtime,allocations):
    actual=list(runtime.staged_buffers)+[runtime.input_buffer,runtime.output_buffer,runtime.output_buffer_alt]
    if len(actual)!=7 or len(allocations)!=7 or any(a is not b for a,b in zip(actual,allocations)):
        raise RuntimeError('Actual original buffer ownership/order differs')
    language=engine.language
    return dict(buffers=[dict(role=role,python_id=id(buffer),**array_info(buffer)) for role,buffer in zip(ROLES,actual)],
        embedding=array_info(language.embedding),norms={name:array_info(value) for name,value in language.norms.items()},
        norm_archive_path=str(language._norm_archive.zip.filename),
        classes={name:type(getattr(engine,name)).__module__+'.'+type(getattr(engine,name)).__name__ for name in ('board','vision','language','tokenizer')},
        note='Payload sizes/identities only; mmap virtual size is not resident memory, and this inventory does not prove system CMA page ownership.')

def mapping_inventory(path=Path('/proc/self/smaps')):
    rows=[];current=None
    for line in path.read_text(encoding='utf-8').splitlines():
        parts=line.split()
        if parts and '-' in parts[0] and len(parts)>=5:
            if current:rows.append(current)
            current=dict(mapping=' '.join(parts[5:]) or '[anonymous]',virtual_address_range=parts[0],permissions=parts[1],bytes={})
        elif current and parts and parts[0].rstrip(':') in ('Size','Rss','Pss','Anonymous','Private_Dirty','Shared_Clean','Private_Clean'):
            current['bytes'][parts[0].rstrip(':')]=int(parts[1])*1024
    if current:rows.append(current)
    groups={}
    for row in rows:
        name=row['mapping'];group=groups.setdefault(name,dict(mapping=name,vma_count=0,bytes={}))
        group['vma_count']+=1
        for k,v in row['bytes'].items():group['bytes'][k]=group['bytes'].get(k,0)+v
    return dict(scope='Process VMAs only; un-mapped file cache and CMA page ownership are not measured',mappings=sorted(groups.values(),key=lambda x:x['bytes'].get('Rss',0),reverse=True))
