"""Defensive replay evaluation. Source tuples are authenticated by SHA-256.
Run companion beihang.py and texbat.py first. Input files are not redistributed.
"""
import argparse
import csv
import hashlib
from pathlib import Path
import urllib.request
import zipfile

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.io import loadmat

from beihang import read_mat, write, HERE
from texbat import START, URL, raw_alarms

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def receiver_seconds(channel, nav):
    valid = channel[:,2] == nav[0, 0]
    rows = channel[valid]
    ort = rows[:,3] + rows[:,4]
    rrt = rows[:,0] * 604800. + rows[:,1]
    offsets = ort - rrt
    if np.ptp(offsets) > 1e-7 or not np.all(nav[:,0] == nav[0, 0]):
        raise ValueError("requires piecewise alignment across weeks or clock jumps")
    return nav[:,1] + nav[:,2] - np.median(offsets), np.ptp(offsets)

def texas(cache):
    clocks=[]; sensitivity=[]; channels=[]
    with (HERE/"texbat_files.csv").open() as fp:
        expected={row["record"]:row["sha256"] for row in csv.DictReader(fp)}
    with (HERE/"channel_files.csv").open() as fp:
        expected_channel = {row["record"]:row["sha256"] for row in csv.DictReader(fp)}
    for name, start in START.items():
        navpath=cache/(name+".mat")
        assert digest(navpath)==expected[name]
        chpath=cache/(name+"_channel.mat")
        url=URL+name+"/channel.mat"
        if not chpath.exists():
            with urllib.request.urlopen(url,timeout=60) as src: chpath.write_bytes(src.read())
        observed = digest(chpath)
        if observed != expected_channel[name]:
            raise ValueError(f"{name}: channel data differs from the archived source")
        channels.append([name,url,observed])
        nav=loadmat(navpath)["navsol"].T; ch=loadmat(chpath)["channel"].T
        rr,span=receiver_seconds(ch,nav)
        # RRT coverage and exact match for first nav observation to a channel epoch.
        first_ort = nav[0,1]+nav[0,2]
        good=ch[ch[:,2]==nav[0,0]]
        assert np.min(np.abs(good[:,3]+good[:,4]-first_ort)) < 1e-8
        elapsed=rr-rr[0]
        epochs=np.arange(int(round(elapsed[-1]))+1)
        idx=np.abs(elapsed[:,None]-epochs).argmin(axis=0)
        dif=np.diff(nav[idx,6]); t=epochs[1:]
        for policy, shift, begin, end in [
            ("historical",0,start,t[-1]),("shifted",1,start,t[-1]),
            ("common",0,110,410),("common_shifted",1,110,410)]:
            ref=dif[(t>=20+shift)&(t<100+shift)]
            keep=(t>=begin)&(t<=end)
            hits=raw_alarms((ref-ref.mean())**2,(dif[keep]-ref.mean())**2,t[keep])
            sensitivity.append([name,policy,20+shift,99+shift,begin,end,*hits])
            if policy=="historical":
                rtime=[round(rr[idx[h]],6) if isinstance(h,int) else "silent" for h in hits]
                clocks.append([name,rr[0],span,rr[idx[begin]],*rtime])
    write("rrt.csv",["record","first_nav_rrt_s","time_offset_range_s","activation_native_rrt_s",
                      "endpoint_rrt_s","cash_rrt_s","adaptive_rrt_s","restart_rrt_s"],clocks)
    write("time_sensitivity.csv",["record","policy","ref_begin","ref_end_inclusive","activate","last_epoch",
                                  "endpoint","cash","adaptive","restart"],sensitivity)
    write("channel_files.csv",["record","url","sha256"],channels)
    assert np.allclose([r[1] for r in clocks],[33.00055317,36.00063277,36.80022943,33.00055317],atol=1e-7,rtol=0)

def frames(archive,trajpath):
    with zipfile.ZipFile(archive) as z:
        ue=read_mat(z.read("BaiduNetdisk/bs1/ueData.mat"),"ueData")[1:]
    tr=read_mat(trajpath.read_bytes(),"trajectory")
    t=np.arange(37,220)
    phi,lam=np.deg2rad(ue[:,3:5]).T
    sl,cl,sp,cp=np.sin(lam),np.cos(lam),np.sin(phi),np.cos(phi)
    invf=298.257223563; ecc=1-(1-1/invf)**2
    normal=6378137/np.sqrt(1-ecc*sp**2); height=ue[:,5]
    rebuilt=np.column_stack(((normal+height)*cp*cl,(normal+height)*cp*sl,((1-ecc)*normal+height)*sp))
    ex,ey,ez=ue[:,6:9].T
    enu=np.column_stack((-sl*ex+cl*ey,-sp*cl*ex-sp*sl*ey+cp*ez,cp*cl*ex+cp*sl*ey+sp*ez))
    # Independent central secant of the published XYZ truth over the 2 s window.
    ix1=(t+1)*200;ix0=(t-1)*200
    assert np.allclose(tr[ix1,0],t+1,rtol=0,atol=1e-8) and np.allclose(tr[ix0,0],t-1,rtol=0,atol=1e-8)
    vel=(tr[ix1,1:4]-tr[ix0,1:4])/(tr[ix1,0]-tr[ix0,0])[:,None]
    pe=np.linalg.norm(rebuilt-ue[:,:3],axis=1); ve=np.linalg.norm(enu-ue[:,9:12],axis=1)
    vtrue=np.linalg.norm(ue[:,6:9]-vel,axis=1)
    write("field_checks.csv",["quantity","units","value"],[("max_xyz_from_llh","m",max(pe)),("max_enu_from_ecef","m/s",max(ve)),
                  ("median_pre120_velocity_secant_discrepancy","m/s",np.median(vtrue[t<120])),
                  ("max_velocity_secant_discrepancy","m/s",max(vtrue))])
    assert max(pe)<.00012 and max(ve)<1e-10
    err=np.linalg.norm(ue[:,:3]-tr[t*200,1:4],axis=1)
    limits=np.unique(np.r_[0.01,np.geomspace(.02,120,301),err[t>=120]])
    margin=np.full(len(limits),np.nan)
    for i,h in enumerate(limits):
        crosses=t[(t>=120)&(err>=h)]
        if len(crosses):margin[i]=crosses[0]-121
    fig,ax=plt.subplots(2,1,figsize=(6.4,5.2),layout="constrained")
    ax[0].plot(t,err,color="#184f78");ax[0].axvline(121,ls="--",color="#8d4025",label="Reported AR alarm (121 s)")
    ax[0].set(xlabel="Replay epoch (s)",ylabel="3-D discrepancy (m)");ax[0].legend(fontsize=8)
    ax[1].step(limits,margin,where="pre",color="#184f78")
    ax[1].axhline(0,color="black",lw=.7);ax[1].axvspan(err.max(),120,color=".9")
    ax[1].text(109,22,"No\ncrossing",ha="center",fontsize=8)
    ax[1].set(xlabel="Candidate position-error limit (m)",ylabel="Observed margin (s)",xlim=(0,120))
    for a in ax:a.grid(axis="y",alpha=.2)
    fig.savefig(HERE/"field_margin.pdf");plt.close(fig)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--cache",required=True,type=Path)
    p.add_argument("--archive",required=True,type=Path)
    p.add_argument("--trajectory",required=True,type=Path)
    args=p.parse_args()
    texas(args.cache);frames(args.archive,args.trajectory)
