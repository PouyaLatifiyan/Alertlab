"""Exact three-epoch partially observed mission; all probabilities are rational.
Run python oracle.py (standard library). Plot creation requires matplotlib.
"""
from fractions import Fraction as F
from itertools import product
from pathlib import Path
import csv

OUT = Path(__file__).resolve().parent
H=3
P0=F(1,5)
# (prior probability, last useful alarm epoch, Pr(sensor=1))
MODES=((F(2,5),1,F(4,5)),(F(3,5),3,F(3,5)))
EFFICACY=F(9,10)
BUDGETS=[F(1,25),F(1,10),F(1,5),F(3,10),F(1,2)]

def histories(t):
    return [''.join(s) for s in product('01',repeat=t)]

def mass(path,p):
    ones=path.count('1')
    return p**ones*(1-p)**(len(path)-ones)

def reward(path):
    return sum(w*mass(path,p) for w,d,p in MODES if len(path)<=d)

def antichains(path):
    # The alarm decision is made after the current symbol.
    if len(path)==H:
        return [(),(path,)]
    children=[a+b for a in antichains(path+'0') for b in antichains(path+'1')]
    return [(path,)]+children

def metrics(stops):
    return sum((mass(s,P0) for s in stops),F(0)),sum((reward(s) for s in stops),F(0))

def upper_hull(points):
    ys={}
    for x,y in points:
        ys[x]=max(ys.get(x,F(0)),y)
    hull=[]
    for x,y in sorted(ys.items()):
        if hull and y<=hull[-1][1]:
            continue
        while len(hull)>=2:
            a,b=hull[-2:]
            if (b[1]-a[1])*(x-b[0])>(y-b[1])*(b[0]-a[0]):
                break
            hull.pop()
        hull.append((x,y))
    return hull

def power_at(hull,alpha):
    for (a,b),(c,d) in zip(hull,hull[1:]):
        if a<=alpha<=c:
            return b+(d-b)*(alpha-a)/(c-a),(d-b)/(c-a)
    return hull[-1][1],F(0)

def dynamic_support(lam):
    # Separate derivation from support-function Bellman recursion.
    def value(h):
        stop=reward(h)-lam*mass(h,P0)
        cont=F(0) if len(h)==H else value(h+'0')+value(h+'1')
        return max(stop,cont)
    return value('0')+value('1')

RULES={'Off':lambda s:False,
       'First positive':lambda s:s[-1]=='1',
       'First two positive':lambda s:s.count('1')>=2,
       'Two consecutive':lambda s:s.endswith('11'),
       'Three consecutive':lambda s:s.endswith('111'),
       'First epoch positive':lambda s:s=='1',
       'Majority at final':lambda s:len(s)==H and s.count('1')>=2}

def paths_for(rule):
    stops=[]
    for t in range(1,H+1):
        for s in histories(t):
            if rule(s) and not any(s.startswith(v) for v in stops):
                stops.append(s)
    return stops

def full_history_np(alpha,prob_alt):
    # Fractional knapsack on likelihood ratios, equal ratios may be split.
    leaves=sorted(histories(H),key=lambda s:prob_alt(s)/mass(s,P0),reverse=True)
    power=F(0)
    for s in leaves:
        use=min(alpha,mass(s,P0))
        power+=use*prob_alt(s)/mass(s,P0);alpha-=use
    return power

def main():
    options=[metrics(a+b) for a in antichains('0') for b in antichains('1')]
    assert len(options)==676
    hull=upper_hull(options)
    for (x,y),(z,w) in zip(hull,hull[1:]):
        lam=(w-y)/(z-x)
        assert dynamic_support(lam)==y-lam*x
    cand={name:metrics(paths_for(rule)) for name,rule in RULES.items()}
    rows=[]
    for a in BUDGETS:
        feasible={n:y for n,(x,y) in cand.items() if x<=a}
        best=max(feasible.values())
        name=' / '.join(n for n,y in feasible.items() if y==best)
        causal,lam=power_at(hull,a)
        assert causal==dynamic_support(lam)+lam*a
        np_upper=full_history_np(a,lambda s:sum(w*mass(s,p) for w,d,p in MODES))
        assert best<=causal<=np_upper
        harm=lambda opportunity:1-EFFICACY*opportunity
        rows.append([a,name,best,causal,np_upper,harm(best),harm(causal),harm(best)-harm(causal)])
    def save(name,columns,rows):
        with (OUT/name).open('w',newline='') as f:
            w=csv.writer(f);w.writerow(columns)
            w.writerows([str(x) for x in row] for row in rows)
    save('decision.csv',['alpha','selected','candidate_timely','optimal_causal_timely','relaxed_np_timely_upper','candidate_hazard','optimal_hazard','exact_hazard_gap'],rows)
    save('frontier.csv',['false_alarm','timely'],hull)
    save('candidates.csv',['monitor','false_alarm','timely'],[(n,*v) for n,v in cand.items()])
    for row in rows:print(row[1],*[round(float(x),6) for i,x in enumerate(row) if i!=1])
    return hull,cand

if __name__=='__main__':
    hull,cand=main()
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        raise SystemExit(0)
    import numpy as np
    from matplotlib.ticker import PercentFormatter
    fig,ax=plt.subplots(figsize=(5.8,3.15),layout='constrained')
    xs=np.linspace(0,.5,251)
    ax.plot(xs,[float(full_history_np(F(str(x)),lambda s:sum(w*mass(s,p) for w,d,p in MODES))) for x in xs],ls='--',label='Full-history test upper bound',color='#8276a6')
    ax.plot(*zip(*[(float(x),float(y)) for x,y in hull]),label='Exact randomized causal frontier',color='#005e68',lw=2.2)
    ax.scatter([float(x) for x,y in cand.values()],[float(y) for x,y in cand.values()],s=30,label='Fixed candidate rules',color='#b24224',zorder=3)
    ax.set(xlabel='Maximum healthy mission false-alarm probability',ylabel='Probability of timely warning',xlim=(-.005,.505),ylim=(-.02,1.02))
    ax.yaxis.set_major_formatter(PercentFormatter(1))
    ax.xaxis.set_major_formatter(PercentFormatter(1))
    ax.grid(axis='y',alpha=.15);ax.legend(fontsize=8,loc='lower right')
    fig.savefig(OUT/'causal_frontier.pdf')
