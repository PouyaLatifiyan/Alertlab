"""Sensitivity to a deployment population rather than an invented mission prior."""
from pathlib import Path
from itertools import permutations
import csv
import numpy as np
import matplotlib.pyplot as plt
HERE=Path(__file__).resolve().parent
B=HERE.parent/'bench'
SCENS=['moderate persistent','brief pulse']
METHODS=['Shewhart','CUSUM','GLR16','RankRestart']

def read(name):
    with (B/name).open() as f:return list(csv.DictReader(f))
def main():
    bounds={}; diff={}; thresholds={}
    for row in read('thresholds.csv'):
        if row['scenario'] in SCENS and float(row['budget'])==.02:
            thresholds[row['scenario'],row['method']]=float(row['threshold'])
    for m in METHODS:assert thresholds[SCENS[0],m]==thresholds[SCENS[1],m]
    for row in read('coordinate_intervals.csv'):
        if row['scenario'] in SCENS and float(row['false_alarm_cap'])==.02:
            bounds[row['scenario'],row['method']]=np.array([float(row[k]) for k in ['fa_lo','fa_up','risk_lo','risk_up']])
    for row in read('paired_intervals.csv'):
        if row['scenario'] in SCENS and float(row['cap'])==.02:
            l,h=float(row['lower']),float(row['upper'])
            diff[row['scenario'],row['A'],row['B']]=[l,h]
            diff[row['scenario'],row['B'],row['A']]=[-h,-l]
    grid=np.linspace(0,1,1001); rows=[]
    fig,ax=plt.subplots(figsize=(7,3.6),layout='constrained')
    for m in METHODS:
        a,b=[bounds[s,m] for s in SCENS]
        low=grid*a[2]+(1-grid)*b[2];up=grid*a[3]+(1-grid)*b[3]
        ax.plot(grid,(low+up)/2,label=m)
        ax.fill_between(grid,low,up,alpha=.13)
    for q in grid:
        box={m:q*bounds[SCENS[0],m]+(1-q)*bounds[SCENS[1],m] for m in METHODS}
        inside=[m for m,v in box.items() if v[1]<=.02 and v[3]<=.6]
        outside=[m for m,v in box.items() if v[0]<=.02 and v[2]<=.6]
        if inside:
            sel=min(inside,key=lambda m:box[m][3])
            gap=max([0]+[min(box[sel][3]-box[m][2],q*diff[SCENS[0],sel,m][1]+(1-q)*diff[SCENS[1],sel,m][1]) for m in outside if m!=sel])
            status='unique' if all(q*diff[SCENS[0],sel,m][1]+(1-q)*diff[SCENS[1],sel,m][1]<0 for m in outside if m!=sel) else 'unresolved'
        else: sel='';gap='';status='no certified feasible policy'
        rows.append([q,','.join(inside),','.join(outside),sel,status,gap])
    ax.axhline(.6,ls=':',color='black',lw=1,label='Hazard budget')
    ax.set(xlabel='Deployment fraction of moderate persistent missions',ylabel='Model-based hazard probability',xlim=(0,1),ylim=(0,1.01))
    ax.legend(ncol=3,fontsize=8);fig.savefig(HERE/'mission_mix.pdf')
    with (HERE/'mission_mix.csv').open('w',newline='') as fp:
        w=csv.writer(fp);w.writerow(['moderate_fraction','inner','outer','min_upper','status','excess_upper']);w.writerows(rows)
    import itertools
    for key,group in itertools.groupby(rows,key=lambda r:(r[3],r[4])):
        g=list(group);print(key,g[0][0],g[-1][0])
    for x in (0,.25,.5,.75,1):print(rows[round(x*1000)])
if __name__=='__main__':main()
