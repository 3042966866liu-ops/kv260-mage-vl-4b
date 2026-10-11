"""Diagnostic-only reuse of the actual pre-Overlay validated tokenizer."""
import os
from pathlib import Path

def identity(path):
    path=Path(path).resolve(strict=True)
    before=path.lstat()
    with path.open('rb') as stream:
        actual=os.fstat(stream.fileno())
    keys=('st_dev','st_ino','st_mode','st_size','st_mtime_ns','st_ctime_ns','st_nlink')
    a=tuple(getattr(before,k) for k in keys);b=tuple(getattr(actual,k) for k in keys)
    if a!=b:raise RuntimeError('Tokenizer pathname/open identity differs')
    return (str(path),a)

class ValidatedTokenizerOnce:
    def __init__(self,parser):
        self.parser=parser;self.cached=None;self.file_identity=None
        self.parse_count=0;self.reuse_count=0;self.object_identity=None
    def from_file(self,path):
        current=identity(path)
        if self.parse_count==0:
            value=self.parser(path)
            if identity(path)!=current:raise RuntimeError('Tokenizer changed during parse')
            self.cached=value;self.file_identity=current;self.object_identity=id(value)
            self.parse_count=1
            return value
        if current!=self.file_identity:raise RuntimeError('Tokenizer changed before original loader reuse')
        if self.reuse_count or self.cached is None:raise RuntimeError('Unexpected additional tokenizer parse')
        value=self.cached;self.cached=None;self.reuse_count=1
        return value
