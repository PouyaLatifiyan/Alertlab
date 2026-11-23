"""Independent clock-bias replay from four public UT GRID navigation solutions.
python texbat.py [--cache directory] 
A verified upstream data file is downloaded when absent in cache. The elapsed
time axis is measured from that file's first valid receiver solution.
"""
import argparse
import csv
import hashlib
import io
import tempfile
import urllib.request
from pathlib import Path
import numpy as np
from scipy.io import loadmat
from beihang import HERE, write

URL="https://rnl-data.ae.utexas.edu/datastore/texbat/processed/"
START={"cleanStatic":110,"ds2":115,"ds3":115,"ds7":150}
def acf1(x):
    z=x-x.mean()
    return z[:-1]@z[1:]/(z@z)
def raw_alarms(r,x,eval_t):
    q=(r[:,None]>=x).mean(axis=0)
    endpoint=(1-q)/(.5+np.sqrt(np.log(2000)/(2*len(r))))
    hits=[]
    for eta in (1.,.5):
        hit=np.flatnonzero(np.cumprod(1+eta*(endpoint-1))>=1000)
        hits.append(int(eval_t[hit[0]]) if len(hit) else "silent")
    eta=0.; wealth=1.; active=np.zeros(5); starts=len(range(0,len(q),25))
    fractions=np.array([.1,.25,.5,.75,.9]); eps=np.sqrt(np.log(2000)/(2*len(r)))
    c=np.mean(np.greater_equal.outer(r,r)); scale=max(c,1-c)+eps
    oga="silent"; restart="silent"
    for j,survival in enumerate(q):
        b=1+(eta*(c-survival)-abs(eta)*eps)/scale
        wealth*=b
        eta=np.clip(eta+.5*(c-survival-np.sign(eta)*eps)/(scale*b*np.sqrt(j+1)),-.95,.95)
        if wealth>=1000 and oga=="silent":oga=int(eval_t[j])
        if j%25==0:active+=1
        active*=1+fractions*(endpoint[j]-1)
        value=(active.mean()+starts-1-j//25)/starts
        if value>=1000 and restart=="silent":restart=int(eval_t[j])
    hits.extend([oga,restart])
    return hits

def run(cache):
    rows=[]; files=[]
    with (HERE/"texbat_files.csv").open() as f:
        expected = {row["record"]: row["sha256"] for row in csv.DictReader(f)}
    for name,start in START.items():
        url=URL+name+"/navsol.mat"
        path=cache/(name+".mat")
        if not path.exists():
            with urllib.request.urlopen(url,timeout=45) as f:path.write_bytes(f.read())
        b=path.read_bytes()
        if hashlib.sha256(b).hexdigest() != expected[name]:
            raise ValueError(f"{name}: navigation solution differs from the archived source")
        a=loadmat(io.BytesIO(b))["navsol"].T
        assert a.shape[1]>=12 and np.all(a[:,11]==2)
        ort=a[:,1]+a[:,2]; elapsed=ort-ort[0]
        ep=np.arange(int(round(elapsed[-1]))+1)
        idx=np.abs(elapsed[:,None]-ep).argmin(axis=0)
        assert np.max(np.abs(elapsed[idx]-ep))<.5
        dif=np.diff(a[idx,6]);t=ep[1:]
        ref=dif[(t>=20)&(t<100)]
        use=t>=start; eval_t=t[use]; obs=dif[use]
        center=ref.mean()
        r=(ref-center)**2; x=(obs-center)**2
        hits=raw_alarms(r,x,eval_t)
        rows.append([name,len(a),float(ort[0]),int(ep[-1]),len(ref),start,acf1(obs),acf1(x),*hits])
        files.append([name,url,hashlib.sha256(b).hexdigest()])
    write("texbat_clock.csv",["record","native_rows","first_ORT_s_of_week","last_elapsed_epoch_s","reference_differences","start_elapsed_s","acf1_differences","acf1_squared_centered","endpoint_alarm_elapsed_s","cash_0.5_alarm_elapsed_s","oga_alarm_elapsed_s","restart_alarm_elapsed_s"],rows)
    write("texbat_files.csv",["record","upstream_navsol_url","sha256"],files)
    assert rows[1][-4:-2]==[136,154] and rows[-1][-4:-2]==[395,392]
    print(rows)
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--cache",type=Path);a=p.parse_args()
    if a.cache:
        a.cache.mkdir(exist_ok=True,parents=True);run(a.cache)
    else:
        with tempfile.TemporaryDirectory() as d:run(Path(d))
