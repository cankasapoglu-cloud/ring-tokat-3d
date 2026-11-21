import numpy as np, wave, json, sys
S,O=sys.argv[1:3]
def rd(p):
    w=wave.open(p); return np.frombuffer(w.readframes(w.getnframes()),dtype=np.int16).reshape(-1,2).astype(np.float64)/32768
m=json.load(open(S+'/meta.json')); BEAT=m['BEAT']; BAR=m['BAR']; INTRO=m['INTRO']; VB=m['VB']; sr=44100
a=rd(O+'/altyapi.wav'); r=rd(O+'/rehber.wav')
db=lambda v:20*np.log10(v+1e-12)
print('dur',round(len(a)/sr,3),round(len(r)/sr,3),'peak dBFS',round(db(abs(a).max()),2),round(db(abs(r).max()),2),'samples>=0.999',(abs(a)>=0.999).sum(),(abs(r)>=0.999).sum())
for c,n in zip([0,1,2,3,4,5,6,9,7],['bass','banjo','accordion','piano','glock','trumpet','brass sect','drums','guide(clarinet)']):
    x=rd(f'{S}/st{c}.wav').mean(1); x=x[int(INTRO*BAR*sr):int((INTRO+2*VB)*BAR*sr)]
    print(f'stem {n:16s} rms {db(np.sqrt((x**2).mean())):6.1f} dB (raw, verses 1-2)')
def pitch(x,lo,hi):
    x=x*np.hanning(len(x)); X=abs(np.fft.rfft(x,1<<16)); best=None
    for f0 in np.arange(lo,hi,0.5):
        s=sum(X[int(round(h*f0*(1<<16)/sr))]/h for h in (1,2,3,4))
        if best is None or s>best[0]: best=(s,f0)
    return 69+12*np.log2(best[1]/440)
g=rd(S+'/st7.wav').mean(1)   # guide stem (the mastered files are limited, so rehber-altyapi is no longer the pure guide)
d=(r-a).mean(1)
bad=0; mx=0; bad2=0
for (k,ln,s,n,midi,b,dur) in m['guide']:
    t0=b*BEAT; i0=int((t0+0.04)*sr); i1=int((t0+max(0.19,dur*BEAT*0.85))*sr)
    p=pitch(g[i0:i1],220,520); err=abs(p-midi); mx=max(mx,err)
    if err>0.3: bad+=1; print('BAD stem',k,ln,s,n,p)
    p2=pitch(d[i0:i1],220,520)
    if abs(p2-midi)>0.3: bad2+=1
print(f'guide notes checked {len(m["guide"])}: bad on guide stem {bad} (max err {mx:.2f} st); bad on mastered rehber-altyapi difference {bad2}')
tp=rd(S+'/st5.wav').mean(1); gl=rd(S+'/st4.wav').mean(1); bt=bg=0
for bb,T in m['ans']:
    for i,exp in enumerate([71,71,69,69,67]):
        t0=(bb*4+(i*.5 if i<4 else 2))*BEAT
        p=pitch(tp[int((t0+0.04)*sr):int((t0+0.19)*sr)],300,700)
        if abs(p-exp-T)>0.4: bt+=1; print('BAD tpt',bb,i,p,exp+T)
        seg=gl[int((t0+0.01)*sr):int((t0+0.19)*sr)]; X=abs(np.fft.rfft(seg*np.hanning(len(seg)),1<<16)); F=np.fft.rfftfreq(1<<16,1/sr); X[(F<650)|(F>1400)]=0; f=F[np.argmax(X)]
        p=69+12*np.log2(f/440)
        if abs(p-exp-12-T)>0.4: bg+=1; print('BAD glk',bb,i,p,exp+12+T)
print('answer notes checked',len(m['ans'])*5,'trumpet bad',bt,'glock bad',bg)
am=a.mean(1)
def rms(t0,t1): x=am[int(t0*sr):int(t1*sr)]; return db(np.sqrt((x**2).mean()))
print('per-bar RMS dB of altyapi per verse (bars 7-8 = slot)')
for k in range(m['NV']):
    v0=(INTRO+VB*k)*BAR
    print(k+1,' '.join(f'{rms(v0+i*BAR,v0+(i+1)*BAR):6.1f}' for i in range(VB)))
