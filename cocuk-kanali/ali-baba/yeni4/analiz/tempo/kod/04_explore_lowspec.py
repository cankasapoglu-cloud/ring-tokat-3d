# Exploration: strongest spectral peaks 30-520 Hz in the sustain part of each beat (long FFT), verse 1 and verse 4,
# to see the real bass register and notes without assuming a pitch range.
import numpy as np, json, scipy.signal as ss, sys
from common import *
x=load_mix(); P,PHI=lattice()
fs=SR/20
y=ss.decimate(ss.decimate(x,5,ftype='fir',zero_phase=True),4,ftype='fir',zero_phase=True)
NF=1<<16; fr=np.fft.rfftfreq(NF,1/fs)
def nm(f): 
    m=69+12*np.log2(f/440); r=int(round(m)); return f"{NAMES[r%12]}{r//12-1}{100*(m-r):+.0f}"
def peaks(b,o0=0.08,o1=None,n=6,lo=30,hi=520):
    g=PHI+b*P; o1=P-0.02 if o1 is None else o1
    a=int((g+o0)*fs); e=int((g+o1)*fs); seg=y[a:e]*np.hanning(e-a)
    S=np.abs(np.fft.rfft(seg,NF)); m=(fr>=lo)&(fr<=hi)
    pk,_=ss.find_peaks(S[m],distance=int(4/(fr[1]-fr[0])))
    pk=pk[np.argsort(S[m][pk])[::-1][:n]]
    ref=S[m].max()
    return [(fr[m][k],20*np.log10(S[m][k]/ref)) for k in pk]
for vb in (15,87):
    for rel in list(range(-4,24)):
        b=vb+rel
        print(f"beat {b:3d} rel {rel:3d}: "+'  '.join(f"{nm(f):7s}({f:5.1f}Hz {d:+5.1f})" for f,d in peaks(b)))
    print()
