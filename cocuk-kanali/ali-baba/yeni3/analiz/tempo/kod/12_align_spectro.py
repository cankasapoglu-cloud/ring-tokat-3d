# Cross-check of the mix <-> vocal-stem lag with a vocal-specific measure:
# per-frequency-bin correlation of log-magnitude time derivatives, weighted by the stem's own energy
# (drums are broadband and are not selected by the stem-weighted bins).  Per verse and per line.
import numpy as np, json, scipy.signal as ss
from common import *
x=load_mix(); v=load_vocal(); n=min(len(x),len(v)); x=x[:n]; v=v[:n]
lines=json.load(open(O+'/lines_words.json'))
NF=1024; HP=16
def lspec(y,a,b):
    f,t,S=ss.stft(y[a:b],SR,window='hann',nperseg=NF,noverlap=NF-HP,boundary=None,padded=False)
    return f,np.abs(S)
out=[]
maxlag=int(0.02*SR/HP)
for L in lines:
    a=int((L['words'][0]['start']-0.1)*SR); b=int((L['words'][-1]['end']+0.1)*SR)
    f,Sm=lspec(x,a,b); f,Sv=lspec(v,a,b)
    band=(f>=200)&(f<=4000)
    Lm=np.log(Sm[band]+1e-3*Sm.max()); Lv=np.log(Sv[band]+1e-3*Sv.max())
    # derivative over ~3 ms (8 hops)
    d=8
    Dm=Lm[:,d:]-Lm[:,:-d]; Dv=Lv[:,d:]-Lv[:,:-d]
    W=(Sv[band][:,d:]>0.1*Sv[band].max())            # bins where the stem is strong
    Dv=Dv*W
    cs=[]
    for lag in range(-maxlag,maxlag+1):
        if lag>=0: p=(Dm[:,lag:]*Dv[:,:Dv.shape[1]-lag]).sum()
        else: p=(Dm[:,:lag]*Dv[:,-lag:]).sum()
        cs.append(p)
    cs=np.array(cs); k=int(np.argmax(cs)); dd=0.0
    if 0<k<len(cs)-1:
        y0,y1,y2=cs[k-1],cs[k],cs[k+1]; dd=0.5*(y0-y2)/(y0-2*y1+y2)
    lag_ms=(k-maxlag+dd)*HP/SR*1000
    out.append(dict(verse=L['verse'],line=L['line'],t=L['words'][0]['start'],lag_ms=float(lag_ms),peak_sharpness=float(cs[k]/(np.abs(cs).mean()+1e-9))))
    print(f"v{L['verse']} L{L['line']}: mix lags vocal by {lag_ms:+6.2f} ms (peak/mean {cs[k]/(np.abs(cs).mean()+1e-9):.1f})")
tt=np.array([o['t'] for o in out]); ll=np.array([o['lag_ms'] for o in out])
b,a=np.polyfit(tt,ll,1); res=ll-(a+b*tt)
print('per verse mean lag:',[round(float(np.mean([o['lag_ms'] for o in out if o['verse']==vi])),2) for vi in range(1,8)])
print('trend %.4f ms/s, intercept %.2f ms, residual sd %.2f ms; overall median %.2f ms'%(b,a,res.std(),np.median(ll)))
json.dump(dict(per_line=out,trend_ms_per_s=float(b),intercept_ms=float(a),residual_sd_ms=float(res.std()),median_ms=float(np.median(ll))),open(O+'/align_spectro.json','w'),indent=1)
