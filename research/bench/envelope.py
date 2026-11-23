"""Admissible-class physical risk lower bound for the single-attempt benchmark."""
from pathlib import Path
import csv
import numpy as np
from scipy.special import ndtr, ndtri
from run import BUDGET, HERE, METHODS, SCENARIOS, T, profile, write

def crossing_cdf(peak):
    # Integral of clip((peak*load-.85)/.30, 0, 1), load uniform on [.85,1.15].
    peak=np.asarray(peak)
    cdf=np.zeros_like(peak,dtype=float)
    c=peak[peak>0]
    def mean_hinge(threshold):
        return (np.maximum(c*1.15-threshold,0)**2-np.maximum(c*.85-threshold,0)**2)/(.6*c)
    cdf[peak>0]=np.clip((mean_hinge(.85)-mean_hinge(1.15))/.30,0,1)
    return cdf

def lower(s,alpha):
    total=0.
    untreated=0.
    for onset in range(s.onset_lo,s.onset_hi+1):
        age=np.arange(1,T+1)-onset
        mean=s.mu*profile(age,s)
        # Same exogenous clock observation in protected and untreated states.
        quadratic=np.r_[mean[0]**2,(mean[1:]-s.rho*mean[:-1])**2/(1-s.rho**2)]/s.noise**2
        separation=np.r_[0.,np.sqrt(np.cumsum(quadratic))]
        power=ndtr(ndtri(alpha)+separation);power[0]=0.  # no epoch 0 action
        force=profile(age-s.delay,s).astype(float)*s.drive
        if s.shape=='pulse' and s.duration==1:force=((age>=s.delay)&(age<s.delay+19))*s.drive
        state=0.; trajectory=[]
        for v in force:
            state=.985*state+v
            trajectory.append(state)
        cdf=np.maximum.accumulate(crossing_cdf(np.maximum.accumulate(trajectory)))
        mass=np.diff(np.r_[0.,cdf])
        for lat in range(s.latency_lo,s.latency_hi+1):
            last=np.maximum(0,np.arange(1,T+1)-lat)
            fail_given_cross=s.fault_probability+(1-s.fault_probability)*(1-power[last])
            total+=mass@fail_given_cross/(s.latency_hi-s.latency_lo+1)
        untreated+=cdf[-1]
    return total/(s.onset_hi-s.onset_lo+1),untreated/(s.onset_hi-s.onset_lo+1)

def run():
    coords=list(csv.DictReader((HERE/'coordinate_intervals.csv').open()))
    decisions=list(csv.DictReader((HERE/'decisions.csv').open()))
    output=[]; fronts=[]
    for s in SCENARIOS:
        for b in BUDGET:
            lb,p_h=lower(s,b)
            sub=[x for x in coords if x['scenario']==s.name and float(x['false_alarm_cap'])==b]
            lookup={x['method']:x for x in sub}
            # Pareto confidence superset: exclude only if comparator uniformly dominates.
            for a in sub:
                dominated=[]
                for d in sub:
                    if d is a or int(d['slots'])>int(a['slots']):continue
                    metrics=['fa','miss','risk']
                    nonworse = all(float(d[k+'_up']) <= float(a[k+'_lo']) for k in metrics)
                    strict = (int(d['slots']) < int(a['slots']) or
                              any(float(d[k+'_up']) < float(a[k+'_lo']) for k in metrics))
                    if nonworse and strict:
                        dominated.append(d['method'])
                fronts.append(dict(scenario=s.name,cap=b,method=a['method'],plausible_frontier=int(not dominated),certified_dominators=','.join(dominated)))
            for d in decisions:
                if d['scenario']==s.name and float(d['fa_cap'])==b and d['slot_cap']=='250' and d['hazard_cap']=='0.6':
                    up=float(lookup[d['choice']]['risk_up']) if d['choice'] else None
                    if up is not None and up < lb:
                        raise ValueError('analytic lower bound exceeds statistical upper bound: '+s.name)
                    output.append(dict(scenario=s.name,fa_cap=b,untreated_probability=p_h,admissible_lower=lb,selected=d['choice'],risk_upper=up,global_gap_upper='' if up is None else up-lb))
    write('admissible_limits.csv',output);write('pareto.csv',fronts)
if __name__=='__main__':run()
