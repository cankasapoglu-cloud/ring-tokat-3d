# Exploration: print envelope / flux traces of the vocal stem around line onsets (10 ms steps),
# to design an onset definition that also works for legato joins (L3 -> L4).
import numpy as np, json, sys, scipy.signal as ss
from common import *
v=load_vocal(); P=60/116.0; PHI=0.0015
lines=json.load(open(O+'/lines_words.json'))
def env(y,win_ms=10.0):
    n=int(SR*win_ms/1000); return np.sqrt(np.convolve(y**2,np.ones(n)/n,mode='same'))
sosv=ss.butter(4,[90,1200],btype='band',fs=SR,output='sos'); vv=ss.sosfiltfilt(sosv,v)
sosh=ss.butter(4,2500,btype='high',fs=SR,output='sos'); vh=ss.sosfiltfilt(sosh,v)
eb=20*np.log10(env(v)+1e-7); ev=20*np.log10(env(vv)+1e-7); eh=20*np.log10(env(vh)+1e-7)
# vocal spectral flux, 1024 window, hop 64 (1.45 ms)
f,t,S=stft_mag(v,1024,64)
fl=flux(S,f,90,8000); flv=flux(S,f,90,1200)
fl/=np.percentile(fl,99); flv/=np.percentile(flv,99)
sel=sys.argv[1:] 
for L in lines:
    key=f"{L['verse']}.{L['line']}"
    if sel and key not in sel and f"L{L['line']}" not in sel: continue
    t0=L['words'][0]['start']; nb=round((t0-PHI)/P); g=PHI+nb*P
    print(f"\nv{L['verse']} L{L['line']} {L['words'][0]['text']} word-start {t0:.2f} (rel grid {1000*(t0-g):+.0f} ms)")
    rel=np.arange(-150,121,10)
    def samp(e): return [e[int(round((g+r/1000)*SR))] for r in rel]
    def sampf(e): return [e[(t>=g+r/1000-0.005)&(t<g+r/1000+0.005)].max() for r in rel]
    print('  rel ms  '+' '.join(f"{r:5d}" for r in rel))
    print('  broad dB'+' '.join(f"{x:5.0f}" for x in samp(eb)))
    print('  voice dB'+' '.join(f"{x:5.0f}" for x in samp(ev)))
    print('  high  dB'+' '.join(f"{x:5.0f}" for x in samp(eh)))
    print('  flux    '+' '.join(f"{x:5.2f}" for x in sampf(fl)))
    print('  fluxLow '+' '.join(f"{x:5.2f}" for x in sampf(flv)))
