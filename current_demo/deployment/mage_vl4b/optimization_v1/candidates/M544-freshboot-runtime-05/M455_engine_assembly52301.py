"""Connect the original M243 loader to the separately guarded full M238 ctor.

Keep strong references before every constructor. The original loader's exception
path may request board.close(); it must never release the outer owner's buffers.
"""
from pathlib import Path
class DeferredOwnerClose(RuntimeError):pass
class EngineAssembly:
    def __init__(self,*,engine_class,language_module,vision_module,constructor,candidate_bit,expected_original_bit,admit,result):
        if not callable(admit):raise ValueError('Actual pre-load admission required')
        self.engine_class=engine_class;self.language_module=language_module;self.vision_module=vision_module;self.constructor=constructor
        self.candidate_bit=Path(candidate_bit);self.expected_original_bit=Path(expected_original_bit);self.admit=admit;self.result=result
        self.engine=None;self.strong=[];self.patches=[];self.called=False;self.returned=False;self.board_returned=False;self.closed=False
    def patch(self,obj,name,replacement):
        self.patches.append((obj,name,name in vars(obj),vars(obj).get(name)));setattr(obj,name,replacement)
    def load(self,config):
        if self.called or self.closed or self.constructor.runtime is not None:raise RuntimeError('Fresh full-engine assembly only')
        self.admit();self.called=True
        vision_class=self.vision_module.M222PSVisionRuntime;language_class=self.language_module.M241VideoLanguageModel
        if vision_class.__new__ is not object.__new__ or language_class.__new__ is not object.__new__:raise RuntimeError('Original ordinary constructor identity required')
        def board_factory(*args,**kwargs):
            if len(args)!=5 or kwargs!={'weight_mode':'staged-low-cma'} or Path(args[0]).resolve()!=self.expected_original_bit.resolve() or self.board_returned:
                raise RuntimeError('Original exact five-argument M238 load required')
            board=self.constructor.construct(self.candidate_bit,*args[1:]);self.strong.append(board);self.board_returned=True
            def defer_close():
                self.result.setdefault('original_loader_close_requests',[]).append(dict(deferred=True,hardware_release_called=False))
                raise DeferredOwnerClose('Original loader cleanup deferred to proven outer owner; retain all objects')
            self.patch(board,'close',defer_close);return board
        def retained_factory(cls,label):
            def construct(*args,**kwargs):
                obj=cls.__new__(cls);self.strong.append(obj)
                self.result.setdefault('engine_constructor_boundaries',[]).append(dict(kind=label,entered=True,returned=False))
                row=self.result['engine_constructor_boundaries'][-1]
                cls.__init__(obj,*args,**kwargs);row['returned']=True;return obj
            return construct
        self.patch(self.language_module,'M238PrefillRuntime',board_factory)
        self.patch(self.vision_module,'M222PSVisionRuntime',retained_factory(vision_class,'original_M273_vision'))
        self.patch(self.language_module,'M241VideoLanguageModel',retained_factory(language_class,'original_M241_language'))
        self.engine=self.engine_class(config);self.strong.append(self.engine)
        self.engine.load()
        if not self.board_returned or self.engine.board is not self.constructor.runtime or type(self.engine.vision)is not vision_class or type(self.engine.language)is not language_class or self.engine.language.runtime is not self.engine.board or self.engine.tokenizer is None:
            raise RuntimeError('Actual complete engine object closure differs')
        if self.engine.board.host_calls or self.engine.board.logical_calls:raise RuntimeError('Original full engine load submitted unexpected work')
        self.returned=True;self.result['original_complete_engine_load_returned']=True;return self.engine
    def restore_bindings(self,check_safe):
        if self.closed or not self.board_returned or not self.constructor.returned or not callable(check_safe):raise RuntimeError('Partial or unproven board constructor: retain patches')
        check_safe()
        for obj,name,owned,value in reversed(self.patches):
            if owned:setattr(obj,name,value)
            else:delattr(obj,name)
        if not all((name in vars(obj))==owned and (not owned or vars(obj)[name] is value) for obj,name,owned,value in self.patches):raise RuntimeError('Original loader binding restoration differs')
        self.patches=[];self.closed=True
