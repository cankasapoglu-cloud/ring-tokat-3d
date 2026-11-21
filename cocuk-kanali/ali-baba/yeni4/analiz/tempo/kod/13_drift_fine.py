# Fine drift check: does the beat lattice drift against an exact 105.000 BPM grid?
# For 10 s windows (hop 5 s) fold full-rate band envelopes over the beat period and locate the
# steepest rise near the expected attack (on-beat or off-beat). A linear trend of that position
# versus time = tempo correction.
import numpy as np, json, scipy.signal as ss
from common import *
x=load_mix(); BN=105.0; P0=60/BN; PHI=0.0
bands={'kick_40_120':(40,120,0.0),'low_120_300_on':(120,300,0.0),'mid_300_2000_on':(300,2000,0.0),'high_2k_8k_on':(2000,8000,0.0),'air_8k_16k_on':(8000,16000,0.0),
       'high_2k_8k_off':(2000,8000,0.5),'air_8k_16k_off':(8000,16000,0.5)}
def env_band(lo,hi,sm_ms=3.0):
    sos=ss.butter(4,[lo,hi],btype='band',fs=SR,output='sos'); y=ss.sosfiltfilt(sos,x)**2
    n=int(SR*sm_ms/1000); return np.sqrt(np.convolve(y,np.ones(n)/n,mode='same'))
res={}
wins=[(a,a+10.0) for a in np.arange(1.0,94.01,5.0)]
for name,(lo,hi,frac) in bands.items():
    e=env_band(lo,hi); pts=[]
    for (a,b) in wins:
        ia=int(a*SR); ib=int(b*SR); tt=np.arange(ia,ib)/SR; nbin=2286     # 0.25 ms bins
        ref=PHI+frac*P0
        idx=np.minimum((((tt-ref+P0/2)%P0)/P0*nbin).astype(int),nbin-1)
        prof=np.bincount(idx,weights=e[ia:ib],minlength=nbin)/np.maximum(np.bincount(idx,minlength=nbin),1)
        k=np.hanning(9); k/=k.sum(); prof=np.convolve(prof,k,mode='same')
        d=np.diff(prof); tb=(np.arange(1,nbin))/nbin*P0-P0/2
        m=np.abs(tb)<=0.05; kk=np.argmax(d[m]); pts.append(((a+b)/2,float(tb[m][kk])))
    tc=np.array([p[0] for p in pts]); dv=np.array([p[1] for p in pts])*1000
    sl,ic=np.polyfit(tc,dv,1); r=dv-(ic+sl*tc)
    ss_=[(dv[j]-dv[i])/(tc[j]-tc[i]) for i in range(len(tc)) for j in range(i+1,len(tc))]
    ts=float(np.median(ss_))
    res[name]=dict(dev_ms=[round(float(q),2) for q in dv],slope_ms_per_s=float(sl),theil_sen_slope_ms_per_s=ts,intercept_ms=float(ic),resid_sd_ms=float(r.std()),
                   implied_bpm=float(BN/(1+sl/1000)),implied_bpm_theil_sen=float(BN/(1+ts/1000)),mean_dev_ms=float(dv.mean()),median_dev_ms=float(np.median(dv)))
    print(f"{name:18s} dev(ms) {' '.join(f'{q:+5.1f}' for q in dv)} | slope {sl*1000:+.1f} us/s (TS {ts*1000:+.1f}) -> {BN/(1+ts/1000):.4f} BPM, resid sd {r.std():.2f} ms, mean {dv.mean():+.2f}")
res['window_centres_s']=[float((a+b)/2) for a,b in wins]
E_=np.load(CACHE+'/env.npz'); te,envA,envB,envC=E_['t'],E_['envA'],E_['envB'],E_['envC']
fine={}
for nm,env in (('A_fullband_flux',envA),('B_kick_lf',envB),('C_hats_8_16k_flux',envC)):
    best=(-1,0,0)
    for bpm in np.arange(104.95,105.0501,0.001):
        Pp=60/bpm; ph=8.0+np.arange(300)/300*Pp
        sc=[grid_score(env,te,Pp,p,8.0,100.0) for p in ph]; j=int(np.argmax(sc))
        if sc[j]>best[0]: best=(sc[j],bpm,ph[j])
    fine[nm]=dict(bpm=float(best[1]),score=float(best[0]/env[(te>8)&(te<100)].mean()))
    print('fine global search',nm,'-> %.3f BPM'%best[1])
res['fine_global_grid_search_step_0.001bpm']=fine
json.dump(res,open(O+'/drift_fine.json','w'),indent=1)
