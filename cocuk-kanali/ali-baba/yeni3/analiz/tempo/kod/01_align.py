# Check that the decoded full mix and the isolated vocal share one timeline.
# Waveform correlation is unreliable for a separated stem (phase differs), so compare
# spectral-magnitude envelopes (vocal band 300-3400 Hz) at a fine hop and find the best lag.
import numpy as np, soundfile as sf, scipy.signal as ss, json
A='/home/user/ring-tokat-3d/cocuk-kanali/ali-baba'
O=A+'/yeni3/analiz/tempo'
m,sr=sf.read(O+'/mix_44k_mono.wav'); v,sr2=sf.read(A+'/dinle_2_vokal.wav')
assert sr==sr2
print('durations',len(m)/sr,len(v)/sr)
hop=32; nfft=1024
def spec(x):
    f,t,S=ss.stft(x,sr,nperseg=nfft,noverlap=nfft-hop,boundary=None,padded=False)
    return f,np.abs(S)
out=[]
for (a,b) in [(5,25),(30,50),(55,75),(80,100),(5,100)]:
    f,Sm=spec(m[a*sr:b*sr]); f,Sv=spec(v[a*sr:b*sr])
    band=(f>=300)&(f<=3400)
    # per-bin log-magnitude flux, summed -> onset envelope; plus per-band correlation
    em=np.maximum(0,np.diff(np.log1p(50*Sm[band]),axis=1)).sum(0)
    ev=np.maximum(0,np.diff(np.log1p(50*Sv[band]),axis=1)).sum(0)
    em-=em.mean(); ev-=ev.mean()
    c=ss.correlate(em,ev,mode='full',method='fft'); lags=ss.correlation_lags(len(em),len(ev))
    sel=np.abs(lags)<=int(0.2*sr/hop)
    k=np.argmax(c[sel]); lag=lags[sel][k]
    nc=c[sel][k]/np.sqrt((em**2).sum()*(ev**2).sum())
    print(f"win {a}-{b}s: mix lags vocal by {lag*hop} samples = {lag*hop/sr*1000:.2f} ms, norm corr {nc:.3f}")
    out.append(dict(win=[a,b],lag_ms=lag*hop/sr*1000,norm_corr=float(nc)))
json.dump(out,open(O+'/align_check.json','w'),indent=1)
