"""Verify regret using a single mixed-integer model with a chosen rival."""
import csv
import numpy as np
from scipy.optimize import milp, Bounds, LinearConstraint
from compare_regret import cells,cols,ineq,rhs,q,HERE,miss,NAMES

def generic_value(i,resource,cap):
    # Unknowns: cell probabilities, one comparator bit per monitor, regret.
    m,n=cells.shape
    A=[]; upper=[];lower=[]
    def add(p,bits,t,lo,hi):
        A.append(np.r_[p,bits,t]); lower.append(lo);upper.append(hi)
    for row,hi in zip(ineq,rhs):
        add(row,np.zeros(m),0,-np.inf,hi)
    for row,mass in zip(cols,q):
        add(row,np.zeros(m),0,mass,mass)
    add(np.zeros(n),np.ones(m),0,1,1)
    for j in range(m):
        bit=np.eye(m)[j]
        # For an inactive rival these rows are redundant since all costs lie in [0,1].
        add(resource[j],bit,0,-np.inf,cap+1)
        add(cells[j]-cells[i],2*bit,1,-np.inf,2)
    sol=milp(np.r_[np.zeros(n+m),-1],integrality=np.r_[np.zeros(n),np.ones(m),0],
             bounds=Bounds(np.zeros(n+m+1),np.ones(n+m+1)),
             constraints=LinearConstraint(A,lower,upper),options={'mip_rel_gap':0.})
    assert sol.success,sol.message
    return -sol.fun
if __name__=='__main__':
    checked=0
    for row in csv.DictReader((HERE/'matched_regret.csv').open()):
        if row['robust_feasible']!='True':continue
        weights=[1,1,1] if row['contract']=='one slot per handoff' else [.05,.5,1]
        resource=((1-miss)*weights).reshape(3,-1)
        val=generic_value(NAMES.index(row['monitor']),resource,float(row['budget']))
        np.testing.assert_allclose(val,float(row['same_law_bound']),atol=2e-7)
        checked+=1
    print(checked,'robust candidate/budget values reproduced by direct statewise regret MILP')
