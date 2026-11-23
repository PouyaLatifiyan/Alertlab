"""Matched comparison on the released Gaussian missions. Run from any directory."""
from itertools import product
from pathlib import Path
import csv
import sys
import numpy as np
from scipy.optimize import linprog
from latency_transport import binomial_box
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'selection'))
from coupled import feasible_rival_regret
NAMES=['Restart','CUSUM','GLR']
data=np.load(HERE/'margin_first_alerts.npz')
tau=data['tau'][:,[list(data['methods']).index(n.lower()) for n in NAMES]]
slack=np.where((tau>100)&(tau<=300),310-tau,-np.inf)
levels=(slack[:,:,None]>=np.array([10,100,200])).sum(axis=2)
types=np.array(list(product(range(4),repeat=3)))
counts=np.bincount(np.ravel_multi_index(levels.T,(4,4,4)),minlength=64)
low,high=binomial_box(counts,.05)
miss=(types.T[:,:,None]<np.arange(1,4)).astype(float)
cells=miss.reshape(3,-1)
rows=np.kron(np.eye(len(types)),np.ones((1,3)))
cols=np.tile(np.eye(3),len(types))
q=np.array([.5,.3,.2])
ineq=np.vstack((rows,-rows))
rhs=np.r_[high,-low]
poly=(ineq,rhs,cols,q)

def maxcost(c,extra=None):
    a,b=ineq,rhs
    if extra is not None:
        row,cap=extra
        a=np.vstack([a,row]); b=np.r_[b,cap]
    sol=linprog(-c,A_ub=a,b_ub=b,A_eq=cols,b_eq=q,bounds=(0,None))
    if sol.status==2:return None
    if not sol.success:raise ValueError(sol.message)
    return -sol.fun

def run():
    results=[]
    for contract,weights in [('one slot per handoff',[1,1,1]),('duration-weighted handoff',[.05,.5,1])]:
        # Downstream reservation charged only on handoffs completed by deadline.
        resource=((1-miss)*weights).reshape(3,-1)
        bounds=[(-maxcost(-u),maxcost(u)) for u in resource]
        for cap in np.linspace(0,1,21):
            outer=[j for j,(l,h) in enumerate(bounds) if l<=cap+1e-10]
            inner=[i for i,(l,h) in enumerate(bounds) if h<=cap+1e-10]
            exact=feasible_rival_regret(cells,resource[:,None,:],[cap],poly)
            relaxed={i:max(maxcost(cells[i]-cells[j]) for j in outer) for i in inner}
            for i in inner:
                # Independently solve general statewise regret by partitioning the
                # comparator's argmin: any better feasible rival already appears in the max.
                rival_bounds=[maxcost(cells[i]-cells[j],(resource[j],cap)) for j in outer]
                np.testing.assert_allclose(exact[i],max(x for x in rival_bounds if x is not None),atol=1e-8)
                assert exact[i] <= relaxed[i]+1e-8
            for i,name in enumerate(NAMES):
                results.append([contract,cap,name,i in inner,i in outer,relaxed.get(i),exact[i],
                    None if i not in inner else relaxed[i]-exact[i],
                    bool(inner and i==min(inner,key=relaxed.get)),
                    bool(inner and i==min(inner,key=lambda m:exact[m]))])
    with (HERE/'matched_regret.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['contract','budget','monitor','robust_feasible','possible','separate_bound','same_law_bound','tightening','separate_choice','same_law_choice']);w.writerows(results)
    for contract in sorted(set(r[0] for r in results)):
        sub=[r for r in results if r[0]==contract]
        print(contract,[(round(r[1],2),r[2],round(r[5],5),round(r[6],5)) for r in sub if r[-1]])
        print('max tightening',max((r[7],r[1],r[2]) for r in sub if r[7] is not None))
if __name__=='__main__':run()
