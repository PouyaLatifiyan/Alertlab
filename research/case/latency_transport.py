"""Sharp opportunity-risk contrasts for an exogenous common response duration.

The finite population LP uses joint paired warning margins. CP intervals on every
type (including unseen types) give an outer confidence region for the population.
"""
from pathlib import Path
from itertools import product, combinations
import csv
import numpy as np
from scipy.optimize import linprog
from scipy.stats import beta
import matplotlib.pyplot as plt
HERE = Path(__file__).resolve().parent

def binomial_box(counts, confidence_failure):
    n = counts.sum()
    tail = confidence_failure/(2*len(counts))
    low = np.zeros(len(counts)); high = np.ones(len(counts))
    has = counts>0; nonfull = counts<n
    low[has] = beta.ppf(tail,counts[has],n-counts[has]+1)
    high[nonfull] = beta.ppf(1-tail,counts[nonfull]+1,n-counts[nonfull])
    return low,high

def transport_interval(payoff,lo,hi,qlo,qhi):
    """Each row is a warning type, each column a possible latency."""
    m,k=payoff.shape
    rows=np.kron(np.eye(m),np.ones((1,k)))
    cols=np.tile(np.eye(k),m)
    A=np.vstack((rows,-rows,cols,-cols))
    b=np.r_[hi,-np.asarray(lo),qhi,-np.asarray(qlo)]
    def optimize(sign):
        res=linprog(sign*payoff.ravel(),A_ub=A,b_ub=b,A_eq=np.ones((1,m*k)),b_eq=[1.0],bounds=(0,None),method='highs')
        if not res.success: raise ValueError(res.message)
        return float(sign*res.fun)
    return optimize(1), optimize(-1)

def main():
    data=np.load(HERE/'margin_first_alerts.npz')
    names=['restart','cusum','glr']
    tau=data['tau'][:,[list(data['methods']).index(k) for k in names]]
    durations=np.array([10,100,200])
    eligible=(tau>100)&(tau<=300)
    slack=np.where(eligible,310-tau,-np.inf)
    categories=(slack[:,:,None]>=durations).sum(axis=2)
    types=np.array(list(product(range(4),repeat=3)))
    labels=np.ravel_multi_index(categories.T,(4,4,4))
    counts=np.bincount(labels,minlength=len(types))
    fractions=counts/counts.sum()
    lo,hi=binomial_box(counts,.05)
    loss=(types[:,:,None]<=np.arange(3)).astype(float)
    targets=[(n,loss[:,i,:]) for i,n in enumerate(names)]
    targets.extend((a+' minus '+b,loss[:,i,:]-loss[:,j,:]) for (i,a),(j,b) in combinations(enumerate(names),2))
    q=np.array([.5,.3,.2]); rows=[]
    for label,c in targets:
        ind=np.sum(fractions[:,None]*c*q)
        plug=transport_interval(c,fractions,fractions,q,q)
        conf=transport_interval(c,lo,hi,q,q)
        robust=transport_interval(c,lo,hi,[.4,.2,.1],[.6,.4,.3])
        rows.append([label,ind,*plug,*conf,*robust])
    with (HERE/'transport.csv').open('w',newline='') as fp:
        w=csv.writer(fp);w.writerow(['target','independent_latency_plugin','lp_lower','lp_upper','sim95_lower','sim95_upper','ambiguous_latency_sim95_lower','ambiguous_latency_sim95_upper']);w.writerows(rows)
    with (HERE/'types.csv').open('w',newline='') as fp:
        w=csv.writer(fp);w.writerow([*names,'count','low','high']);w.writerows([*t,k,l,u] for t,k,l,u in zip(types,counts,lo,hi))
    fig,ax=plt.subplots(figsize=(7.2,2.8),layout='constrained')
    for i,(label,ind,_,__,l,u,lr,ur) in enumerate(rows[3:]):
        ax.plot([lr,ur],[i,i],color='#a8b9c8',lw=8,solid_capstyle='butt',label='Latency shares uncertain' if i==0 else None)
        ax.plot([l,u],[i,i],color='#12645c',lw=3,label='Latency shares fixed' if i==0 else None)
        ax.plot(ind,i,'o',color='#ad5816',label='Independent latency (estimate)' if i==0 else None)
    ax.axvline(0,ls=':',color='black')
    ax.set_yticks(range(3),[r[0].upper().replace(' MINUS ',' – ') for r in rows[3:]])
    ax.set_xlabel('Difference in probability of insufficient response time')
    ax.legend(fontsize=8,ncol=1,loc='upper right',bbox_to_anchor=(1.0,1.0))
    ax.set_ylim(-.5,3.2)
    fig.savefig(HERE/'transport.pdf')
    print(*rows,sep='\n')

def check():
    # Two equiprobable types. Coupling extremes must coincide with the two permutations.
    cost=np.array([[0.,1.],[-1.,0.]])
    q=np.array([.5,.5])
    both=transport_interval(cost,q,q,q,q)
    assert np.allclose(both,[0,0])
    cost=np.array([[0.,1.],[1.,0.]])
    assert np.allclose(transport_interval(cost,q,q,q,q),[0,1])
    # Shared latency makes two identical policies indistinguishable under every coupling.
    assert np.allclose(transport_interval(np.zeros((2,2)),q,q,q,q),[0,0])

if __name__=='__main__':
    check()
    main()
