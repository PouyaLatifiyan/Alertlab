"""Paired, fixed-horizon evaluation of four existing monitor families.

Run with python run.py. Input is a fully specified synthetic scenario, not a
training dataset. Output observations precede control and are policy-invariant
clock/sensor readouts; intervention changes the downstream physical state.
"""
from dataclasses import dataclass, asdict
import csv, json
from pathlib import Path
import numpy as np
from scipy.special import logsumexp
from scipy.stats import beta
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE=Path(__file__).resolve().parent
T=80
METHODS=('Shewhart','CUSUM','GLR16','RankRestart')
BUDGET=np.array([.005,.02,.08])
CAL_N, TEST_N, BATCH=18000,12000,400
FRACTIONS=np.array([.1,.25,.5,.75,.9])
SEED=816341
SLOTS={'Shewhart':0,'CUSUM':2,'GLR16':17} # kinetic accumulators only, excluding shared input, clock, decision bit
@dataclass(frozen=True)
class Scenario:
    name:str
    mu:float
    shape:str
    rho:float=0.
    cal_rho:float=0.
    noise:float=1.
    w:int=80
    onset_lo:int=18
    onset_hi:int=30
    drive:float=.055
    duration:int=80
    delay:int=0
    latency_lo:int=2
    latency_hi:int=6
    fault_probability:float=.04

SCENARIOS=[
    Scenario('weak persistent',.45,'step',drive=.040),
    Scenario('moderate persistent',1.15,'step'),
    Scenario('negative persistent',-1.15,'step'),
    Scenario('slow ramp',2.2,'ramp',drive=.060),
    Scenario('brief pulse',4.5,'pulse',duration=1,drive=.095,delay=4,latency_lo=1,latency_hi=3),
    Scenario('transient drift',1.65,'pulse',duration=10,drive=.12,delay=4),
    Scenario('correlated',1.15,'step',rho=.65,cal_rho=.65),
    Scenario('short reference',1.15,'step',w=32),
    Scenario('long reference',1.15,'step',w=180),
    Scenario('late onset',1.15,'step',onset_lo=47,onset_hi=59),
    Scenario('slow response',1.15,'step',latency_lo=12,latency_hi=20,fault_probability=.15),
    Scenario('shifted healthy law',1.15,'step',rho=.65,noise=1.35),
]
def ar(rng,n,t,rho,sd=1.):
    x=rng.normal(size=(n,t))
    scale=np.sqrt(1-rho*rho)
    for i in range(1,t):
        x[:,i]=rho*x[:,i-1]+scale*x[:,i]
    return sd*x

def scores(z,refs):
    n,t=z.shape
    p=np.column_stack((np.zeros(n),np.cumsum(z,axis=1)))
    glr=np.zeros_like(z)
    for l in range(1,17):
        win=p[:,l:]-p[:,:-l]
        np.maximum(glr[:,l-1:],win*win/(2*l),out=glr[:,l-1:])
    cus=np.zeros_like(z); pos=np.zeros(n);neg=np.zeros(n)
    rank=np.zeros_like(z); w=refs.shape[1]
    refs=np.sort(np.abs(refs),axis=1)
    x=np.stack([np.searchsorted(r,np.abs(y),side='left')/w for r,y in zip(refs,z)])
    active=np.zeros((n,5)); starts=len(range(0,t,10))
    eps=np.sqrt(np.log(4000)/(2*w))
    for i in range(t):
        pos=np.maximum(0,pos+z[:,i]-.5);neg=np.maximum(0,neg-z[:,i]-.5)
        cus[:,i]=np.maximum(pos,neg)
        if i%10==0: active+=1
        active*=1+(x[:,i,None]/(.5+eps)-1)*FRACTIONS
        rank[:,i]=np.log((active.mean(axis=1)+starts-1-i//10)/starts)
    return (np.abs(z),cus,glr,rank)

def profile(age,s):
    active=age>=0
    if s.shape=='ramp':return np.clip((age+1)/16.,0.,1.)
    if s.shape=='pulse':return active*(age<s.duration)
    return active

def trial(rng,n,s,changed):
    z=ar(rng,n,T,s.rho,s.noise)
    refs=ar(rng,n,s.w,s.rho,s.noise)
    # First changed epoch (one-based). Onset unknown to all monitors.
    onset=rng.integers(s.onset_lo,s.onset_hi+1,n)
    age=np.arange(1,T+1)[None,:]-onset[:,None]
    if changed:z+=s.mu*profile(age,s)
    S=scores(z,refs)
    return S,onset,age

def calibrate(rng,s):
    maxima=[]
    for n in chunk(CAL_N):
        S=scores(ar(rng,n,T,s.cal_rho),ar(rng,n,s.w,s.cal_rho))
        maxima.append(np.column_stack([v.max(axis=1) for v in S]))
    # First integer rank at or above quantile; strict crossing handles atoms.
    maxima=np.sort(np.vstack(maxima),axis=0)
    k=np.ceil(CAL_N*(1-.55*BUDGET)).astype(int)
    return maxima[k-1].T

def chunk(n):
    return [min(BATCH,n-i) for i in range(0,n,BATCH)]
def first(flags):
    return np.where(flags.any(axis=-1),np.argmax(flags,axis=-1)+1,T+1)
def physical(rng,s,age,tau,onset):
    n=len(age)
    limit=rng.uniform(.85,1.15,n)
    latent_load=rng.uniform(.85,1.15,n)
    latency=rng.integers(s.latency_lo,s.latency_hi+1,n)
    working=rng.random(n)>=s.fault_probability
    force=profile(age-s.delay,s).astype(float)
    if s.shape=='pulse' and s.duration==1:
        # Downstream response to a single impulsive change lasts 19 epochs.
        force=((age>=s.delay)&(age<s.delay+19)).astype(float)
    force*=s.drive*latent_load[:,None]
    state=np.zeros(n); crossing=np.full(n,T+1,dtype=int)
    closed=np.zeros_like(tau,dtype=float);hazard=np.zeros_like(tau,dtype=bool)
    complete=tau+latency[:,None,None]
    for i in range(T):
        state=.985*state+force[:,i]
        crossing=np.where((state>=limit)&(crossing>T),i+1,crossing)
        mitigating=(complete<=i+1)&working[:,None,None]
        closed=np.where(mitigating,.68*closed+.12*force[:,i,None,None],
                          .985*closed+force[:,i,None,None])
        hazard|=closed>=limit[:,None,None]
    # Signed states have the same |state| by linearity. Persistent mitigation
    # can prevent hazard even following an early firing (policy counted in risk).
    need=crossing<=T
    eligible=(tau>=onset[:,None,None])&(tau<=T)
    miss=need[:,None,None]&~(eligible&(complete<=crossing[:,None,None]))
    return hazard,miss,need,crossing

def cp(k,n,tail):
    lo=np.zeros(np.shape(k)); hi=np.ones(np.shape(k))
    k=np.asarray(k)
    mask=k>0;lo[mask]=beta.ppf(tail,k[mask],n-k[mask]+1)
    mask=k<n;hi[mask]=beta.ppf(1-tail,k[mask]+1,n-k[mask])
    return lo,hi
def write(name,rows):
    with (HERE/name).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def run():
    cal={}
    rows=[];pairs=[];decisions=[];thresholds=[];counts={}
    # Family includes every published coordinate for all three nominal budgets
    # and both cells of each paired comparison at a given budget.
    number=len(SCENARIOS)*len(BUDGET)*(4*3+2*6)
    tail=.05/(2*number)
    seeds=np.random.SeedSequence(SEED).spawn(3*len(SCENARIOS))
    for si,s in enumerate(SCENARIOS):
        key=(s.w,s.cal_rho)
        if key not in cal:cal[key]=calibrate(np.random.default_rng(seeds[3*si]),s)
        th=cal[key]
        for j,m in enumerate(METHODS):
            for b,budget in enumerate(BUDGET):thresholds.append(dict(scenario=s.name,method=m,budget=budget,threshold=th[j,b]))
        null_rng=np.random.default_rng(seeds[3*si+1]);alt_rng=np.random.default_rng(seeds[3*si+2])
        false=[];hz=[];miss=[];need=[];cross=[];times=[]
        for n in chunk(TEST_N):
            S,_,_=trial(null_rng,n,s,False)
            false.append(np.stack([a.max(axis=1)[:,None]>th[j] for j,a in enumerate(S)],axis=1))
            S,onset,age=trial(alt_rng,n,s,True)
            tau=np.stack([first(a[:,None,:]>th[j,:,None]) for j,a in enumerate(S)],axis=1)
            h,o,v,c=physical(alt_rng,s,age,tau,onset)
            hz.append(h);miss.append(o);need.append(v);cross.append(c);times.append(tau)
        flags=np.stack([np.concatenate(y) for y in (false,miss,hz)],axis=-1)
        hazards=flags[:,:,:,2]
        k=flags.sum(axis=0); lo,up=cp(k,TEST_N,tail)
        sr={**asdict(s),'untreated_hazards':int(np.concatenate(need).sum())}
        for j,m in enumerate(METHODS):
            slots=SLOTS.get(m,s.w+5)
            for b,budget in enumerate(BUDGET):
                entry=dict(scenario=s.name,method=m,false_alarm_cap=budget,slots=slots,**{f'{metric}_{stat}':v[j,b,i] for i,metric in enumerate(('fa','miss','risk')) for stat,v in [('k',k),('lo',lo),('up',up)]})
                rows.append(entry)
        for b,budget in enumerate(BUDGET):
            contrasts={}
            for j in range(4):
                for l in range(j+1,4):
                    f=hazards[:,j,b];g=hazards[:,l,b]
                    d=np.array([np.sum(f&~g),np.sum(~f&g)])
                    lq,uq=cp(d,TEST_N,tail)
                    left,right=lq[0]-uq[1],uq[0]-lq[1]
                    contrasts[(j,l)]=(left,right);contrasts[(l,j)]=(-right,-left)
                    pairs.append(dict(scenario=s.name,cap=budget,A=METHODS[j],B=METHODS[l],A_only=int(d[0]),B_only=int(d[1]),lower=left,upper=right))
            for capslots in (2,250):
                slots=np.array([SLOTS.get(m,s.w+5) for m in METHODS])
                for riskcap in (.12,.6):
                    inner=np.flatnonzero((up[:,b,0]<=budget)&(up[:,b,2]<=riskcap)&(slots<=capslots))
                    outer=np.flatnonzero((lo[:,b,0]<=budget)&(lo[:,b,2]<=riskcap)&(slots<=capslots))
                    rec='' if not len(inner) else min(inner,key=lambda j:(up[j,b,2],slots[j],j))
                    if rec=='':
                        status='no feasible candidate' if len(outer)==0 else 'uncertain feasibility'
                        label='';gap=''
                    else:
                        rivals=[j for j in outer if j!=rec]
                        status='unique certified' if all(contrasts[rec,j][1]<0 for j in rivals) else 'ordering unresolved'
                        label=METHODS[rec]
                        gap=max([0]+[min(up[rec,b,2]-lo[j,b,2],contrasts[rec,j][1]) for j in rivals])
                    decisions.append(dict(scenario=s.name,fa_cap=budget,hazard_cap=riskcap,slot_cap=capslots,inner=','.join(METHODS[j] for j in inner),outer=','.join(METHODS[j] for j in outer),choice=label,status=status,excess_upper=gap))
        counts[s.name]=sr
        print(s.name,flush=True)
    write('coordinate_intervals.csv',rows);write('paired_intervals.csv',pairs);write('decisions.csv',decisions);write('thresholds.csv',thresholds)
    (HERE/'design.json').write_text(json.dumps(dict(seed=SEED,calibration=CAL_N,heldout_per_law=TEST_N,epochs=T,simultaneous_statements=number,scenarios=counts),indent=2))
    figures(rows,decisions)
def figures(rows,decisions):
    fig,ax=plt.subplots(figsize=(7.6,4.8),layout='constrained')
    colors=['#eeeeee','#caa53c','#218762','#356d9f','#8d5c8b']
    from matplotlib.colors import ListedColormap, BoundaryNorm
    arr=np.zeros((len(SCENARIOS),len(BUDGET)),dtype=int)
    for i,s in enumerate(SCENARIOS):
        for b,bd in enumerate(BUDGET):
            d=next(x for x in decisions if x['scenario']==s.name and x['fa_cap']==bd and x['slot_cap']==250 and x['hazard_cap']==.6)
            if d['choice']:arr[i,b]=1+METHODS.index(d['choice'])
            symbol=['--','S','C','G','R'][arr[i,b]]
            if d['status']=='unique certified':symbol+='*'
            ax.text(b,i,symbol,ha='center',va='center',color='black',weight='bold')
    ax.imshow(arr,cmap=ListedColormap(colors),norm=BoundaryNorm(np.arange(-.5,5,1),5),aspect='auto')
    ax.set(yticks=range(len(SCENARIOS)),yticklabels=[s.name for s in SCENARIOS],xticks=range(3),xticklabels=['0.005','0.020','0.080'],xlabel='Maximum healthy mission false-alarm probability')
    fig.savefig(HERE/'decision_map.pdf');plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(8.5,3.6),layout='constrained')
    for ax,scenario in zip(axes,['moderate persistent','brief pulse']):
        for m in METHODS:
            x=[r for r in rows if r['scenario']==scenario and r['method']==m]
            ax.plot([r['fa_up'] for r in x],[r['risk_up'] for r in x],'.-',label=m)
        ax.set(title=scenario,xlabel='False-alarm upper limit',ylabel='Hazard upper limit',xscale='log');ax.grid(alpha=.2)
    axes[1].legend(fontsize=8);fig.savefig(HERE/'tradeoff.pdf');plt.close(fig)
if __name__=='__main__':run()
