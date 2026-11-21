# ROUGH sung pitch per word (verses 1 and 2; summary for all 7) from the FULL MIX - the band is still in the signal.
#  method 1: harmonic-comb salience (harmonics 1..5, in-between penalty) on a 93 ms STFT, 10 ms hop, f0 130-700 Hz;
#            per word: median, note runs (stable stretches >= 60 ms), share of frames per semitone
#  method 2: pyworld (harvest) on the 200-1500 Hz band-passed mix
# Then: how well do the sung notes fit candidate MAJOR keys under the harmony planned for the new form
# (vocal bars: I I IV I per beat, "diye bagirir": I)?
import numpy as np, json, scipy.signal as ss
from common import *
P,PHI=lattice(); x=load_mix(); words=load_words(); S_=json.load(open(O+'/segments.json')); KC=json.load(open(O+'/key_chords.json'))
TUNE=KC['tuning']['adopted_cents_re_A440']
fs=SR/4; y=ss.decimate(x,4,ftype='fir',zero_phase=True)
NW=1024; NF=8192; HP=110; dt=HP/fs
f,t,S=ss.stft(y,fs,window='hann',nperseg=NW,noverlap=NW-HP,nfft=NF,boundary='zeros',padded=True); S=np.abs(S)
cands=130*2**(np.arange(0,int(1200*np.log2(700/130)),10)/1200)
W=((1,1.0),(2,0.8),(3,0.6),(4,0.5),(5,0.4))
def sal_frame(col):
    c=np.sqrt(col); s=np.zeros(len(cands))
    for h,w in W:
        s+=w*np.interp(cands*h,f,c); s-=0.5*w*np.interp(cands*(h-0.5),f,c)
    return s
SAL=np.array([sal_frame(S[:,i]) for i in range(S.shape[1])]).T     # cand x frame
def midi(fq): return 69+12*np.log2(fq/440.0)-TUNE/100.0
def nname(m): r=int(round(m)); return f"{NAMES[r%12]}{r//12-1}"
import pyworld as pw
sos=ss.butter(4,[200,1500],btype='band',fs=fs,output='sos'); yb=ss.sosfiltfilt(sos,y).astype(np.float64)
f0w,tw=pw.harvest(yb,int(fs),f0_floor=130.0,f0_ceil=700.0,frame_period=10.0)
def analyse(w):
    a=w['start']+0.02; b=w['end']-0.01
    if b-a<0.05: a=w['start']; b=w['end']
    idx=np.where((t>=a)&(t<=b))[0]
    best=SAL[:,idx].argmax(0); fq=cands[best]; m=midi(fq); st=SAL[:,idx].max(0)
    # octave diagnostic: salience at f0/2 relative to f0 (mean over frames)
    half=np.array([np.interp(fq[i]/2,cands,SAL[:,idx[i]]) if fq[i]/2>=cands[0] else 0.0 for i in range(len(idx))])
    # runs of stable pitch
    mm=ss.medfilt(m,5) if len(m)>=5 else m
    runs=[]; s0=0
    for i in range(1,len(mm)+1):
        if i==len(mm) or abs(mm[i]-np.median(mm[s0:i]))>0.7:
            if (i-s0)*dt>=0.06:
                med=float(np.median(mm[s0:i])); runs.append(dict(start=round(float(t[idx[s0]]),3),dur=round((i-s0)*dt,3),midi=round(med,2),note=nname(med),cents=round(100*(med-round(med))),
                      beat_in_verse=None))
            s0=i
    hist={}
    for q in np.round(m).astype(int): hist[nname(q)]=hist.get(nname(q),0)+1
    hist={k:round(v/len(m),2) for k,v in sorted(hist.items(),key=lambda kv:-kv[1])[:3]}
    iw=np.where((tw>=a)&(tw<=b)&(f0w>0))[0]
    pwm=float(np.median(midi(f0w[iw]))) if len(iw)>=3 else None
    med=float(np.median(m))
    return dict(text=w['text'],start=w['start'],end=w['end'],median_midi=round(med,2),median_note=nname(med),median_cents=round(100*(med-round(med))),median_hz=round(float(440*2**((med+TUNE/100-69)/12)),1),
                iqr_semitones=round(float(np.percentile(m,75)-np.percentile(m,25)),2),frame_share_by_note=hist,note_runs=runs,
                subharmonic_salience_ratio=round(float(half.mean()/(st.mean()+1e-9)),2),
                pyworld_median_midi=None if pwm is None else round(pwm,2),pyworld_note=None if pwm is None else nname(pwm),pyworld_voiced_frames=int(len(iw)))
out=[]
SEG=['L1']*5+['L2']*3+['ses']*2+['diye']*2+['L4']*3
for v in range(7):
    vb=S_['verses'][v]['onset_beat']
    for i in range(15):
        w=words[15*v+i]; r=analyse(w); r.update(verse=v+1,segment=SEG[i],index_in_verse=i,start_beats_from_verse_downbeat=round((w['start']-(PHI+vb*P))/P,2))
        for q in r['note_runs']: q['beat_in_verse']=round((q['start']-(PHI+vb*P))/P,2)
        out.append(r)
for v in (1,2):
    print(f'--- verse {v} (rough, band still in the signal) ---')
    for r in out:
        if r['verse']!=v: continue
        print(f"  {r['segment']:4s} {r['text']:13s} {r['start']:6.2f}-{r['end']:6.2f} b{r['start_beats_from_verse_downbeat']:5.2f} median {r['median_note']:3s}{r['median_cents']:+4d}c ({r['median_hz']:5.1f} Hz) iqr {r['iqr_semitones']:.1f} | runs: "+' '.join(f"{q['note']}{q['cents']:+d}({q['dur']:.2f}s@b{q['beat_in_verse']})" for q in r['note_runs'])+f" | share {r['frame_share_by_note']} | sub {r['subharmonic_salience_ratio']} | pyworld {r['pyworld_note']} ({r['pyworld_voiced_frames']})")
# consensus per word index over the 7 verses (the tune repeats)
print('--- consensus over 7 verses (median note per word index) ---')
cons=[]
for i in range(15):
    ms=[r['median_midi'] for r in out if r['index_in_verse']==i]; nn=[nname(q) for q in ms]
    c=dict(index=i,segment=SEG[i],text_verse1=words[i]['text'],median_midi=round(float(np.median(ms)),2),note=nname(np.median(ms)),per_verse_notes=nn,agree=int(sum(1 for q in nn if q==nname(np.median(ms)))))
    cons.append(c); print(f"  {i:2d} {SEG[i]:4s} {words[i]['text']:13s} {c['note']:3s} agree {c['agree']}/7  {nn}")
# pitch-class duration histogram of the sung parts (L1, L2, diye, L4; not 'ses'), all verses, from note runs
pcd=np.zeros(12)
for r in out:
    if r['segment']=='ses': continue
    for q in r['note_runs']: pcd[int(round(q['midi']))%12]+=q['dur']
pcd/=pcd.sum(); print('sung pitch-class duration share (no ses):',{NAMES[i]:round(float(pcd[i]),3) for i in np.argsort(pcd)[::-1] if pcd[i]>0.005})
# ---- fit of the sung notes to candidate keys of the NEW backing ----
MAJ=[0,2,4,5,7,9,11]; NATMIN=[0,2,3,5,7,8,10]
def chord_pcs(key,deg,minor=False):
    sc=NATMIN if minor else MAJ
    return [(key+sc[(deg+k)%7]+(0))%12 for k in (0,2,4)]
def fit(key,minor=False):
    """duration-weighted score: chord tone 1, other scale tone 0.5 (0 if a semitone above a chord tone = 'avoid' note), outside the scale -1"""
    sc=[(key+s)%12 for s in (NATMIN if minor else MAJ)]; tot=0; wsum=0; det=dict(chord_tone=0.0,scale_tone=0.0,avoid=0.0,outside=0.0)
    for r in out:
        if r['segment']=='ses': continue
        for q in r['note_runs']:
            bar_start={'L1':0,'L2':4,'diye':8,'L4':12}[r['segment']]
            bib=int(np.floor(q['beat_in_verse']-bar_start+0.15))%4
            deg=3 if (bib==2 and r['segment']!='diye') else 0          # planned: I I IV I ; "diye bagirir" over I
            ch=chord_pcs(key,deg,minor); pc=int(round(q['midi']))%12; d=q['dur']
            if pc in ch: s=1.0; det['chord_tone']+=d
            elif pc not in sc: s=-1.0; det['outside']+=d
            elif any((pc-c)%12==1 for c in ch): s=0.0; det['avoid']+=d
            else: s=0.5; det['scale_tone']+=d
            tot+=s*d; wsum+=d
    return dict(score=round(tot/wsum,3),**{k:round(v/wsum,3) for k,v in det.items()})
fits={}
for k in range(12):
    fits[NAMES[k]+' major']=fit(k)
fits['D minor (original loop key, for reference: i i iv i)']=fit(2,True)
rank=sorted(fits.items(),key=lambda kv:-kv[1]['score'])
print('--- fit of the sung notes (all verses, without ses) to the planned harmony I I IV I, by key of the new backing ---')
for k,vv in rank[:8]: print(f"  {k:55s} {vv}")
json.dump(dict(flag='ROUGH: measured on the full mix; the band (off-beat chords and melody notes in the same register) is still in the signal',
               tuning_cents_used=TUNE,words=out,consensus_per_word_index=cons,sung_pitch_class_duration_share={NAMES[i]:float(pcd[i]) for i in range(12)},
               key_fit_for_new_backing=dict(method='duration-weighted: chord tone 1, scale tone 0.5, avoid note (semitone above a chord tone) 0, outside scale -1; harmony I I IV I per beat for L1/L2/L4 bars, I for diye bagirir',ranking=[dict(key=k,**vv) for k,vv in rank])),
          open(O+'/vocal_pitch_rough.json','w'),ensure_ascii=False,indent=1)
