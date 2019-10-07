#AUTOGENERATED! DO NOT EDIT! File to edit: dev/01_core.ipynb (unless otherwise specified).

__all__ = ['defaults', 'FixSigMeta', 'PrePostInitMeta', 'NewChkMeta', 'BypassNewMeta', 'copy_func', 'patch_to', 'patch',
           'patch_property', 'use_kwargs', 'delegates', 'funcs_kwargs', 'method', 'add_docs', 'docs', 'custom_dir',
           'arg0', 'arg1', 'arg2', 'arg3', 'arg4', 'bind', 'GetAttr', 'delegate_attr', 'coll_repr', 'mask2idxs',
           'listable_types', 'CollBase', 'cycle', 'zip_cycle', 'is_indexer', 'L', 'camel2snake', 'display_df',
           'PrettyString']

#Cell
from .test import *
from .imports import *
from .notebook.showdoc import *

#Cell
defaults = SimpleNamespace()

#Cell
class FixSigMeta(type):
    "A metaclass that fixes the signature on classes that override __new__"
    def __new__(cls, name, bases, dict):
        res = super().__new__(cls, name, bases, dict)
        if res.__init__ is not object.__init__: res.__signature__ = inspect.signature(res.__init__)
        return res

#Cell
class PrePostInitMeta(FixSigMeta):
    "A metaclass that calls optional `__pre_init__` and `__post_init__` methods"
    def __call__(cls, *args, **kwargs):
        res = cls.__new__(cls)
        if type(res)==cls:
            if hasattr(res,'__pre_init__'): res.__pre_init__(*args,**kwargs)
            res.__init__(*args,**kwargs)
            if hasattr(res,'__post_init__'): res.__post_init__(*args,**kwargs)
        return res

#Cell
class NewChkMeta(FixSigMeta):
    "Metaclass to avoid recreating object passed to constructor"
    def __call__(cls, x=None, *args, **kwargs):
        if not args and not kwargs and x is not None and isinstance(x,cls):
            x._newchk = 1
            return x

        res = super().__call__(*((x,) + args), **kwargs)
        res._newchk = 0
        return res

#Cell
class BypassNewMeta(FixSigMeta):
    "Metaclass: casts `x` to this class if it's of type `cls._bypass_type`, initializing with `_new_meta` if available"
    def __call__(cls, x=None, *args, **kwargs):
        if hasattr(cls, '_new_meta'): x = cls._new_meta(x, *args, **kwargs)
        elif not isinstance(x,getattr(cls,'_bypass_type',object)) or len(args) or len(kwargs):
            x = super().__call__(*((x,)+args), **kwargs)
        if cls!=x.__class__: x.__class__ = cls
        return x

#Cell
def copy_func(f):
    "Copy a non-builtin function (NB `copy.copy` does not work for this)"
    if not isinstance(f,types.FunctionType): return copy(f)
    fn = types.FunctionType(f.__code__, f.__globals__, f.__name__, f.__defaults__, f.__closure__)
    fn.__dict__.update(f.__dict__)
    return fn

#Cell
def patch_to(cls, as_prop=False):
    "Decorator: add `f` to `cls`"
    if not isinstance(cls, (tuple,list)): cls=(cls,)
    def _inner(f):
        for c_ in cls:
            nf = copy_func(f)
            # `functools.update_wrapper` when passing patched function to `Pipeline`, so we do it manually
            for o in functools.WRAPPER_ASSIGNMENTS: setattr(nf, o, getattr(f,o))
            nf.__qualname__ = f"{c_.__name__}.{f.__name__}"
            setattr(c_, f.__name__, property(nf) if as_prop else nf)
        return f
    return _inner

#Cell
def patch(f):
    "Decorator: add `f` to the first parameter's class (based on f's type annotations)"
    cls = next(iter(f.__annotations__.values()))
    return patch_to(cls)(f)

#Cell
def patch_property(f):
    "Decorator: add `f` as a property to the first parameter's class (based on f's type annotations)"
    cls = next(iter(f.__annotations__.values()))
    return patch_to(cls, as_prop=True)(f)

#Cell
def _mk_param(n,d=None): return inspect.Parameter(n, inspect.Parameter.KEYWORD_ONLY, default=d)

#Cell
def use_kwargs(names, keep=False):
    "Decorator: replace `**kwargs` in signature with `names` params"
    def _f(f):
        sig = inspect.signature(f)
        sigd = dict(sig.parameters)
        k = sigd.pop('kwargs')
        s2 = {n:_mk_param(n) for n in names if n not in sigd}
        sigd.update(s2)
        if keep: sigd['kwargs'] = k
        f.__signature__ = sig.replace(parameters=sigd.values())
        return f
    return _f

#Cell
def delegates(to=None, keep=False):
    "Decorator: replace `**kwargs` in signature with params from `to`"
    def _f(f):
        if to is None: to_f,from_f = f.__base__.__init__,f.__init__
        else:          to_f,from_f = to,f
        from_f = getattr(from_f,'__func__',from_f)
        if hasattr(from_f,'__delwrap__'): return f
        sig = inspect.signature(from_f)
        sigd = dict(sig.parameters)
        k = sigd.pop('kwargs')
        s2 = {k:v for k,v in inspect.signature(to_f).parameters.items()
              if v.default != inspect.Parameter.empty and k not in sigd}
        sigd.update(s2)
        if keep: sigd['kwargs'] = k
        from_f.__signature__ = sig.replace(parameters=sigd.values())
        from_f.__delwrap__ = to_f
        return f
    return _f

#Cell
def funcs_kwargs(cls):
    "Replace methods in `self._methods` with those from `kwargs`"
    old_init = cls.__init__
    def _init(self, *args, **kwargs):
        for k in cls._methods:
            arg = kwargs.pop(k,None)
            if arg is not None:
                if isinstance(arg,types.MethodType): arg = types.MethodType(arg.__func__, self)
                setattr(self, k, arg)
        old_init(self, *args, **kwargs)
    functools.update_wrapper(_init, old_init)
    cls.__init__ = use_kwargs(cls._methods)(_init)
    return cls

#Cell
def method(f):
    "Mark `f` as a method"
    # `1` is a dummy instance since Py3 doesn't allow `None` any more
    return types.MethodType(f, 1)

#Cell
def add_docs(cls, cls_doc=None, **docs):
    "Copy values from `docs` to `cls` docstrings, and confirm all public methods are documented"
    if cls_doc is not None: cls.__doc__ = cls_doc
    for k,v in docs.items():
        f = getattr(cls,k)
        if hasattr(f,'__func__'): f = f.__func__ # required for class methods
        f.__doc__ = v
    # List of public callables without docstring
    nodoc = [c for n,c in vars(cls).items() if callable(c)
             and not n.startswith('_') and c.__doc__ is None]
    assert not nodoc, f"Missing docs: {nodoc}"
    assert cls.__doc__ is not None, f"Missing class docs: {cls}"

#Cell
def docs(cls):
    "Decorator version of `add_docs`, using `_docs` dict"
    add_docs(cls, **cls._docs)
    return cls

#Cell
def custom_dir(c, add:list):
    "Implement custom `__dir__`, adding `add` to `cls`"
    return dir(type(c)) + list(c.__dict__.keys()) + add

#Cell
class _Arg:
    def __init__(self,i): self.i = i
arg0 = _Arg(0)
arg1 = _Arg(1)
arg2 = _Arg(2)
arg3 = _Arg(3)
arg4 = _Arg(4)

#Cell
# _all_ = ['arg0', 'arg1', 'arg2', 'arg3', 'arg4']

#Cell
class bind:
    "Same as `partial`, except you can use `arg0` `arg1` etc param placeholders"
    def __init__(self, fn, *pargs, **pkwargs):
        self.fn,self.pargs,self.pkwargs = fn,pargs,pkwargs
        self.maxi = max((x.i for x in pargs if isinstance(x, _Arg)), default=-1)

    def __call__(self, *args, **kwargs):
        args = list(args)
        kwargs = {**self.pkwargs,**kwargs}
        for k,v in kwargs.items():
            if isinstance(v,_Arg): kwargs[k] = args.pop(v.i)
        fargs = [args[x.i] if isinstance(x, _Arg) else x for x in self.pargs] + args[self.maxi+1:]
        return self.fn(*fargs, **kwargs)

#Cell
class GetAttr:
    "Inherit from this to have all attr accesses in `self._xtra` passed down to `self.default`"
    _default='default'
    @property
    def _xtra(self): return [o for o in dir(getattr(self,self._default)) if not o.startswith('_')]
    def __getattr__(self,k):
        if k not in ('_xtra',self._default) and (self._xtra is None or k in self._xtra): return getattr(getattr(self,self._default), k)
        raise AttributeError(k)
    def __dir__(self): return custom_dir(self, self._xtra)
    def __setstate__(self,data): self.__dict__.update(data)

#Cell
def delegate_attr(self, k, to):
    "Use in `__getattr__` to delegate to attr `to` without inheriting from `GetAttr`"
    if k.startswith('_') or k==to: raise AttributeError(k)
    try: return getattr(getattr(self,to), k)
    except AttributeError: raise AttributeError(k) from None

#Cell
def _is_array(x): return hasattr(x,'__array__') or hasattr(x,'iloc')

def _listify(o):
    if o is None: return []
    if isinstance(o, list): return o
    if isinstance(o, str) or _is_array(o): return [o]
    if is_iter(o): return list(o)
    return [o]

#Cell
def coll_repr(c, max_n=10):
    "String repr of up to `max_n` items of (possibly lazy) collection `c`"
    return f'(#{len(c)}) [' + ','.join(itertools.islice(map(str,c), max_n)) + (
        '...' if len(c)>10 else '') + ']'

#Cell
def mask2idxs(mask):
    "Convert bool mask or index list to index `L`"
    if isinstance(mask,slice): return mask
    mask = list(mask)
    if len(mask)==0: return []
    if isinstance(mask[0],(bool,NoneType)): return [i for i,m in enumerate(mask) if m]
    return [int(i) for i in mask]

#Cell
listable_types = typing.Collection,Generator,map,filter,zip

#Cell
class CollBase:
    "Base class for composing a list of `items`"
    def __init__(self, items): self.items = items
    def __len__(self): return len(self.items)
    def __getitem__(self, k): return self.items[k]
    def __setitem__(self, k, v): self.items[list(k) if isinstance(k,CollBase) else k] = v
    def __delitem__(self, i): del(self.items[i])
    def __repr__(self): return self.items.__repr__()
    def __iter__(self): return self.items.__iter__()

#Cell
def cycle(o):
    "Like `itertools.cycle` except creates list of `None`s if `o` is empty"
    o = _listify(o)
    return itertools.cycle(o) if o is not None and len(o) > 0 else itertools.cycle([None])

#Cell
def zip_cycle(x, *args):
    "Like `itertools.zip_longest` but `cycle`s through elements of all but first argument"
    return zip(x, *map(cycle,args))

#Cell
def is_indexer(idx):
    "Test whether `idx` will index a single item in a list"
    return isinstance(idx,int) or not getattr(idx,'ndim',1)

#Cell
class L(CollBase, GetAttr, metaclass=NewChkMeta):
    "Behaves like a list of `items` but can also index with list of indices or masks"
    _default='items'
    def __init__(self, items=None, *rest, use_list=False, match=None):
        if rest: items = (items,)+rest
        if items is None: items = []
        if (use_list is not None) or not _is_array(items):
            items = list(items) if use_list else _listify(items)
        if match is not None:
            if is_coll(match): match = len(match)
            if len(items)==1: items = items*match
            else: assert len(items)==match, 'Match length mismatch'
        super().__init__(items)

    def _new(self, items, *args, **kwargs): return type(self)(items, *args, use_list=None, **kwargs)
    def __getitem__(self, idx): return self._get(idx) if is_indexer(idx) else L(self._get(idx), use_list=None)

    def _get(self, i):
        if is_indexer(i) or isinstance(i,slice): return getattr(self.items,'iloc',self.items)[i]
        i = mask2idxs(i)
        return (self.items.iloc[list(i)] if hasattr(self.items,'iloc')
                else self.items.__array__()[(i,)] if hasattr(self.items,'__array__')
                else [self.items[i_] for i_ in i])

    def __setitem__(self, idx, o):
        "Set `idx` (can be list of indices, or mask, or int) items to `o` (which is broadcast if not iterable)"
        idx = idx if isinstance(idx,L) else _listify(idx)
        if not is_iter(o): o = [o]*len(idx)
        for i,o_ in zip(idx,o): self.items[i] = o_

    def __iter__(self): return iter(self.items.itertuples() if hasattr(self.items,'iloc') else self.items)
    def __contains__(self,b): return b in self.items
    def __invert__(self): return self._new(not i for i in self)
    def __eq__(self,b): return False if isinstance(b, (str,dict,set)) else all_equal(b,self)
    def __repr__(self): return repr(self.items) if _is_array(self.items) else coll_repr(self)
    def __mul__ (a,b): return a._new(a.items*b)
    def __add__ (a,b): return a._new(a.items+_listify(b))
    def __radd__(a,b): return a._new(b)+a
    def __addi__(a,b):
        a.items += list(b)
        return a

    def sorted(self, key=None, reverse=False):
        if isinstance(key,str):   k=lambda o:getattr(o,key,0)
        elif isinstance(key,int): k=itemgetter(key)
        else: k=key
        return self._new(sorted(self.items, key=k, reverse=reverse))

    @classmethod
    def split(cls, s, sep=None, maxsplit=-1): return cls(s.split(sep,maxsplit))

    @classmethod
    def range(cls, a, b=None, step=None):
        if is_coll(a): a = len(a)
        return cls(range(a,b,step) if step is not None else range(a,b) if b is not None else range(a))

    def map(self, f, *args, **kwargs):
        g = (bind(f,*args,**kwargs) if callable(f)
             else f.format if isinstance(f,str)
             else f.__getitem__)
        return self._new(map(g, self))

    def unique(self): return L(dict.fromkeys(self).keys())
    def enumerate(self): return L(enumerate(self))
    def val2idx(self): return {v:k for k,v in self.enumerate()}
    def itemgot(self, idx): return self.map(itemgetter(idx))
    def attrgot(self, k, default=None): return self.map(lambda o:getattr(o,k,default))
    def cycle(self): return cycle(self)
    def filter(self, f, *args, **kwargs): return self._new(filter(partial(f,*args,**kwargs), self))
    def map_dict(self, f=noop, *args, **kwargs): return {k:f(k, *args,**kwargs) for k in self}
    def starmap(self, f, *args, **kwargs): return self._new(itertools.starmap(partial(f,*args,**kwargs), self))
    def zip(self, cycled=False): return self._new((zip_cycle if cycled else zip)(*self))
    def zipwith(self, *rest, cycled=False): return self._new([self, *rest]).zip(cycled=cycled)
    def map_zip(self, f, *args, cycled=False, **kwargs): return self.zip(cycled=cycled).starmap(f, *args, **kwargs)
    def map_zipwith(self, f, *rest, cycled=False, **kwargs): return self.zipwith(*rest, cycled=cycled).starmap(f, **kwargs)
    def concat(self): return self._new(itertools.chain.from_iterable(self.map(L)))
    def shuffle(self):
        it = copy(self.items)
        random.shuffle(it)
        return self._new(it)

#Cell
add_docs(L,
         __getitem__="Retrieve `idx` (can be list of indices, or mask, or int) items",
         range="Same as builtin `range`, but returns an `L`. Can pass a collection for `a`, to use `len(a)`",
         split="Same as builtin `str.split`, but returns an `L`",
         sorted="New `L` sorted by `key`. If key is str then use `attrgetter`. If key is int then use `itemgetter`",
         unique="Unique items, in stable order",
         val2idx="Dict from value to index",
         filter="Create new `L` filtered by predicate `f`, passing `args` and `kwargs` to `f`",
         map="Create new `L` with `f` applied to all `items`, passing `args` and `kwargs` to `f`",
         map_dict="Like `map`, but creates a dict from `items` to function results",
         starmap="Like `map`, but use `itertools.starmap`",
         itemgot="Create new `L` with item `idx` of all `items`",
         attrgot="Create new `L` with attr `k` of all `items`",
         cycle="Same as `itertools.cycle`",
         enumerate="Same as `enumerate`",
         zip="Create new `L` with `zip(*items)`",
         zipwith="Create new `L` with `self` zip with each of `*rest`",
         map_zip="Combine `zip` and `starmap`",
         map_zipwith="Combine `zipwith` and `starmap`",
         concat="Concatenate all elements of list",
         shuffle="Same as `random.shuffle`, but not inplace")

#Comes from 01a_utils.ipynb, cell
_camel_re1 = re.compile('(.)([A-Z][a-z]+)')
_camel_re2 = re.compile('([a-z0-9])([A-Z])')

def camel2snake(name):
    s1   = re.sub(_camel_re1, r'\1_\2', name)
    return re.sub(_camel_re2, r'\1_\2', s1).lower()

test_eq(camel2snake('ClassAreCamel'), 'class_are_camel')

#Comes from 01a_utils.ipynb, cell
def display_df(df):
    "Display `df` in a notebook or defaults to print"
    try: from IPython.display import display, HTML
    except: return print(df)
    display(HTML(df.to_html()))

#Comes from 15_callback_hook.ipynb, cell
class PrettyString(str):
    "Little hack to get strings to show properly in Jupyter."
    def __repr__(self): return self