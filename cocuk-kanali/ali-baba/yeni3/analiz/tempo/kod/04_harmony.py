# Exploration for the downbeat question: per-beat bass note and chord (chroma) of the accompaniment.
# Accompaniment magnitude is approximated by spectral subtraction |mix| - |vocal| (>=0).
import numpy as np, json, scipy.signal as ss
from common import *
x=load_mix(); v=load_vocal()
n=min(len(x),len(v)); x=x[:n]; v=v[:n]
NF=8192; HP=512
f,t,Sm=stft_mag(x,NF,HP); _,_,Sv=stft_mag(v,NF,HP)
Sa=np.maximum(Sm-1.0*Sv,0)
P=60/116.0; PH=0.0047
names=['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
words=load_words()
def midi_of(fr): return 69+12*np.log2(fr/440.0)
# bass salience: pitches 28..55, harmonic sum over h=1..4
def bass_pitch(spec):
    best=[]
    for m in range(28,56):
        f0=440*2**((m-69)/12); s=0
        for h,wt in ((1,1.0),(2,0.8),(3,0.5),(4,0.3)):
            fh=f0*h
            lo=fh*2**(-0.4/12); hi=fh*2**(0.4/12)
            band=(f>=lo)&(f<=hi)
            if band.any(): s+=wt*spec[band].max()
        best.append(s)
    best=np.array(best)
    return 28+int(best.argmax()),best
def chroma(spec,lo=200,hi=2000):
    c=np.zeros(12)
    band=(f>=lo)&(f<=hi)
    m=midi_of(f[band]); pc=np.round(m).astype(int)%12
    dev=np.abs(m-np.round(m))
    w=np.cos(np.pi*dev)**2
    np.add.at(c,pc,spec[band]**2*w)
    return c/(c.sum()+1e-12)
def chord(c):
    best=(-1,'')
    res=[]
    for r in range(12):
        for q,iv in (('',(0,4,7)),('m',(0,3,7))):
            tpl=np.zeros(12); tpl[[(r+i)%12 for i in iv]]=1
            s=float((c*tpl).sum()); res.append((s,names[r]+q))
    res.sort(reverse=True)
    return res[:2]
nb=int((t[-1]-PH)/P)
rows=[]
for b in range(nb):
    g=PH+b*P
    m=(t>=g+0.02)&(t<g+P-0.02)
    sa=Sa[:,m].mean(1); sm=Sm[:,m].mean(1)
    # bass from first half of the beat (the "oom")
    m1=(t>=g+0.0)&(t<g+P*0.5)
    bp,sal=bass_pitch(Sm[:,m1].mean(1))
    m2=(t>=g+P*0.5)&(t<g+P)
    bp2,_=bass_pitch(Sm[:,m2].mean(1))
    c=chroma(sa); ch=chord(c)
    rows.append(dict(beat=b,t=g,bass=bp,bass2=bp2,chroma=c.tolist(),chord=ch[0][1],chord_s=ch[0][0],chord2=ch[1][1],chord2_s=ch[1][0]))
def wordat(g):
    s=''
    for w in words:
        if g-P/4<=w['start']<g+3*P/4: s+=w['text']+' '
    return s
for r in rows:
    print(f"{r['beat']:4d} {r['t']:7.3f} bass {names[r['bass']%12]:2s}{r['bass']//12-1} /{names[r['bass2']%12]:2s}{r['bass2']//12-1}  chord {r['chord']:3s} {r['chord_s']:.2f} ({r['chord2']:3s} {r['chord2_s']:.2f})  top3pc {' '.join(names[i] for i in np.argsort(r['chroma'])[::-1][:3]):9s} {wordat(r['t'])}")
json.dump(rows,open(CACHE+'/beat_harmony_explore.json','w'))
