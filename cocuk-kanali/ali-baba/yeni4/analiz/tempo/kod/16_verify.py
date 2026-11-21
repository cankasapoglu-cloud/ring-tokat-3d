# Checks on the deliverable tempo.json (structure, arithmetic, and independent re-measurements on the mix).
import json, numpy as np
from common import *
d=json.load(open(O+'/tempo.json')); P=d['beat_phase']['lattice']['beat_period_s']; PHI=d['beat_phase']['lattice']['phase_first_beat_s']
ok=True
def chk(c,msg):
    global ok
    print(('OK   ' if c else 'FAIL ')+msg); ok&=bool(c)
S=d['segments']; chk(len(S)==35,'35 segments')
for v in range(1,8): chk([s['name'] for s in S if s['verse']==v]==['L1','L2','ses','diye','L4'],f'verse {v} has L1 L2 ses diye L4')
words=load_words()
bad=[]
for s in S:
    db=PHI+s['beat_number_of_bar_downbeat']*P
    if abs(db-s['bar_downbeat'])>1e-3: bad.append(('db',s['verse'],s['name']))
    if abs(s['onset']-s['bar_downbeat']-s['offset_sec'])>2e-4: bad.append(('off',s['verse'],s['name']))
    if abs(s['offset_sec']/P-s['offset_beats'])>2e-3: bad.append(('offb',s['verse'],s['name']))
    if abs(s['onset']-s['onset_words_file'])>0.065: bad.append(('refine',s['verse'],s['name']))
    if not s['onset']<s['end']: bad.append(('order',s['verse'],s['name']))
    exp=2.0 if s['name']=='diye' else 0.0
    if abs(s['offset_beats']-exp)>0.12: bad.append(('beat',s['verse'],s['name'],s['offset_beats']))
    if not any(abs(w['start']-s['onset_words_file'])<1e-6 for w in words): bad.append(('word',s['verse'],s['name']))
chk(not bad,'segment arithmetic, onsets within 65 ms of the words file, expected beats within 0.12 beat '+str(bad))
vd=d['summary']['verse_downbeats']; chk(np.allclose(np.diff(vd),24*P,atol=1e-3),'verse downbeats 24 beats apart: '+str(np.round(np.diff(vd),4).tolist()))
chk(all(np.allclose(np.diff(v['bar_downbeats']),4*P,atol=1e-4) for v in d['downbeat']['verses']),'bar downbeats 4 beats apart in every verse')
# independent re-measurement 1: kick-envelope grid score at the lattice vs alternatives
E_=np.load(CACHE+'/env.npz'); te,envB=E_['t'],E_['envB']; m=envB[(te>8)&(te<100)].mean()
def sc(per,ph): return grid_score(envB,te,per,ph,8.0,100.0)/m
s0=max(sc(P,PHI+k*0.002) for k in range(0,13)); s_half=max(sc(P,PHI+P/2+k*0.002) for k in range(0,13)); s_49=max(sc(60/104.96,8.0+k*0.004) for k in range(150)); s_105=max(sc(60/105.0,8.0+k*0.004) for k in range(150))
print('kick grid score: lattice %.2f | half-beat shifted %.2f | best phase at 104.96 BPM %.2f | best phase at 105.000 BPM %.2f'%(s0,s_half,s_49,s_105))
chk(s0>3*s_half,'lattice beats carry the kick (not the off-beat eighth)')
chk(s_105>s_49 and s0>s_49,'a 104.96 BPM grid scores lower than 105.00 (it would slip 35 ms over the song; the kick envelope is about that wide, so the drop is moderate)')
# independent re-measurement 1b: regression of the individual kick times (beats 15..174) on the beat number
kt=[];kb=[]
for b in range(15,175):
    g=PHI+b*P; mm=np.where((te>=g-0.06)&(te<=g+0.06))[0]; k=mm[np.argmax(envB[mm])]
    y0,y1,y2=envB[k-1],envB[k],envB[k+1]; dd=0.5*(y0-y2)/(y0-2*y1+y2) if (y0-2*y1+y2)!=0 else 0
    kt.append(te[k]+dd*(te[1]-te[0])); kb.append(b)
kt=np.array(kt); kb=np.array(kb); A_=np.vstack([kb,np.ones(len(kb))]).T
(sl,ic),res,_,_=np.linalg.lstsq(A_,kt,rcond=None); r=kt-(sl*kb+ic); se=r.std(ddof=2)/np.sqrt(((kb-kb.mean())**2).sum())
bpm_k=60/sl; se_bpm=60/sl**2*se
print('160 individual kick times regressed on beat number: %.4f BPM +- %.4f (residual sd %.1f ms); time of beat 0 = %.4f s'%(bpm_k,se_bpm,r.std()*1000,ic))
chk(abs(bpm_k-60/P)<0.01 and abs(bpm_k-104.96)>10*se_bpm,'independent kick regression confirms the lattice tempo and excludes 104.96 BPM')
# independent re-measurement 2: kick rise near every bar downbeat of the 42 bars
dev=[]
for v in d['downbeat']['verses']:
    for g in v['bar_downbeats']:
        mm=(te>=g-0.08)&(te<=g+0.08); dev.append(te[mm][np.argmax(envB[mm])]-g)
dev=np.array(dev)*1000
print('kick low-frequency rise peak minus bar downbeat over 42 bars: mean %.1f ms, sd %.1f ms, min %.1f, max %.1f (the LF body of the kick lags its click by design)'%(dev.mean(),dev.std(),dev.min(),dev.max()))
chk(dev.std()<8 and abs(dev.mean())<35,'every one of the 42 bar downbeats has a kick at the same small lag')
chk(d['summary']['original_key']=='D minor' and len(d['key']['chords_per_bar'])==6,'key and 6 bars of chords present')
chk(len(d['vocal_pitch_rough']['verse_1'])==15 and len(d['vocal_pitch_rough']['verse_2'])==15,'rough pitch for 15 words of verse 1 and verse 2')
json.dump(dict(all_ok=bool(ok)),open(O+'/verify_result.json','w'))
print('ALL OK' if ok else 'SOME CHECKS FAILED')
