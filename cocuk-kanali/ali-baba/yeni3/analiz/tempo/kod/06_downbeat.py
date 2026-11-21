# Step 2: where are the bar lines?  Evidence gathered on the fixed 116.00 BPM beat lattice.
# Lattice: beat n at PHI + n*P (global, drift-free, see 02/05).  Verse onset beats come from the
# sung-line onsets (nearest lattice beat).  Everything is folded RELATIVE TO THE VERSE ONSET BEAT,
# so that irregular bar counts between verses do not matter.
import numpy as np, json, scipy.signal as ss
from common import *
P=60/116.0; PHI=0.0015
names=['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
x=load_mix(); v=load_vocal(); n=min(len(x),len(v)); x=x[:n]; v=v[:n]
words=load_words()
VERSE_T=[6.20,18.62,33.12,46.56,59.48,73.96,86.40]
VB=[int(round((tv-PHI)/P)) for tv in VERSE_T]            # verse onset beat numbers
print('verse onset beats',VB,'diffs',np.diff(VB),'mod4',[b%4 for b in VB])
NBEAT=int((len(x)/SR-PHI)/P)-1

# ---------- features ----------
NF=8192; HP=256
f,t,Sm=stft_mag(x,NF,HP); _,_,Sv=stft_mag(v,NF,HP)
Sa=np.maximum(Sm-Sv,0)                                   # accompaniment estimate
def midi_of(fr): return 69+12*np.log2(np.maximum(fr,1e-6)/440.0)
def chroma(spec,lo,hi):
    band=(f>=lo)&(f<=hi); m=midi_of(f[band]); pc=np.round(m).astype(int)%12
    w=np.cos(np.pi*np.abs(m-np.round(m)))**2
    c=np.zeros(12); np.add.at(c,pc,spec[band]**2*w); return c/(c.sum()+1e-12)
f2,t2,S2=stft_mag(x,2048,HP); _,_,S2v=stft_mag(v,2048,HP); S2a=np.maximum(S2-S2v,0)
fl_low=flux(S2,f2,120,300); fl_kick=flux(S2,f2,40,120); fl_hi=flux(S2a,f2,2000,8000); fl_air=flux(S2a,f2,8000,16000); fl_mid=flux(S2a,f2,300,2000)
en_air=np.sqrt((S2a[(f2>=6000)&(f2<=16000)]**2).sum(0))
def pk(env,g,w=0.045):
    m=(t2>=g-w)&(t2<=g+w); return float(env[m].max())
beats=[]
for b in range(NBEAT):
    g=PHI+b*P
    m=(t>=g+0.03)&(t<g+P-0.03)
    bc=chroma(Sm[:,m].mean(1),40,260); mc=chroma(Sa[:,m].mean(1),260,2000)
    m_air=(t2>=g)&(t2<g+P)
    beats.append(dict(beat=b,t=g,bass=bc,mid=mc,kick=pk(fl_kick,g),low=pk(fl_low,g),hi=pk(fl_hi,g),air=pk(fl_air,g),mid_on=pk(fl_mid,g),
                      low_off=pk(fl_low,g+P/2),kick_off=pk(fl_kick,g+P/2),hi_off=pk(fl_hi,g+P/2),air_off=pk(fl_air,g+P/2),mid_off=pk(fl_mid,g+P/2),
                      air_energy=float(en_air[m_air].mean())))
for key in ('kick','low','hi','air','mid_on','low_off','kick_off','hi_off','air_off','mid_off','air_energy'):
    med=np.median([bt[key] for bt in beats if VB[0]<=bt['beat']<VB[-1]+28])
    for bt in beats: bt[key]/=med
A_pc,E_pc=9,4
out={'lattice':dict(bpm=116.0,beat_period_s=P,phase_first_beat_s=PHI),'verse_onset_beats':VB,'verse_onset_beat_diffs':np.diff(VB).tolist(),
     'verse_onset_beat_mod4_on_global_grid':[b%4 for b in VB]}

# ---------- C6: intro pattern ----------
print('\nINTRO (beats 0..15):')
intro=[]
for b in range(0,16):
    bt=beats[b]
    tb=' '.join(names[i] for i in np.argsort(bt['bass'])[::-1][:2]); tm=' '.join(names[i] for i in np.argsort(bt['mid'])[::-1][:3])
    print(f"  beat {b:2d} t={bt['t']:6.3f} kick {bt['kick']:.2f} low {bt['low']:.2f} mid_on {bt['mid_on']:.2f} hi {bt['hi']:.2f} | off: mid {bt['mid_off']:.2f} hi {bt['hi_off']:.2f} | bass-top {tb:5s} mid-top {tm}")
    intro.append(dict(beat=b,t=bt['t'],kick=bt['kick'],low=bt['low'],mid_on=bt['mid_on'],mid_off=bt['mid_off'],bass_top=tb,mid_top=tm))
out['intro_beats']=intro

# ---------- sections ----------
secs=[]
for i,vb in enumerate(VB):
    end=VB[i+1] if i+1<len(VB) else vb+16+12
    secs.append((i+1,vb,end))
def fold(key,nmod=4,vocal_only=None):
    """mean of a scalar beat feature by position mod nmod relative to the verse onset. vocal_only: True -> first 16 beats, False -> gap."""
    acc=[[] for _ in range(nmod)]
    for (vi,vb,end) in secs:
        for b in range(vb,min(end,NBEAT)):
            rel=b-vb
            if vocal_only is True and rel>=16: continue
            if vocal_only is False and rel<16: continue
            acc[rel%nmod].append(beats[b][key])
    return [(float(np.mean(a)),float(np.std(a)/np.sqrt(len(a))),len(a)) for a in acc]

# ---------- C1: bass root parity ----------
def bassA(bt): return bt['bass'][A_pc]/(bt['bass'][A_pc]+bt['bass'][E_pc]+1e-9)
for bt in beats: bt['bassA']=float(bassA(bt)); bt['domE']=float(bt['mid'][[4,8,11]].sum()); bt['tonA']=float(bt['mid'][[9,0,1,4]].sum()); bt['colFC']=float(bt['mid'][[5,0]].sum())
print('\nFOLD relative to verse onset (mean, sem, n) by beat position mod 4')
folds={}
for key in ('bassA','tonA','domE','colFC','kick','low','hi','air','mid_on','low_off','kick_off','hi_off','air_off','mid_off','air_energy'):
    for vo,lab in ((None,'all'),(True,'vocal_bars'),(False,'gap_bars')):
        r=fold(key,4,vo); folds[key+'_'+lab]=r
        print(f"  {key:10s} {lab:10s} "+'  '.join(f"p{i}: {a:.3f}±{s:.3f}" for i,(a,s,_) in enumerate(r)))
out['fold_mod4_relative_to_verse_onset']=folds

# per-verse root parity: is bass A stronger on even (0,2) or odd (1,3) relative positions?
par=[]
for (vi,vb,end) in secs:
    ev=np.mean([beats[b]['bassA'] for b in range(vb,min(end,NBEAT)) if (b-vb)%2==0]); od=np.mean([beats[b]['bassA'] for b in range(vb,min(end,NBEAT)) if (b-vb)%2==1])
    nwin=sum(1 for b in range(vb,min(end,NBEAT)-1,2) if beats[b]['bassA']>beats[b+1]['bassA']); ntot=len(range(vb,min(end,NBEAT)-1,2))
    par.append(dict(verse=vi,bassA_even=float(ev),bassA_odd=float(od),pairs_even_gt_odd=nwin,pairs=ntot))
    print(f"  verse {vi}: bass-A share even {ev:.3f} odd {od:.3f}; pairs even>odd {nwin}/{ntot}")
out['bass_root_parity_per_verse']=par

# global-lattice parity check: does the root parity flip between verse 4 and 5 on the GLOBAL beat numbering?
gp=[]
for (vi,vb,end) in secs:
    e0=np.mean([beats[b]['bassA'] for b in range(vb,min(end,NBEAT)) if b%2==0]); e1=np.mean([beats[b]['bassA'] for b in range(vb,min(end,NBEAT)) if b%2==1])
    gp.append(dict(verse=vi,bassA_global_even=float(e0),bassA_global_odd=float(e1)))
out['bass_root_parity_on_global_numbering']=gp
print('  global-number parity (even,odd):',[(round(g['bassA_global_even'],2),round(g['bassA_global_odd'],2)) for g in gp])

# ---------- C4: periodicity of beat feature sequences ----------
def vec(bt): return np.concatenate([bt['bass'],bt['mid']])
V=np.array([vec(bt) for bt in beats]); V=V-V[VB[0]:VB[-1]+28].mean(0)
def lagsim(lag,a,b):
    s=[]
    for i in range(a,b-lag):
        u,w=V[i],V[i+lag]; s.append(float(u@w/(np.linalg.norm(u)*np.linalg.norm(w)+1e-12)))
    return float(np.mean(s))
ls={lag:lagsim(lag,VB[0],VB[-1]+28) for lag in range(1,13)}
print('\nbeat-feature self-similarity by lag (beats):',{k:round(vv,3) for k,vv in ls.items()})
out['beat_feature_selfsim_by_lag']=ls

# ---------- C5: cross-verse alignment ----------
print('\ncross-verse alignment (chroma sequence of the 16 vocal beats of verse v vs verse 1, shifted by s beats):')
ca=[]
ref=V[VB[0]:VB[0]+16]
for (vi,vb,end) in secs[1:]:
    row={}
    for s in range(-4,5):
        seg=V[vb+s:vb+s+16]
        row[s]=float(np.mean([seg[i]@ref[i]/(np.linalg.norm(seg[i])*np.linalg.norm(ref[i])+1e-12) for i in range(16)]))
    best=max(row,key=row.get); ca.append(dict(verse=vi,sim_by_shift=row,best_shift=best))
    print(f"  verse {vi}: "+' '.join(f"{s:+d}:{row[s]:.2f}" for s in range(-4,5))+f"  -> best {best:+d}")
out['cross_verse_alignment_vs_verse1']=ca

# ---------- 4-beat-phase evidence inside sections: average 4-beat chroma pattern ----------
print('\nmean mid-chroma (accompaniment) top pitch classes by position mod 4 (relative to verse onset):')
pat={}
for lab,vo in (('vocal_bars',True),('gap_bars',False)):
    for p in range(4):
        cs=[];bs=[]
        for (vi,vb,end) in secs:
            for b in range(vb,min(end,NBEAT)):
                rel=b-vb
                if (rel<16)!=vo or rel%4!=p: continue
                cs.append(beats[b]['mid']); bs.append(beats[b]['bass'])
        c=np.mean(cs,0); bb=np.mean(bs,0)
        top=' '.join(f"{names[i]}:{c[i]:.2f}" for i in np.argsort(c)[::-1][:4]); topb=' '.join(f"{names[i]}:{bb[i]:.2f}" for i in np.argsort(bb)[::-1][:3])
        pat[f'{lab}_p{p}']=dict(mid=c.tolist(),bass=bb.tolist())
        print(f"  {lab} p{p}: mid {top} | bass {topb}")
out['mean_chroma_by_position']=pat

# ---------- per-section beat listing of the gaps (to see where irregular bars sit) ----------
print('\nGAP listings (rel = beats since verse onset):')
gaps=[]
for (vi,vb,end) in secs:
    for b in range(vb+14,min(end+2,NBEAT)):
        bt=beats[b]; rel=b-vb
        tb=names[int(np.argmax(bt['bass']))]; tm=' '.join(names[i] for i in np.argsort(bt['mid'])[::-1][:3])
        mark='<-- next verse onset' if b==end else ''
        print(f"  v{vi} beat {b:3d} rel {rel:2d} (p{rel%4}) t={bt['t']:7.3f} bassA {bt['bassA']:.2f} bass-top {tb:2s} mid-top {tm:9s} kick {bt['kick']:.2f} kick_off {bt['kick_off']:.2f} low_off {bt['low_off']:.2f} mid_on {bt['mid_on']:.2f} mid_off {bt['mid_off']:.2f} hi_off {bt['hi_off']:.2f} air_en {bt['air_energy']:.2f} {mark}")
        gaps.append(dict(verse=vi,beat=b,rel=rel,t=bt['t'],bassA=bt['bassA'],bass_top=tb,mid_top=tm,kick=bt['kick'],kick_off=bt['kick_off'],low_off=bt['low_off'],mid_on=bt['mid_on'],mid_off=bt['mid_off'],hi_off=bt['hi_off'],air_energy=bt['air_energy']))
out['gap_beat_listing']=gaps
for bt in beats: bt['bass']=bt['bass'].tolist(); bt['mid']=bt['mid'].tolist()
out['beats']=beats
json.dump(out,open(O+'/downbeat_evidence.json','w'))
