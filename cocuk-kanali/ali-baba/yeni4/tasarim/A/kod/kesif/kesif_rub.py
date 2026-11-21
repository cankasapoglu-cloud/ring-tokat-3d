# EXPLORATORY SCRIPT, kept as a record of what was run; superseded by the numbered scripts.
# where the measured rub of the chosen plan comes from; reads a rendered WAV in ara/ses (became the breakdown in 04_ses_olcumu.py, which now renders to a work folder)
# where does the rub above -6 dB come from in the chosen plan?  (exploration)
import sys, os, collections
sys.path.insert(0, '/home/user/ring-tokat-3d/cocuk-kanali/ali-baba/yeni4/tasarim/A/kod')
import numpy as np, soundfile as sf
from scipy.signal import butter, sosfiltfilt
from ortak import *
from olcut import Frames
from bant import Band, note_name
sr=44100
F=Frames(); band=Band('C')
x,_=sf.read(os.path.join(ARA,'ses','Ay_V-V-V-V_SECILEN.wav')); x=x[int(round(1.0*(int(round(60e6/105))/1e6)*sr))+82:].mean(axis=1)
def env(m):
    f=440*2**((m-69)/12); sos=butter(4,[f*2**(-1/24),f*2**(1/24)],btype='band',fs=sr,output='sos'); y=sosfiltfilt(sos,x)
    n=int(0.020*sr)|1; h=np.hanning(n+2)[1:-1]; h/=h.sum(); return np.sqrt(np.convolve(y**2,h,'same')*2)
E={m:env(m) for m in range(56,74)}
a=int(4.5*BEAT*sr); b=int(4.8*BEAT*sr); ref=E[64][a:b].max()
si=np.round((F.pos+4)*BEAT*sr).astype(int); nf=np.round(F.note_midi).astype(int)
lo=np.array([E[n-1][i] for n,i in zip(nf,si)]); hi=np.array([E[n+1][i] for n,i in zip(nf,si)])
rub=10*np.log10((lo**2+hi**2)/ref**2+1e-12)
bar=np.floor(F.pos/4+1e-9).astype(int); bt=F.pos-4*bar
cnt=collections.Counter(); tot=collections.Counter()
for k in range(F.n):
    key=(bar[k], round(np.floor(bt[k]*2)/2,1), NOTE[nf[k]%12])
    tot[key]+=1
    if rub[k]>-6: cnt[(key, 'lower' if lo[k]>hi[k] else 'upper')]+=1
kinds=['voc','voc','voc','slot','slot','fillin','voc','voc']
plan8=[['I','IV','I','I'],['I','V7','I','I'],['V']*4,['I']*4,['I']*4,['I']*4,['V']*4,['I','V7','I','I']]
print('frames above -6 dB: %.1f%%' % (100*np.mean(rub>-6)))
for (key,side),c in sorted(cnt.items(), key=lambda q:-q[1])[:22]:
    b_,q,nm=key
    ev=[note_name(n) for (t0,d,ch,n,v) in band.bar(kinds[b_],plan8[b_]) if t0 < q+0.5 and t0+d > q]
    print('bar %d beat %.1f sung %s: %4d of %4d frames above -6 dB (%s neighbour)  band notes sounding: %s' % (b_,q,nm,c,tot[key],side,' '.join(sorted(set(ev)))))
