#AUTOGENERATED! DO NOT EDIT! File to edit: dev/09a_rect_augment.ipynb (unless otherwise specified).

__all__ = ['SortARSampler', 'ResizeCollate']

from ..imports import *
from ..test import *
from ..core import *
from ..data.transform import *
from ..data.pipeline import *
from ..data.source import *
from ..data.core import *
from .core import *
from .augment import *
from ..data.external import *
from ..notebook.showdoc import show_doc

class SortARSampler(BatchSampler):
    def __init__(self, ds, items=None, bs=32, grp_sz=1000, shuffle=False, drop_last=False):
        if not items: items=ds.items
        self.shapes = [Image.open(it).shape for it in items]
        self.sizes = [h*w for h,w in self.shapes]
        self.ars = [h/w for h,w in self.shapes]
        self.ds,self.grp_sz,self.bs,self.shuffle,self.drop_last = ds,round_multiple(grp_sz,bs),bs,shuffle,drop_last
        self.grp_sz = round_multiple(grp_sz,bs)

        # reverse argsort of sizes
        idxs = [i for i,o in sorted(enumerate(self.sizes), key=itemgetter(1), reverse=True)]
        # create approx equal sized groups no larger than `grp_sz`
        grps = [idxs[i:i+self.grp_sz] for i in range(0, len(idxs), self.grp_sz)]
        # sort within groups by aspect ratio
        self.grps = [sorted(g, key=lambda o:self.ars[o]) for g in grps]

    def __iter__(self):
        grps = self.grps
        if self.shuffle: grps = [shufflish(o) for o in grps]
        grps = [g[i:i+self.bs] for g in grps for i in range(0, len(g), self.bs)]
        if self.drop_last and len(grps[-1])!=self.bs: del(grps[-1])
        # Shuffle all but first (so can have largest first)
        if self.shuffle: grps = random.sample(grps[1:], len(grps)-1) + [grps[0]]
        return iter(grps)

    def __len__(self): return (len(self.ds) if self.drop_last else (len(self.ds)+self.bs-1)) // self.bs

from torch.utils.data.dataloader import default_collate

class ResizeCollate(TfmdCollate):
    def __init__(self, tfms=None, collate_fn=default_collate, sz=None, is_fixed_px=False, max_px=512*512, round_mult=None,
                rand_min_scale=None, rand_ratio_pct=None):
        super().__init__(tfms, default_collate)
        self.round_mult,self.is_fixed_px,self.max_px = round_mult,is_fixed_px,max_px
        self.is_rand = rand_min_scale or rand_ratio_pct
        if self.is_rand:
            self.inv_ratio = 1-ifnone(rand_ratio_pct, 0.10)
            self.resize = RandomResizedCrop(1, min_scale=ifnone(rand_min_scale, 0.25), as_item=False)
        else: self.resize = Resize(1, as_item=False)
        self.sz = None if sz is None else (sz, sz) if isinstance(sz, int) else sz

    def __call__(self, samples):
        if self.sz is None:
            if self.is_fixed_px: px = self.max_px
            else: px = min(self.max_px, max(L(o[0].shape[0]*o[0].shape[1] for o in samples)))
            ar = np.median(L(o[0].aspect for o in samples))
            sz = int(math.sqrt(px*ar)),int(math.sqrt(px/ar))
        else: sz,ar = self.sz,self.sz[1]/self.sz[0]
        if self.round_mult is not None: sz = round_multiple(sz, self.round_mult, round_down=True)
        if self.is_rand: self.resize.ratio = (ar*self.inv_ratio, ar/self.inv_ratio)
        return super().__call__(self.resize(o,size=sz) for o in samples)