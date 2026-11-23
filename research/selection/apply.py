"""Re-evaluate the published joint confidence region or an identically formatted
coordinate CSV. See README for formats. Prints a machine-readable decision.
"""
import argparse
import csv
import json
from pathlib import Path
from decision import select,pareto,robust_intervals

BENCH=Path(__file__).resolve().parents[1]/'bench'
def readrows(p):
    with Path(p).open(newline='') as f:
        return list(csv.DictReader(f))
def run(args):
    strata=args.scenarios
    by_s={}
    costs={}
    for scenario in strata:
        rows=[r for r in readrows(args.coordinates) if r['scenario']==scenario and float(r['false_alarm_cap'])==args.operating_point]
        if not rows:raise ValueError('missing scenario/operating-point '+scenario)
        by_s[scenario]={}
        for r in rows:
            i=r['method']
            if i in by_s[scenario]:raise ValueError('duplicate candidate in a stratum')
            by_s[scenario][i]={k:(float(r[k+'_lo']),float(r[k+'_up'])) for k in ('fa','miss','risk')}
            costs[i]=max(costs.get(i,0),int(r['slots']))
    # Multi-stratum worst case assumes one shared implementable policy per
    # candidate. Cross-stratum input or calibration changes require the
    # deployment to observe the appropriate configuration.
    if len(strata)>1:
        thresholds=readrows(args.thresholds)
        config={}
        design=json.loads(args.design.read_text())['scenarios']
        for s in strata:
            present = set()
            for r in thresholds:
                if r['scenario']!=s or float(r['budget'])!=args.operating_point:continue
                i=r['method']
                if i in present: raise ValueError('duplicate frozen policy metadata')
                present.add(i)
                cfg=(float(r['threshold']),design[s]['w'] if i=='RankRestart' else None)
                if i in config and config[i]!=cfg:
                    raise ValueError('different frozen thresholds/reference designs across strata; construct a shared-policy comparison first')
                config[i]=cfg
            if present != set(by_s[s]): raise ValueError('incomplete frozen policy metadata')
    paired={}
    if len(strata)==1 and not args.tv:
        pp={}
        for r in readrows(args.pairs):
            if r['scenario']==strata[0] and float(r['cap'])==args.operating_point:
                l,u=float(r['lower']),float(r['upper'])
                pp[r['A'],r['B']]=l,u
                pp[r['B'],r['A']]=-u,-l
        paired={'risk':pp}
    intervals=robust_intervals(by_s,tv_radius=args.tv)
    names=sorted(intervals,key=costs.get)
    budgets={'fa':args.fa_limit if args.fa_limit is not None else args.operating_point,'risk':args.hazard_limit}
    result=select(names,intervals,budgets,objective='risk',costs=costs,cost_budget=args.slots,paired=paired,oracle_lower=args.oracle_lower)
    outer=result['feasible']+result['unresolved']
    front,w=pareto(result['feasible'],outer,intervals,['fa','miss','risk'],paired,costs)
    result.update(outer_pareto=front,dominance_witnesses=w,intervals=intervals,cost_slots=costs,
                  strata=strata,objective='worst stratum physical hazard',budgets=budgets)
    return result
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--scenarios',nargs='+',required=True)
    p.add_argument('--operating-point',type=float,default=.02)
    p.add_argument('--fa-limit',type=float)
    p.add_argument('--hazard-limit',type=float,default=.6)
    p.add_argument('--slots',type=int,default=250)
    p.add_argument('--tv',type=float,default=0)
    p.add_argument('--oracle-lower',type=float,default=0)
    p.add_argument('--coordinates',type=Path,default=BENCH/'coordinate_intervals.csv')
    p.add_argument('--pairs',type=Path,default=BENCH/'paired_intervals.csv')
    p.add_argument('--thresholds',type=Path,default=BENCH/'thresholds.csv')
    p.add_argument('--design',type=Path,default=BENCH/'design.json')
    print(json.dumps(run(p.parse_args()),indent=2))
