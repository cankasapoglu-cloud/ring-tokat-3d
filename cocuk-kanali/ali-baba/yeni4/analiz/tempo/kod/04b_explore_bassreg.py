# Exploration: peaks 30-200 Hz per beat (two halves) to find the bass register; mean spectrum of the song body 30-200 Hz.
import numpy as np, scipy.signal as ss
from common import *
x=load_mix(); P,PHI=lattice()
fs=SR/40
y=ss.decimate(ss.decimate(x,8,ftype='fir',zero_phase=True),5,ftype='fir',zero_phase=True)
NF=1<<15; fr=np.fft.rfftfreq(NF,1/fs)
def nm(f):
    m=69+12*np.log2(f/440); r=int(round(m)); return f"{NAMES[r%12]}{r//12-1}{100*(m-r):+.0f}"
def spec(t0,t1):
    a=int(t0*fs); e=int(t1*fs); seg=y[a:e]*np.hanning(e-a); return np.abs(np.fft.rfft(seg,NF))
def peaks(S,n=5,lo=30,hi=200):
    m=(fr>=lo)&(fr<=hi); pk,_=ss.find_peaks(S[m],distance=int(3/(fr[1]-fr[0]))); pk=pk[np.argsort(S[m][pk])[::-1][:n]]; ref=S[m].max()
    return '  '.join(f"{nm(fr[m][k]):7s}({fr[m][k]:5.1f} {20*np.log10(S[m][k]/ref):+5.1f})" for k in pk)
# long-term spectrum of the body
acc=np.zeros(len(fr)); n=0
for b in range(15,180):
    g=PHI+b*P; acc+=spec(g+0.12,g+P-0.02)**2; n+=1
acc=np.sqrt(acc/n)
print('long-term (beats 15..179, sustain part) peaks 30-200 Hz:',peaks(acc,10))
for vb in (15,87):
    for rel in range(0,24):
        g=PHI+(vb+rel)*P
        print(f"beat {vb+rel:3d} rel {rel:2d}: 1st half: {peaks(spec(g+0.10,g+P/2+0.02),4)}   || 2nd half: {peaks(spec(g+P/2,g+P-0.01),3)}")
    print()
