"""Two bounded conservative-adaptation probes; inherited 18D slots stay intact."""
from dynamic import *

class AdaptNormalizer(FixedNormalizer):
    def normalize(self,x):
        y=super().normalize(x)
        mode=self.state.get('adaptation','original')
        if mode=='original':return y
        y=y.clone()
        if mode=='shrink':
            y[...,18:26]*=.5
        elif mode=='headon_guard':
            # All operands are own state and the legal observed/cached relative
            # velocity. Invalid slots were already masked by the inherited norm.
            c,s=torch.cos(x[...,3]),torch.sin(x[...,3])
            bx=x[...,20]+x[...,4]
            by=x[...,21]+x[...,5]*torch.cos(x[...,2])
            vx,vy=c*bx-s*by,s*bx+c*by
            # In the retained task initial position is (0,0); goal is the fixed
            # mission axis, not current desired heading or a scenario category.
            gx,gy=x[...,12],x[...,13]
            cosine=(vx*gx+vy*gy)/(torch.sqrt(vx*vx+vy*vy).clamp_min(1e-6)*torch.sqrt(gx*gx+gy*gy).clamp_min(1e-6))
            suppress=(x[...,24]>0)&(cosine<-.7)
            y[...,18:26]*=(~suppress).unsqueeze(-1)
        else:raise ValueError(mode)
        return y
