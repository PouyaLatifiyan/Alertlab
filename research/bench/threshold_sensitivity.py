"""Sensitivity to the engineering limit with frozen thresholds and paired paths."""
from dataclasses import replace
from pathlib import Path
import csv
import numpy as np
from run import SCENARIOS, trial, first, physical, chunk, cp

HERE = Path(__file__).resolve().parent
METHODS = ['Shewhart','CUSUM','GLR16','RankRestart']
SCALES = [.8,1.,1.2]
N = 6000


def run():
    with (HERE/'thresholds.csv').open() as f:
        thresholds = {(r['scenario'],r['method']):float(r['threshold'])
                      for r in csv.DictReader(f) if float(r['budget'])==.02}
    rows = []
    for scenario_id in [1,3,4]:
        s = SCENARIOS[scenario_id]
        rng = np.random.default_rng(37601+scenario_id)
        counts = np.zeros((3,4),int)
        means = np.zeros(4)
        detected = np.zeros(4,int)
        for n in chunk(N):
            scores,onset,age = trial(rng,n,s,True)
            tau = np.stack([first(z>thresholds[s.name,m]) for z,m in zip(scores,METHODS)],axis=1)[:,:,None]
            delay=tau[:,:,0]-onset[:,None]
            eligible=(delay>=0)&(tau[:,:,0]<=age.shape[1])
            detected+=eligible.sum(axis=0)
            means+=np.where(eligible,delay,0).sum(axis=0)
            seed = rng.integers(2**31)
            for k,scale in enumerate(SCALES):
                # Linear dynamics: dividing forcing by scale is identical to
                # multiplying the unsafe-state threshold by scale on both paths.
                h,*_=physical(np.random.default_rng(seed),replace(s,drive=s.drive/scale),age,tau,onset)
                counts[k]+=h[:,:,0].sum(axis=0)
        lo,hi=cp(counts,N,.05/(2*counts.size*3))
        for k,scale in enumerate(SCALES):
            for j,m in enumerate(METHODS):
                rows.append([s.name,scale,m,N,counts[k,j],lo[k,j],hi[k,j],
                            detected[j],means[j]/detected[j] if detected[j] else ''])
    with (HERE/'threshold_sensitivity.csv').open('w',newline='') as f:
        w=csv.writer(f)
        w.writerow(['regime','limit_multiplier','monitor','n','hazards','lo','hi','eligible_detections','mean_delay_among_detected'])
        w.writerows(rows)

if __name__=='__main__':
    run()
