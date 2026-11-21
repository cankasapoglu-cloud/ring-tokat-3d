# Step 2: where are the bar lines?  Evidence gathered on the refined 105 BPM beat lattice (14_lattice.py).
# Verse onset beats come from the sung-line onsets (nearest lattice beat).  Features are folded RELATIVE TO THE
# VERSE ONSET BEAT (position 0..23 inside the 24-beat verse) and by position mod 4.
# No separated vocal exists yet, so all features come from the full mix.
import numpy as np, json, scipy.signal as ss
from common import *
P,PHI=lattice()
names=NAMES
x=load_mix(); words=load_words()
VB=[int(round((tv-PHI)/P)) for tv in VERSE_T]
print('verse onset beats',VB,'diffs',np.diff(VB).tolist(),'mod4 on the global grid (beat 0 = t %.4f):'%PHI,[b%4 for b in VB])
NBEAT=int((len(x)/SR-PHI)/P)-1
f2,t2,S2=stft_mag(x,2048,HOP)
fl={'kick':flux(S2,f2,40,120),'low':flux(S2,f2,120,300),'mid':flux(S2,f2,300,2000),'hi':flux(S2,f2,2000,8000),'air':flux(S2,f2,8000,16000)}
en={'e_low':np.sqrt((S2[(f2>=40)&(f2<=150)]**2).sum(0)),'e_mid':np.sqrt((S2[(f2>=300)&(f2<=2000)]**2).sum(0)),
    'e_snare':np.sqrt((S2[(f2>=1500)&(f2<=6000)]**2).sum(0)),'e_air':np.sqrt((S2[(f2>=7000)&(f2<=16000)]**2).sum(0)),'e_all':np.sqrt((S2**2).sum(0))}
def pk(env,g,w=0.045):
    m=(t2>=g-w)&(t2<=g+w); return float(env[m].max())
beats=[]
for b in range(NBEAT):
    g=PHI+b*P; r=dict(beat=b,t=g)
    for k,e in fl.items():
        r[k]=pk(e,g); r[k+'_off']=pk(e,g+P/2)
    for k,e in en.items():
        m=(t2>=g)&(t2<g+P); r[k]=float(e[m].mean())
        m1=(t2>=g+0.01)&(t2<g+0.13); r[k+'_hit']=float(e[m1].mean())
    beats.append(r)
keys=[k for k in beats[0] if k not in('beat','t')]
for key in keys:
    med=np.median([bt[key] for bt in beats if VB[0]<=bt['beat']<VB[-1]+24])
    for bt in beats: bt[key]/=med
out={'lattice':dict(bpm=60/P,beat_period_s=P,phase_first_beat_s=PHI),'verse_onset_beats':VB,'verse_onset_beat_diffs':np.diff(VB).tolist(),
     'verse_onset_beat_mod4_on_global_grid':[b%4 for b in VB]}
def wordat(g):
    return ' '.join(w['text'] for w in words if g-P/4<=w['start']<g+3*P/4)
print('\nINTRO + verse 1 (beats 0..%d): band onset strengths (1.0 = median of the song body)'%(VB[0]+24))
lst=[]
for b in range(0,min(VB[0]+25,NBEAT)):
    bt=beats[b]; rel=b-VB[0]
    print(f"  beat {b:3d} rel {rel:3d} t={bt['t']:7.3f} kick {bt['kick']:.2f} low {bt['low']:.2f} mid {bt['mid']:.2f} hi {bt['hi']:.2f} air {bt['air']:.2f} | off: mid {bt['mid_off']:.2f} hi {bt['hi_off']:.2f} air {bt['air_off']:.2f} | E low {bt['e_low']:.2f} snare-hit {bt['e_snare_hit']:.2f} air {bt['e_air']:.2f} all {bt['e_all']:.2f}  {wordat(bt['t'])}")
    lst.append(dict(beat=b,rel=rel,t=bt['t'],**{k:bt[k] for k in ('kick','low','mid','hi','air','mid_off','hi_off','air_off','e_low','e_snare_hit','e_air','e_all')}))
out['intro_and_verse1_beats']=lst
print('\nFOLD by position mod 4 relative to the verse onset (mean±sem over 7 verses x 6 bars):')
folds={}
for key in keys:
    acc=[[] for _ in range(4)]
    for vb in VB:
        for b in range(vb,min(vb+24,NBEAT)): acc[(b-vb)%4].append(beats[b][key])
    r=[(float(np.mean(a)),float(np.std(a)/np.sqrt(len(a))),len(a)) for a in acc]; folds[key]=r
    print(f"  {key:12s} "+'  '.join(f"p{i}: {a:.3f}±{s:.3f}" for i,(a,s,_) in enumerate(r)))
out['fold_mod4_relative_to_verse_onset']=folds
print('\nFOLD by position 0..23 inside the verse (mean over 7 verses):')
f24={}
for key in ('kick','low','mid','hi','air','hi_off','air_off','e_low','e_snare_hit','e_air','e_air_hit','e_all'):
    r=[float(np.mean([beats[vb+p][key] for vb in VB if vb+p<NBEAT])) for p in range(24)]; f24[key]=r
    print(f"  {key:12s} "+' | '.join(' '.join(f"{v:4.2f}" for v in r[q*4:q*4+4]) for q in range(6)))
out['fold_24_relative_to_verse_onset']=f24
# beat-feature periodicity
V=np.array([[bt[k] for k in ('kick','low','mid','hi','air','mid_off','hi_off','air_off','e_low','e_snare_hit','e_air','e_all')] for bt in beats])
V=np.log(V+1e-3); V=V-V[VB[0]:min(VB[-1]+24,NBEAT)].mean(0)
def lagsim(lag,a,b):
    return float(np.mean([V[i]@V[i+lag]/(np.linalg.norm(V[i])*np.linalg.norm(V[i+lag])+1e-12) for i in range(a,b-lag)]))
ls={lag:lagsim(lag,VB[0],min(VB[-1]+24,NBEAT)) for lag in (1,2,3,4,6,8,12,16,24)}
print('\nbeat-feature self-similarity by lag (beats):',{k:round(v,3) for k,v in ls.items()})
out['beat_feature_selfsim_by_lag']=ls
out['beats']=beats
json.dump(out,open(O+'/downbeat_evidence.json','w'))
