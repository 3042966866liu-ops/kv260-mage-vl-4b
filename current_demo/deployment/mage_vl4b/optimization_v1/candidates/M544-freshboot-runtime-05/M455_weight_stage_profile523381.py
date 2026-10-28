"""Observe only the original synchronous weight-window copy; no device API changes."""
import ast, contextlib, copy, hashlib, inspect, textwrap, threading, time

class WeightStageProfile:
    def __init__(self, expected_source_sha256, clock=time.perf_counter_ns, limit=1024):
        self.expected_source_sha256=expected_source_sha256
        self.clock,self.limit=clock,limit
        self.rows=[];self.active=False;self.current=None;self.original=None
        self.owner=threading.get_ident()
    @contextlib.contextmanager
    def part(self, name):
        assert self.current is not None and threading.get_ident()==self.owner
        began=self.clock()
        try:yield
        finally:
            self.current[name+'_ns']+=self.clock()-began
            self.current[name+'_calls']+=1
    def install(self, base):
        assert self.original is None
        self.namespace=base.M120BoardRuntime._stage.__globals__
        original=self.namespace['copy_window_to_buffer']
        source=textwrap.dedent(inspect.getsource(original))
        digest=hashlib.sha256(source.encode()).hexdigest()
        assert digest==self.expected_source_sha256 and not original.__code__.co_freevars
        before=ast.parse(source);hits=[]
        class Insert(ast.NodeTransformer):
            def visit(self, node):
                stage=None
                if isinstance(node,ast.Assign):
                    if any(isinstance(t,ast.Name) and t.id=='block' for t in node.targets):stage='read'
                    if any(isinstance(t,ast.Subscript) and isinstance(t.value,ast.Name) and t.value.id=='buffer' for t in node.targets):stage='copy'
                if isinstance(node,ast.Expr) and isinstance(node.value,ast.Call) and isinstance(node.value.func,ast.Attribute) and node.value.func.attr=='sync_to_device':stage='sync'
                node=super().visit(node)
                if stage is None:return node
                hits.append(stage)
                call=ast.Call(ast.Attribute(ast.Name('_weight_profile',ast.Load()),'part',ast.Load()),[ast.Constant(stage)],[])
                return ast.copy_location(ast.With([ast.withitem(call,None)],[node]),node)
        after=Insert().visit(copy.deepcopy(before))
        class Strip(ast.NodeTransformer):
            def visit_With(self,node):
                c=node.items[0].context_expr
                if isinstance(c,ast.Call) and isinstance(c.func,ast.Attribute) and isinstance(c.func.value,ast.Name) and c.func.value.id=='_weight_profile':
                    return [self.visit(n) for n in node.body]
                return self.generic_visit(node)
        assert sorted(hits)==['copy','read','sync'] and ast.dump(Strip().visit(copy.deepcopy(after)))==ast.dump(before)
        space=dict(original.__globals__);space['_weight_profile']=self
        exec(compile(ast.fix_missing_locations(after),'<M455_weight_stage_profile381>','exec'),space)
        observed=space[original.__name__]
        def wrapper(path,offset,size,buffer):
            if not self.active:return original(path,offset,size,buffer)
            assert threading.get_ident()==self.owner and self.current is None and len(self.rows)<self.limit
            row=dict(path=str(path),offset=offset,effective_bytes=size,buffer_capacity_bytes=int(buffer.nbytes),
                     read_ns=0,copy_ns=0,sync_ns=0,read_calls=0,copy_calls=0,sync_calls=0,ok=False)
            assert 0<size<=row['buffer_capacity_bytes']
            self.current=row;began=self.clock()
            try:
                result=observed(path,offset,size,buffer);row['ok']=True;return result
            finally:
                row['total_ns']=self.clock()-began
                row['open_seek_close_and_observer_ns']=row['total_ns']-row['read_ns']-row['copy_ns']-row['sync_ns']
                self.rows.append(row);self.current=None
        self.original,self.wrapper=original,wrapper
        self.namespace['copy_window_to_buffer']=wrapper
        self.proof=dict(original_source_sha256=digest,stripped_AST_equals_original=True,inserted_statements=hits,
                        no_new_device_API=True,no_sync_length_or_buffer_change=True)
    def begin(self):
        assert self.original is not None and not self.active and self.current is None
        self.rows=[];self.active=True
    def end(self):
        assert self.active and self.current is None;self.active=False
        assert self.rows and all(r['ok'] and r['open_seek_close_and_observer_ns']>=0 for r in self.rows)
        ns=('read_ns','copy_ns','sync_ns','total_ns','open_seek_close_and_observer_ns')
        summary={k[:-3]+'_s':sum(r[k] for r in self.rows)/1e9 for k in ns}
        summary.update(windows=len(self.rows),effective_bytes=sum(r['effective_bytes'] for r in self.rows),
                       whole_buffer_sync_capacity_bytes=sum(r['buffer_capacity_bytes'] for r in self.rows),
                       source_categories={})
        for r in self.rows:
            category='tmpfs_cropped' if r['path'].startswith('/dev/shm/') else 'original_storage'
            d=summary['source_categories'].setdefault(category,dict(windows=0,effective_bytes=0,read_s=0.,copy_s=0.,sync_s=0.))
            d['windows']+=1;d['effective_bytes']+=r['effective_bytes']
            for k in ('read','copy','sync'):d[k+'_s']+=r[k+'_ns']/1e9
        return dict(proof=self.proof,summary=summary,windows=self.rows)
    def restore(self):
        assert not self.active and self.current is None
        if self.original is not None:
            assert self.namespace['copy_window_to_buffer'] is self.wrapper
            self.namespace['copy_window_to_buffer']=self.original
            assert self.namespace['copy_window_to_buffer'] is self.original
            self.original=None
