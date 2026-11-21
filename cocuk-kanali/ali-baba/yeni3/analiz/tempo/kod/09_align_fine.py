# Fine check of the mix <-> isolated-vocal time alignment (does the stem share the mix timeline?).
#  (1) band-limited WAVEFORM cross-correlation in short vocal-dominated windows (sample accuracy if phase is kept)
#  (2) ENVELOPE cross-correlation (1 kHz-4 kHz band RMS, 0.18 ms hop) per sung line
import numpy as np, json, scipy.signal as ss
from common import *
x=load_mix(); v=load_vocal(); n=min(len(x),len(v)); x=x[:n]; v=v[:n]
lines=json.load(open(O+'/lines_words.json'))
sos=ss.butter(4,[250,3000],btype='band',fs=SR,output='sos')
xb=ss.sosfiltfilt(sos,x); vb=ss.sosfiltfilt(sos,v)
res=[]
print('(1) waveform correlation per line (band 250-3000 Hz), max |lag| 30 ms')
for L in lines:
    a=int(L['words'][0]['start']*SR); b=int(L['words'][-1]['end']*SR)
    X=xb[a:b]; V=vb[a:b]
    c=ss.correlate(X,V,mode='full',method='fft'); lags=ss.correlation_lags(len(X),len(V))
    sel=np.abs(lags)<=int(0.03*SR); cs=c[sel]/np.sqrt((X**2).sum()*(V**2).sum()); ls=lags[sel]
    k=np.argmax(np.abs(cs))
    res.append(dict(verse=L['verse'],line=L['line'],wave_lag_samples=int(ls[k]),wave_lag_ms=float(ls[k]/SR*1000),wave_corr=float(cs[k])))
    print(f"  v{L['verse']} L{L['line']}: lag {ls[k]:+5d} samples ({ls[k]/SR*1000:+6.2f} ms) corr {cs[k]:+.3f}  | corr at lag 0: {cs[ls==0][0]:+.3f}")
print('(2) envelope correlation per line (1-4 kHz RMS envelope, hop 8 samples)')
sos2=ss.butter(4,[1000,4000],btype='band',fs=SR,output='sos')
def envf(y):
    z=ss.sosfiltfilt(sos2,y)**2
    nwin=int(0.004*SR); e=np.sqrt(np.convolve(z,np.ones(nwin)/nwin,mode='same'))
    return e[::8]
ex=envf(x); evv=envf(v); hop=8
for i,L in enumerate(lines):
    a=int(L['words'][0]['start']*SR/hop)-int(0.1*SR/hop); b=int(L['words'][-1]['end']*SR/hop)+int(0.1*SR/hop)
    X=np.log(ex[a:b]+1e-4); V=np.log(evv[a:b]+1e-4); X=X-X.mean(); V=V-V.mean()
    c=ss.correlate(X,V,mode='full',method='fft'); lags=ss.correlation_lags(len(X),len(V))
    sel=np.abs(lags)<=int(0.03*SR/hop); cs=c[sel]/np.sqrt((X**2).sum()*(V**2).sum()); ls=lags[sel]
    k=int(np.argmax(cs))
    d=0.0
    if 0<k<len(cs)-1:
        y0,y1,y2=cs[k-1],cs[k],cs[k+1]; d=0.5*(y0-y2)/(y0-2*y1+y2)
    lag_ms=(ls[k]+d)*hop/SR*1000
    res[i].update(env_lag_ms=float(lag_ms),env_corr=float(cs[k]))
    print(f"  v{L['verse']} L{L['line']}: mix lags vocal by {lag_ms:+6.2f} ms, corr {cs[k]:.3f}")
wl=np.array([r['wave_lag_ms'] for r in res]); wc=np.array([abs(r['wave_corr']) for r in res]); el=np.array([r['env_lag_ms'] for r in res])
print('waveform: median lag %.2f ms, median |corr| %.3f ; envelope: median lag %.2f ms, IQR %.2f..%.2f'%(np.median(wl),np.median(wc),np.median(el),np.percentile(el,25),np.percentile(el,75)))
tm=np.array([L['words'][0]['start'] for L in lines])
print('envelope lag trend: %.4f ms per s, intercept %.2f ms'%tuple(np.polyfit(tm,el,1)))
gw=wc>0.3
if gw.sum()>3: print('waveform lag (corr>0.3) trend: %.5f ms per s, intercept %.2f ms, n=%d'%(*np.polyfit(tm[gw],wl[gw],1),gw.sum()))
json.dump(dict(per_line=res,wave_median_lag_ms=float(np.median(wl)),wave_median_abs_corr=float(np.median(wc)),env_median_lag_ms=float(np.median(el)),
               env_lag_trend_ms_per_s=float(np.polyfit(tm,el,1)[0])),open(O+'/align_check.json','w'),indent=1)
