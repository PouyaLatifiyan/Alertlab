"""Generate independent fixture outputs from the included Python reference."""
from pathlib import Path
import sys,json
import numpy as np

root=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(root/'research'/'bench'),str(root/'research'/'selection')]
import run
from decision import cp
r=np.random.default_rng(4821)
z=r.normal(size=(1,34))
ref=r.normal(size=(1,32))
outputs=run.scores(z,ref)
cases=[[0,12000,.05/864],[12000,12000,.05/864],[6413,12000,.05/864],[31,12000,.05/864],[3,10,.05],[9,10,.01]]
class FixedPhysicalDraws:
    def __init__(self, limit, load, latency, works):
        self.draws = iter([limit, load])
        self.latency = latency
        self.works = works
    def uniform(self, a, b, n):
        return np.full(n,next(self.draws))
    def integers(self, a, b, n):
        return np.full(n,self.latency)
    def random(self, n):
        return np.full(n,0.99 if self.works else 0.)

physical=[]
for name,tau,worked in [('moderate persistent',8,True),('moderate persistent',36,False),
                        ('brief pulse',27,True),('slow ramp',81,True),('transient drift',31,True)]:
    scenario=next(s for s in run.SCENARIOS if s.name==name)
    nu=26
    args=[nu,1.03,.94,4,worked,tau if tau<=run.T else None]
    hazard,miss,need,cross=run.physical(FixedPhysicalDraws(*args[1:5]),scenario,
        np.arange(1,run.T+1)[None,:]-nu,np.array([[[tau]]]),np.array([nu]))
    physical.append(dict(name=name,args=args,hazard=bool(hazard[0,0,0]),
      opportunity=not bool(miss[0,0,0]) if need[0] else None,crossing=int(cross[0]) if need[0] else None))
(root/'scripts/python-reference.json').write_text(json.dumps(dict(input=z[0].tolist(),ref=ref[0].tolist(),physical=physical,
  scores={k:v[0].tolist() for k,v in zip(run.METHODS,outputs)},cp=[dict(args=c,expected=cp(*c)) for c in cases]),indent=2)+'\n')
