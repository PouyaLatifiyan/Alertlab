"""Independent numerical cross-checks for the released aggregate decision tables."""
import csv
from fractions import Fraction
from itertools import combinations, product
from pathlib import Path
import sys

import numpy as np
from scipy.optimize import linprog
from scipy.stats import beta

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'selection'))
from decision import select


def rows(file):
    with file.open(newline='') as f:
        return list(csv.DictReader(f))


def verify_benchmark():
    folder = ROOT / 'bench'
    coords = rows(folder/'coordinate_intervals.csv')
    paired = rows(folder/'paired_intervals.csv')
    decisions = rows(folder/'decisions.csv')
    assert len(coords)==144 and len(paired)==216 and len(decisions)==144
    for row in coords:
        for key in ('fa', 'risk', 'miss'):
            count = int(row[key+'_k'])
            n=12000
            low = 0 if not count else beta.ppf(.05/(2*864),count,n-count+1)
            high = 1 if count==n else beta.isf(.05/(2*864),count+1,n-count)
            np.testing.assert_allclose([low,high], [float(row[key+'_lo']), float(row[key+'_up'])], atol=1e-12)
    for out in decisions:
        s,cap = out['scenario'],out['fa_cap']
        matching = [r for r in coords if r['scenario']==s and r['false_alarm_cap']==cap]
        sets = {r['method']:{k:(float(r[k+'_lo']),float(r[k+'_up'])) for k in ('fa','risk')} for r in matching}
        cost = {r['method']:int(r['slots']) for r in matching}
        bounds = {}
        for r in paired:
            if r['scenario']==s and r['cap']==cap:
                a,b = r['A'],r['B']
                d=float(r['lower']),float(r['upper'])
                bounds[a,b]=d
                bounds[b,a]=-d[1],-d[0]
        choice=select(sets,sets,{'fa':float(cap),'risk':float(out['hazard_cap'])},'risk',
                      costs=cost,cost_budget=int(out['slot_cap']),paired={'risk':bounds})
        assert (choice['choice'] or '')==out['choice'],out
        assert set(choice['feasible'])==set(filter(None,out['inner'].split(',')))
        assert set(choice['feasible']+choice['unresolved'])==set(filter(None,out['outer'].split(',')))
        if out['choice']:
            np.testing.assert_allclose(choice['candidate_excess_upper'],float(out['excess_upper']))
            assert choice['unique_best']==(out['status']=='unique certified')
    for r in rows(folder/'admissible_limits.csv'):
        if r['selected']:
            lo,up=map(float,(r['admissible_lower'],r['risk_upper']))
            assert up>=lo
            np.testing.assert_allclose(float(r['global_gap_upper']),up-lo)
    print('432 marginal intervals, 144 selection decisions and 36 class envelope rows checked.')


def verify_oracle():
    # Alternative primal occupancy formulation, no stopping-tree enumeration.
    nodes=[''.join(p) for i in (1,2,3) for p in product('01',repeat=i)]
    leaves=[u for u in nodes if len(u)==3]
    def prob(u,p):return p**u.count('1')*(1-p)**u.count('0')
    prob0=np.array([prob(u,.2) for u in nodes])
    reward=np.array([.4*prob(u,.8)*(len(u)<=1)+.6*prob(u,.6) for u in nodes])
    path=np.array([[float(v.startswith(u)) for u in nodes] for v in leaves])
    for r in rows(ROOT/'limits'/'decision.csv'):
        a=float(Fraction(r['alpha']))
        opt=linprog(-reward,A_ub=np.vstack([path,prob0]),b_ub=[*[1]*len(leaves),a],
                    bounds=(0,1),method='highs')
        assert opt.success
        np.testing.assert_allclose(-opt.fun,float(Fraction(r['optimal_causal_timely'])),atol=1e-12)
        np.testing.assert_allclose(1+.9*opt.fun,float(Fraction(r['optimal_hazard'])),atol=1e-12)
    print('All 5 exact causal optima also reproduced by occupancy LP.')


if __name__=='__main__':
    verify_benchmark()
    verify_oracle()
