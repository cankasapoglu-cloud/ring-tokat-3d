import numpy as np, wave, json, sys
S,O=sys.argv[1:3]
def rd(p):
    w=wave.open(p); return np.frombuffer(w.readframes(w.getnframes()),dtype=np.int16).reshape(-1,2).astype(np.float64)/32768
m=json.load(open(S+'/meta.json')); BEAT=m['BEAT']; BAR=m['BAR']; sr=44100
a=rd(O+'/altyapi.wav'); r=rd(O+'/rehber.wav')
db=lambda v:20*np.log10(v+1e-12)
print('dur',len(a)/sr,len(r)/sr,'peak dBFS',db(abs(a).max()),db(abs(r).max()),'samples>=0.999',(abs(a)>=0.999).sum(),(abs(r)>=0.999).sum())
for c,n in zip([0,1,2,3,4,5,9,6],['bass','banjo','accordion','piano','glock','flute','drums','guide(clarinet)']):
    x=rd(f'{S}/st{c}.wav').mean(1); x=x[int(4*BAR*sr):int(24*BAR*sr)]
    print(f'stem {n:16s} rms {db(np.sqrt((x**2).mean())):6.1f} dB (raw, verses 1-2)')
def pitch(x,lo=150,hi=1200):
    x=x*np.hanning(len(x)); X=abs(np.fft.rfft(x,1<<16)); f=np.fft.rfftfreq(1<<16,1/sr)
    # harmonic product spectrum-ish: pick f0 maximising sum of first 4 harmonics
    best=None
    for f0 in np.arange(lo,hi,0.5):
        s=sum(X[int(round(h*f0*(1<<16)/sr))]/h for h in (1,2,3,4))
        if best is None or s>best[0]: best=(s,f0)
    f0=best[1]; return 69+12*np.log2(f0/440)
d=(r-a).mean(1)
bad=0; mx=0
for (k,ln,s,n,b,dur) in m['guide']:
    t0=b*BEAT; seg=d[int((t0+0.04)*sr):int((t0+max(0.2,dur*BEAT*0.85))*sr)]
    p=pitch(seg,220,480); exp={'D4':62,'E4':64,'G4':67}[n]
    # onset: energy before vs after
    pre=np.sqrt((d[int((t0-0.03)*sr):int(t0*sr)]**2).mean()); post=np.sqrt((d[int((t0+0.03)*sr):int((t0+0.1)*sr)]**2).mean())
    err=abs(p-exp); mx=max(mx,err)
    if err>0.3 or post<1e-3: bad+=1; print('BAD',k,ln,s,n,p,post)
print(f'guide notes checked {len(m["guide"])}, bad {bad}, max pitch error {mx:.2f} semitones (rehber-altyapi difference signal)')
L=rd(S+'/lead_raw.wav').mean(1); bad=0
for bb in m['ans_bars']:
    for i,exp in enumerate([83,83,81,81,79]):
        t0=(bb*4+(i*.5 if i<4 else 2))*BEAT; seg=L[int((t0+0.02)*sr):int((t0+0.2)*sr)]
        p=pitch(seg,400,1300)
        if abs(p-exp)>0.4: bad+=1; print('BAD ans',bb,i,p,exp)
print('answer notes checked',len(m['ans_bars'])*5,'bad',bad)
am=a.mean(1)
def rms(t0,t1): x=am[int(t0*sr):int(t1*sr)]; return db(np.sqrt((x**2).mean()))
print('verse: per-bar RMS dB of altyapi (bar7 = slot)')
for k in range(7):
    v0=(4+10*k)*BAR
    print(k+1,' '.join(f'{rms(v0+i*BAR,v0+(i+1)*BAR):6.1f}' for i in range(10)))
def envl(x): n=len(x)//2205; return np.sqrt((x[:n*2205].reshape(n,2205)**2).mean(1))
v=[am[int(round((4+10*k)*BAR*sr)):int(round((4+10*k)*BAR*sr))+int(10*BAR*sr)] for k in range(7)]
print('verse-to-verse 50ms-envelope correlation with verse 1:',[round(float(np.corrcoef(envl(v[0]),envl(x))[0,1]),4) for x in v[1:]])
