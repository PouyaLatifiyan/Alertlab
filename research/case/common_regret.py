"""Reproduce the two-type feasibility witness and sample-size sensitivity."""
import csv
from pathlib import Path
from itertools import product
import numpy as np
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"selection"))
from coupled import feasible_rival_regret
from latency_transport import transport_interval, binomial_box

HERE = Path(__file__).resolve().parent


def witness(cap):
    # Rows are two equiprobable mission types; columns are fast/slow response.
    fixed = np.array([0, 0, 1, 1])
    rival = np.array([0, 1, 0, 0])
    margins = [[1, 1, 0, 0], [0, 0, 1, 1], [1, 0, 1, 0]]
    losses=np.stack((fixed,rival))
    constraints=(1-losses)[:,None,:]
    return feasible_rival_regret(losses,constraints,[cap],([],[],margins,[.5]*3))[0]


def sensitivity():
    data = np.load(HERE/'margin_first_alerts.npz')
    names = list(data['methods'])
    times = data['tau'][:, [names.index(m) for m in ['restart','cusum','glr']]]
    margins = np.where((times>100)&(times<=300),310-times,-np.inf)
    levels = (margins[:,:,None]>=np.array([10,100,200])).sum(axis=2)
    ids = np.ravel_multi_index(levels.T,(4,4,4))
    types = np.array(list(product(range(4),repeat=3)))
    losses = (types[:,:,None]<np.arange(1,4)).astype(float)
    cost = losses[:,0]-losses[:,1]
    q = np.array([.5,.3,.2])
    with (HERE/'latency_sensitivity.csv').open('w',newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['n','lower','upper','joint_error_over_three_prefixes'])
        for n in [500,1500,5000]:
            lo,hi = binomial_box(np.bincount(ids[:n],minlength=64),.05/3)
            writer.writerow([n,*transport_interval(cost,lo,hi,q,q),.05])


if __name__=='__main__':
    for cap in [.5,.55,.6,.75,1.]:
        np.testing.assert_allclose(witness(cap),cap-.5,atol=1e-12)
    sensitivity()
