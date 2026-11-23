"""Worst feasible-rival regret on a bounded probability polytope.

Each column is one joint mission/latency cell. 'poly' is (A_ub,b_ub,
A_eq,b_eq) for the cell masses, including normalization and marginals.
"""
import numpy as np
from scipy.optimize import linprog


def feasible_rival_regret(losses, constraints, budgets, poly):
    a, b, e, f = poly
    costs = np.asarray(losses, dtype=float)
    limits = np.asarray(budgets, dtype=float)
    usage = np.asarray(constraints, dtype=float)
    if costs.ndim != 2 or usage.shape != (len(costs),len(limits),costs.shape[1]):
        raise ValueError("expected monitor by cell losses and monitor by constraint by cell usage")
    a=np.asarray(a,dtype=float).reshape(-1,costs.shape[1])
    b=np.asarray(b,dtype=float)
    def maximum(objective, rival=None):
        rows,rhs=a,b
        if rival is not None:
            rows=np.vstack((a,usage[rival]))
            rhs=np.concatenate((b,limits))
        sol=linprog(-objective,A_ub=rows,b_ub=rhs,A_eq=e,b_eq=f,bounds=(0,None))
        if sol.status==2:
            return None
        if not sol.success:
            raise ValueError(sol.message)
        return -sol.fun
    if maximum(np.zeros(costs.shape[1])) is None:
        raise ValueError("empty input law region")
    result=[]
    for i,loss in enumerate(costs):
        if any(maximum(row)>cap+1e-10 for row,cap in zip(usage[i],limits)):
            result.append(None)
            continue
        gaps=[maximum(loss-other,j) for j,other in enumerate(costs)]
        result.append(max(g for g in gaps if g is not None))
    return result
