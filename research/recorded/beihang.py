"""Regenerate recorded-data diagnostics from BS.zip and the commit-pinned trajectory.
Usage: python beihang.py /path/to/BS.zip [--trajectory /path/to/trajectory_XYZ.mat]
Installs: numpy scipy matplotlib and either h5py or system libhdf5_serial(_hl).
"""
import argparse, csv, hashlib, io, tempfile, zipfile, urllib.request
from pathlib import Path
import numpy as np
from scipy.io import loadmat
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE=Path(__file__).resolve().parent
COMMIT="7b0517bbda1e3fe3dc4539729d22b8813067a7e9"
TRAJ_URL=f"https://raw.githubusercontent.com/BUAASatNav/the-BDS-Spoofing-Dataset-bs-/{COMMIT}/trajectory_XYZ.mat"

def read_mat(raw, key):
    f=io.BytesIO(raw)
    try: return loadmat(f,variable_names=[key])[key]
    except NotImplementedError: pass
    try:
        import h5py
        with h5py.File(io.BytesIO(raw),"r") as h: return np.asarray(h[key]).T
    except ImportError:
        # Minimal read-only alternative for the two known numeric rank-two datasets.
        import ctypes as c, ctypes.util as u
        h=c.CDLL(u.find_library("hdf5_serial")); hl=c.CDLL(u.find_library("hdf5_serial_hl"))
        hid=c.c_int64; ull=c.c_uint64
        h.H5Fopen.argtypes=[c.c_char_p,c.c_uint,hid];h.H5Fopen.restype=hid
        h.H5Fclose.argtypes=[hid]
        hl.H5LTget_dataset_ndims.argtypes=[hid,c.c_char_p,c.POINTER(c.c_int)]
        hl.H5LTget_dataset_info.argtypes=[hid,c.c_char_p,c.POINTER(ull),c.POINTER(c.c_int),c.POINTER(c.c_size_t)]
        hl.H5LTread_dataset_double.argtypes=[hid,c.c_char_p,c.POINTER(c.c_double)]
        with tempfile.NamedTemporaryFile() as t:
            t.write(raw);t.flush(); fd=h.H5Fopen(t.name.encode(),0,0)
            if fd<0: raise ValueError("unreadable HDF5")
            try:
                k=key.encode(); ndim=c.c_int()
                assert hl.H5LTget_dataset_ndims(fd,k,c.byref(ndim))>=0 and ndim.value==2
                dims=(ull*2)(); typ=c.c_int(); sz=c.c_size_t()
                assert hl.H5LTget_dataset_info(fd,k,dims,c.byref(typ),c.byref(sz))>=0
                arr=np.empty(tuple(dims),"float64")
                assert hl.H5LTread_dataset_double(fd,k,arr.ctypes.data_as(c.POINTER(c.c_double)))>=0
                return arr.T
            finally: h.H5Fclose(fd)

def write(name,fields,rows):
    with (HERE/name).open("w",newline="") as fp:
        writer=csv.writer(fp); writer.writerow(fields); writer.writerows(rows)
def main():
    p=argparse.ArgumentParser();p.add_argument("archive",type=Path);p.add_argument("--trajectory",type=Path)
    a=p.parse_args()
    raw=a.trajectory.read_bytes() if a.trajectory else urllib.request.urlopen(TRAJ_URL,timeout=30).read()
    trajectory=read_mat(raw,"trajectory")
    assert hashlib.sha256(raw).hexdigest()=="00dfd9012f24f2773a73374016abb47e0b865a6f838cdce5ca9d6f89411591d4"
    with zipfile.ZipFile(a.archive) as z:
        rows=[]
        for path in z.namelist():
            if path.endswith(".mat"):
                data=z.read(path);rows.append((path,len(data),hashlib.sha256(data).hexdigest()))
        write("inventory.csv",["archive_member","bytes","sha256"],rows)
        def arr(path,key):return read_mat(z.read("BaiduNetdisk/"+path),key)
        gps=arr("bs1/bdsData.mat","gpsData"); ue=arr("bs1/ueData.mat","ueData")
        five=arr("5gData/results_5G.mat","results_5G")
    assert gps.shape==(184,112) and ue.shape==(184,14)
    assert not gps[0].any()
    t=gps[1:,80]
    assert np.array_equal(t,np.arange(37.,220.))
    time=trajectory[:,0]
    def aligned(tags):
        idx=np.searchsorted(time,tags)
        # Times can differ from integer grid by a few floating point ulps.
        prev=np.maximum(idx-1,0)
        idx=np.where(np.abs(time[prev]-tags)<np.abs(time[idx]-tags),prev,idx)
        assert np.allclose(time[idx],tags,atol=1e-6,rtol=0)
        return trajectory[idx,1:4]
    err=np.linalg.norm(ue[1:,:3]-aligned(t),axis=1)
    write("bs1_error.csv",["record_s","3d_position_discrepancy_m"],zip(t,err))
    rows=[]
    for offset in (-1,0,1):
        alternative=np.linalg.norm(ue[1:,:3]-aligned(t+offset),axis=1)
        rows.append((offset,np.median(alternative[t<120]),np.max(alternative)))
    write("alignment.csv",["reference_time_offset_s","median_pre120_m","overall_peak_m"],rows)
    # Field inference: column 13 and its first difference match two published ACF values.
    from texbat import acf1, raw_alarms
    dv=np.diff(ue[1:,12]); dt=t[1:]; cal=(dt>=10)&(dt<80); test=dt>=120
    center=dv[cal].mean(); squared=(dv[test]-center)**2
    hits=raw_alarms((dv[cal]-center)**2,squared,dt[test])
    write("bs1_clock.csv",["calibration_scores","evaluation_scores","acf1_innovation","acf1_score","endpoint","cash","oga","restart"],
          [[cal.sum(),test.sum(),acf1(dv[test]),acf1(squared),*hits]])
    assert round(acf1(dv[test]),6)==.798078 and round(acf1(squared),6)==.654874
    assert hits==["silent"]*4
    # Data-driven breakpoints of the first crossing; no operational alert limit selected.
    envelope=[];previous=0.
    for time_i,mag in zip(t[t>=120],err[t>=120]):
        if mag>previous:
            envelope.append((previous,mag,time_i,time_i-121))
            previous=mag
    write("bs1_first_crossing.csv",["open_lower_limit_m","closed_upper_limit_m","first_at_or_above_s_from_t120","slack_to_reported_alarm_s"],envelope)
    errors=[]
    for station in (0,1):
        start=1+14*station
        truth=five[:,start+7]
        for signal,j in (("SSB",8),("PRS",9)):
            rms=np.sqrt(np.mean((five[:,start+j]-truth)**2))
            errors.append((station+1,signal,len(truth),rms))
    write("5g_rms.csv",["link","signal","epochs","rms_m"],errors)
    fig,ax=plt.subplots(figsize=(7.2,3.4),layout="constrained");ax.plot(t,err,color="#185883",lw=1.7)
    ax.axvline(120,ls=":",c="#812f2f",label="Manuscript evaluation start (120 s)")
    ax.set(xlabel="Record time (s)",ylabel="3-D discrepancy (m)",title="Beihang bs1 receiver and reference positions")
    ax.legend(frameon=False);ax.grid(axis="y",alpha=.2);fig.savefig(HERE/"bs1_error.pdf");plt.close(fig)
    assert np.isclose(err.max(),98.75106869,rtol=1e-7)
    assert t[err.argmax()]==170
    assert [round(x[-1],6) for x in errors]==[.010983,.002951,.013737,.007928]
    print("trajectory",hashlib.sha256(raw).hexdigest(),trajectory.shape)
    print("maximum at",t[err.argmax()],err.max(),"shifts",rows,"RMS",errors)
if __name__=="__main__":main()
