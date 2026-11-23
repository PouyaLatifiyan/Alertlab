"""Confidence-aware selection among frozen candidates. All metrics are losses.
Intervals supplied to select must already be simultaneous for all decisions.
"""
from itertools import combinations
from math import isfinite
import numpy as np
from scipy.stats import beta

def cp(k, n, alpha):
    """Two-sided Clopper--Pearson interval; alpha is its total error budget."""
    if not isinstance(n,(int,np.integer)) or not isinstance(k,(int,np.integer)) or not 0<=k<=n or n==0 or not 0<alpha<1:
        raise ValueError("need 0 <= integer k <= positive integer n and alpha in (0,1)")
    return (0.0 if k==0 else float(beta.ppf(alpha/2,k,n-k+1)),
            1.0 if k==n else float(beta.isf(alpha/2,k+1,n-k)))

def binary(a):
    a=np.asarray(a)
    if a.ndim!=1 or len(a)==0 or not np.isin(a,[0,1]).all():
        raise ValueError("expected a nonempty vector of observed binary outcomes")
    return a.astype(bool)

def pair_interval_counts(n10,n01,n,alpha):
    """Interval for risk(A)-risk(B) via discordance rate and orientation."""
    if min(n10,n01)<0 or n10+n01>n: raise ValueError("invalid discordance counts")
    m=n10+n01
    d=cp(m,n,alpha/2)
    q=cp(n10,m,alpha/2) if m else (0.,1.)
    values=[discordance*(2*direction-1) for discordance in d for direction in q]
    return min(values),max(values)

def pair_interval(a,b,alpha):
    a,b=binary(a),binary(b)
    if len(a)!=len(b): raise ValueError("pair vectors on the same missions")
    return pair_interval_counts(np.count_nonzero(a&~b),np.count_nonzero(b&~a),len(a),alpha)

def simultaneous(outcomes, alpha=.05, paired_metrics=()):
    """Inputs candidate -> loss name -> vector. Within each metric, array order
    identifies the same missions across candidates. Different metrics can have
    different cohorts. Every supplied pair comparison shares the same budget.
    """
    names=list(outcomes)
    if not names or not 0<alpha<1: raise ValueError("missing candidates or invalid alpha")
    keys=list(outcomes[names[0]])
    if not keys or any(set(outcomes[i])!=set(keys) for i in names):
        raise ValueError("each candidate requires the same named metrics")
    paired_metrics=tuple(dict.fromkeys(paired_metrics))
    if set(paired_metrics)-set(keys): raise ValueError("unknown pair metric")
    pairs=list(combinations(names,2))
    count=len(names)*len(keys)+len(pairs)*len(paired_metrics)
    per=alpha/count
    data={i:{k:binary(outcomes[i][k]) for k in keys} for i in names}
    marginal={i:{k:cp(int(x.sum()),len(x),per) for k,x in row.items()} for i,row in data.items()}
    contrasts={k:{} for k in paired_metrics}
    for k in paired_metrics:
        for i,j in pairs:
            l,u=pair_interval(data[i][k],data[j][k],per)
            contrasts[k][i,j]=(l,u)
            contrasts[k][j,i]=(-u,-l)
    return marginal,contrasts

def _pair_upper(i,j,metric,intervals,paired):
    if i==j: return 0.
    u=intervals[i][metric][1]-intervals[j][metric][0]
    return min(u,paired.get(metric,{}).get((i,j),(-1.,1.))[1])

def select(candidates, intervals, budgets, objective='hazard', costs=None,
           cost_budget=None, paired=None, oracle_lower=0.):
    """Deterministic upper-risk rule; tie breaking follows candidate input order.
    Returns inner/outer feasible sets, candidate-optimal risk interval, rigorous
    excess bound and strict ordering if separable. No feasibility presumed.
    oracle_lower must be an independently justified lower bound for the broader
    feasible risk with the same loss, information and constraints.
    """
    names=list(candidates)
    if not names or len(set(names))!=len(names): raise ValueError("candidates must be unique")
    keys=set(budgets)|{objective}
    if not isfinite(oracle_lower) or not 0<=oracle_lower<=1: raise ValueError("invalid probability lower bound")
    if any(not 0<=b<=1 for b in budgets.values()): raise ValueError("invalid risk budget")
    for i in names:
        for k in keys:
            l,u=intervals[i][k]
            if not 0<=l<=u<=1: raise ValueError("invalid probability interval")
    if cost_budget is not None and (costs is None or not isfinite(cost_budget) or any(not isfinite(costs[i]) for i in names)):
        raise ValueError("all resource costs and budget must be finite")
    pair=paired or {}
    admitted=[i for i in names if cost_budget is None or costs[i]<=cost_budget]
    outer=[i for i in admitted if all(intervals[i][k][0]<=b for k,b in budgets.items())]
    inner=[i for i in outer if all(intervals[i][k][1]<=b for k,b in budgets.items())]
    result=dict(feasible=inner,unresolved=[i for i in outer if i not in inner],
                infeasible=[i for i in names if i not in outer],choice=None,
                unique_best=False,inferior_to_choice=[],candidate_optimum_interval=None,
                candidate_excess_upper=None,admissible_excess_upper=None)
    if not inner:
        result['status']='infeasible' if not outer else 'insufficient evidence'
        return result
    best=min(inner,key=lambda i:intervals[i][objective][1])
    upper=intervals[best][objective][1]
    gap=max(_pair_upper(best,j,objective,intervals,pair) for j in outer)
    if upper<oracle_lower:
        raise ValueError("analytic lower bound conflicts with selected upper bound")
    inferior=[j for j in outer if _pair_upper(best,j,objective,intervals,pair)<0]
    result.update(choice=best,status='certified feasible selection',
                  candidate_optimum_interval=(max(oracle_lower,min(intervals[i][objective][0] for i in outer)),upper),
                  candidate_excess_upper=min(upper-oracle_lower,max(0.,gap)),
                  admissible_excess_upper=upper-oracle_lower,inferior_to_choice=inferior,
                  unique_best=len(inferior)==len(outer)-1)
    return result

def pareto(inner,outer,intervals,metrics,paired=None,costs=None):
    """Return outer superset of feasible nondominated candidates. A witness
    must be certified feasible and dominate every loss (and specified cost).
    """
    if not metrics: raise ValueError("specify Pareto losses")
    if not set(inner)<=set(outer):raise ValueError("inner must lie within outer")
    front=[]
    witnesses={}
    for j in outer:
        for i in inner:
            if i==j:continue
            differences=[_pair_upper(i,j,k,intervals,paired or {}) for k in metrics]
            if costs is not None:differences.append(costs[i]-costs[j])
            if max(differences)<=0 and min(differences)<0:
                witnesses[j]=i
                break
        else:front.append(j)
    return front,witnesses

def robust_intervals(by_scenario,weight_vertices=None,tv_radius=0.):
    """Aggregate simultaneous scenario intervals over the convex hull of named
    weight vertices. With no vertices, all mixtures are allowed. tv_radius
    bounds the per-stratum TV distance between validated and deployed mission
    laws on which losses are defined. Inputs are statistical, not fitted here.
    """
    if not by_scenario or not 0<=tv_radius<=1: raise ValueError("invalid uncertainty set")
    strata=list(by_scenario)
    weights=np.eye(len(strata)) if weight_vertices is None else np.asarray(weight_vertices,float)
    if weights.ndim!=2 or weights.shape[1]!=len(strata) or not len(weights) or not np.isfinite(weights).all() or (weights<0).any() or not np.allclose(weights.sum(axis=1),1,atol=1e-12,rtol=0):
        raise ValueError("weights must be probability vertices in scenario input order")
    first=by_scenario[strata[0]]
    if not first or any(set(by_scenario[s]) != set(first) for s in strata):
        raise ValueError('all strata must contain the same nonempty candidate menu')
    if any(set(by_scenario[s][i]) != set(first[i]) for s in strata for i in first):
        raise ValueError('all strata must have the same metrics per candidate')
    out={i:{} for i in first}
    for i in first:
        for metric in first[i]:
            bounds=np.asarray([by_scenario[s][i][metric] for s in strata],float)
            if not np.isfinite(bounds).all() or (bounds[:,0]>bounds[:,1]).any() or bounds.min()<0 or bounds.max()>1:
                raise ValueError("invalid stratum probability intervals")
            # A bound on the worst optimized mixture of the actual displaced
            # risks, not a claim that TV radius can be estimated from these data.
            out[i][metric]=(float(np.max(weights@np.maximum(0.,bounds[:,0]-tv_radius))),
                            float(np.max(weights@np.minimum(1.,bounds[:,1]+tv_radius))))
    return out
