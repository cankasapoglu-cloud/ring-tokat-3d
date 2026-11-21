# Checks on tempo.json by independent re-measurement (no listening possible).
import numpy as np, json, scipy.signal as ss
from common import *
T=json.load(open(O+'/tempo.json')); L=T['lines']; S=T['summary']
ok=True
def check(name,cond,info=''):
    global ok; ok&=bool(cond); print(('PASS ' if cond else 'FAIL ')+name+(' | '+info if info else ''))
# 1 coverage
check('28 lines, verses 1..7 x lines 1..4',sorted((r['verse'],r['line']) for r in L)==[(v,l) for v in range(1,8) for l in range(1,5)])
# 2 bar spacing inside verses
bp=S['beat_sec']
d=[L[i+1]['downbeat']-L[i]['downbeat'] for i in range(27) if L[i]['verse']==L[i+1]['verse']]
check('downbeats inside a verse are exactly 4 beats apart',max(abs(q-4*bp) for q in d)<0.0006,f"max dev {1000*max(abs(q-4*bp) for q in d):.2f} ms")
# 3 no line is a pickup
ob=np.array([r['offset_beats'] for r in L]); vb=np.array([r['vowel_offset_beats'] for r in L])
check('all acoustic onsets within +-0.125 beat of the downbeat',np.abs(ob).max()<0.125,f"range {ob.min():+.3f}..{ob.max():+.3f} beats, median {np.median(ob):+.3f}")
check('all vowel onsets within +-0.125 beat of the downbeat',np.abs(vb).max()<0.125,f"range {vb.min():+.3f}..{vb.max():+.3f} beats, median {np.median(vb):+.3f}")
check('reported typical offset equals the median of the 28 offsets',abs(S['typical_offset_beats']-np.median(ob))<1e-3)
# 4 independent beat detection in the mix: pick kick-band rise peaks, regress on beat index
x=load_mix()
sos=ss.butter(4,[120,300],btype='band',fs=SR,output='sos'); y=ss.sosfiltfilt(sos,x)**2
n=int(0.003*SR); e=np.sqrt(np.convolve(y,np.ones(n)/n,mode='same')); de=np.diff(e,prepend=e[0]); de=np.convolve(de,np.hanning(89)/np.hanning(89).sum(),mode='same')
pk,_=ss.find_peaks(de,distance=int(0.3*SR),height=0.3*np.percentile(de,99.9))
tp=pk/SR; tp=tp[(tp>6)&(tp<100)]
P0=0.5172; idx=np.round((tp-tp[0])/P0)
keep=np.abs((tp-tp[0])-idx*P0)<0.06
A=np.vstack([idx[keep],np.ones(keep.sum())]).T; (p,c),res,_,_=np.linalg.lstsq(A,tp[keep],rcond=None)
r=tp[keep]-A@np.array([p,c])
bpm_ind=60/p; lat=T['tempo']['refined_lattice_mix_timeline']
check('independent kick/bass-attack regression gives the same tempo',abs(bpm_ind-lat['bpm'])<0.01,f"{bpm_ind:.4f} BPM from {keep.sum()} attacks (residual sd {1000*r.std():.1f} ms) vs lattice {lat['bpm']:.4f}")
ph_ind=(c-idx[keep][0]*0)  # time of the first used attack
dph=((c-lat['phase_first_beat_s']+p/2)%p)-p/2
check('its phase agrees with the lattice (low-band attack is a few ms after the hat transient)',-2e-3<dph<15e-3,f"low-band attack minus lattice {1000*dph:+.1f} ms")
# 5 a drum hit at every reported downbeat (single events, mix timeline)
dv=[]
for rr in L:
    g=rr['downbeat_mix_timeline']; a=int((g-0.04)*SR); b=int((g+0.04)*SR); k=a+int(np.argmax(de[a:b])); dv.append((k/SR-g)*1000)
dv=np.array(dv)
check('low-band attack found within -10..+20 ms of at least 26 of the 28 downbeats',((dv>-10)&(dv<20)).sum()>=26,f"mean {dv.mean():+.1f} ms, sd {dv.std():.1f}, outside: {[(L[i]['verse'],L[i]['line'],round(float(dv[i]),1)) for i in range(28) if not -10<dv[i]<20]}")
# 6 comb test for the half-beat decision
E=np.load(CACHE+'/env.npz'); te,envB=E['t'],E['envB']
g=lat['phase_first_beat_s']+np.arange(12,195)*lat['beat_period_s']
on=np.interp(g+0.004,te,envB).mean(); off=np.interp(g+0.004+lat['beat_period_s']/2,te,envB).mean()
check('kick envelope is concentrated on the lattice, not half a beat later',on>3*off,f"on/off = {on/off:.1f}")
# 7 onsets agree with the words file within its 20 ms resolution + typical alignment error
dw=np.array([r['onset']-r['word_start_from_words_file'] for r in L])
check('refined onsets stay within 60 ms of the word timestamps',np.abs(dw).max()<0.06,f"mean {1000*dw.mean():+.1f} ms, sd {1000*dw.std():.1f}, max |.| {1000*np.abs(dw).max():.0f} ms")
# 8 timeline conversion small
dc=np.array([r['downbeat']-r['downbeat_mix_timeline'] for r in L])
check('mix->vocal timeline correction is below 5 ms everywhere',np.abs(dc).max()<0.005,f"range {1000*dc.min():+.1f}..{1000*dc.max():+.1f} ms")
print('ALL CHECKS PASSED' if ok else 'SOME CHECKS FAILED')
json.dump(dict(all_passed=bool(ok)),open(O+'/verify_result.json','w'))
