# Key, chords and tuning of the ORIGINAL band of v2_2 (full mix; no separated stems exist).
#  - There is no bass guitar: 40-120 Hz is the kick only (about 52 Hz on every beat). The harmony instrument plays
#    on the OFF-beat half of every beat with its lowest notes at A2..G3, i.e. BELOW the sung range (D4..A4).
#  - chroma LOW  = 95-275 Hz (A2..C4), off-beat half of each beat  -> vocal-free root/fifth/third information
#  - chroma MID  = 275-2000 Hz, whole beat                         -> contains the vocal in bars 0-3; clean in bars 4-5
#  - chords: triad templates on the 24 positions of a verse (mean over 7 verses) and per verse (agreement count)
#  - key: Krumhansl-Schmuckler profiles on aggregated chroma + the chord loop itself
#  - tuning: cents deviation of strong spectral peaks from equal temperament (A=440), instrumental bars and all
import numpy as np, json, scipy.signal as ss
from common import *
x=load_mix(); P,PHI=lattice()
VB=[int(round((tv-PHI)/P)) for tv in VERSE_T]
fs=SR/4; y=ss.decimate(x,4,ftype='fir',zero_phase=True)
NF=8192; fr=np.fft.rfftfreq(NF,1/fs)          # 1.35 Hz bins
def spec(t0,t1):
    a=int(t0*fs); e=int(t1*fs); seg=y[a:e]*np.hanning(e-a); return np.abs(np.fft.rfft(seg,NF))
def midi_of(f): return 69+12*np.log2(np.maximum(f,1e-6)/440.0)
def chroma(S,lo,hi,tune=0.0):
    band=(fr>=lo)&(fr<=hi); m=midi_of(fr[band])-tune/100.0; pc=np.round(m).astype(int)%12
    w=np.cos(np.pi*np.abs(m-np.round(m)))**4
    c=np.zeros(12); np.add.at(c,pc,S[band]**2*w); return c
def peaks_cents(S,lo,hi,rel_db=-25):
    band=np.where((fr>=lo)&(fr<=hi))[0]; s=S[band]; pk,_=ss.find_peaks(s,height=s.max()*10**(rel_db/20))
    out=[]
    for k in pk:
        if k<1 or k>=len(s)-1: continue
        y0,y1,y2=np.log(s[k-1]+1e-12),np.log(s[k]+1e-12),np.log(s[k+1]+1e-12); d=0.5*(y0-y2)/(y0-2*y1+y2)
        f=fr[band][k]+d*(fr[1]-fr[0]); m=midi_of(f); out.append((100*(m-np.round(m)),s[k]**2,f))
    return out
# ---------- tuning ----------
def tuning(beat_list,lo,hi,half='off'):
    cs=[];ws=[]
    for b in beat_list:
        g=PHI+b*P
        S=spec(g+P/2,g+P-0.005) if half=='off' else spec(g+0.03,g+P-0.005)
        for c,w,f in peaks_cents(S,lo,hi): cs.append(c); ws.append(w)
    cs=np.array(cs); ws=np.array(ws)
    z=(np.sqrt(ws)*np.exp(2j*np.pi*cs/100)).sum()/np.sqrt(ws).sum()
    return dict(cents=float(np.angle(z)/(2*np.pi)*100),concentration_R=float(abs(z)),n_peaks=int(len(cs)),median_cents_of_peaks_within_30c=float(np.median(cs[np.abs(cs)<30])) if (np.abs(cs)<30).any() else None)
inst=[vb+p for vb in VB for p in range(16,24) if vb+p<int((len(x)/SR-PHI)/P)-1]
allb=[vb+p for vb in VB for p in range(0,24) if vb+p<int((len(x)/SR-PHI)/P)-1]
tun={'instrumental_bars_low_95_275':tuning(inst,95,275),'instrumental_bars_mid_275_2000':tuning(inst,275,2000,'all'),
     'all_bars_low_95_275':tuning(allb,95,275),'all_bars_mid_275_2000_incl_vocal':tuning(allb,275,2000,'all')}
import librosa
try:
    yi=np.concatenate([x[int((PHI+(vb+16)*P)*SR):int((PHI+(vb+24)*P)*SR)] for vb in VB[:-1]]).astype(np.float32)
    tun['librosa_estimate_tuning_instrumental_bars_cents']=float(100*librosa.estimate_tuning(y=yi,sr=SR,n_fft=8192))
    tun['librosa_estimate_tuning_whole_song_cents']=float(100*librosa.estimate_tuning(y=x.astype(np.float32),sr=SR,n_fft=8192))
except Exception as e: tun['librosa_error']=str(e)
vals=[tun[k]['cents'] for k in ('instrumental_bars_low_95_275','instrumental_bars_mid_275_2000','all_bars_low_95_275')]
TUNE=float(np.median(vals)); tun['adopted_cents_re_A440']=TUNE; tun['adopted_A4_hz']=float(440*2**(TUNE/1200))
print('TUNING:',json.dumps(tun,indent=1))
# ---------- per-beat chroma ----------
NB=int((len(x)/SR-PHI)/P)-1
beats=[]
for b in range(NB):
    g=PHI+b*P
    So=spec(g+P/2,g+P-0.005); Sw=spec(g+0.03,g+P-0.005)
    beats.append(dict(beat=b,t=g,low=chroma(So,95,275,TUNE),mid=chroma(Sw,275,2000,TUNE),mid_off=chroma(So,275,2000,TUNE),low_e=float((So[(fr>=95)&(fr<=275)]**2).sum())))
QUAL={'':(0,4,7),'m':(0,3,7)}
def chord_scores(c):
    c=c/(np.linalg.norm(c)+1e-12); res=[]
    for r in range(12):
        for q,iv in QUAL.items():
            tpl=np.zeros(12); tpl[[(r+i)%12 for i in iv]]=1/np.sqrt(3); res.append((float(c@tpl),NAMES[r]+q))
    res.sort(reverse=True); return res
def top(c,n=4): 
    c=c/(c.sum()+1e-12); return ' '.join(f"{NAMES[i]}:{c[i]:.2f}" for i in np.argsort(c)[::-1][:n])
def norm(c): return c/(c.sum()+1e-12)
print('\nPER POSITION in the 24-beat verse (mean of normalised chroma over 7 verses):')
pos=[]
for p in range(24):
    bl=[vb+p for vb in VB if vb+p<NB]
    low=np.mean([norm(beats[b]['low']) for b in bl],0); mid=np.mean([norm(beats[b]['mid']) for b in bl],0); mo=np.mean([norm(beats[b]['mid_off']) for b in bl],0)
    comb=norm(low)+ (norm(mo) if p>=16 else 0*mo)       # vocal bars: low band only; instrumental bars: low + mid
    cs=chord_scores(comb); cl=chord_scores(low)
    # per-verse vote
    votes={}
    for b in bl:
        cv=norm(beats[b]['low'])+(norm(beats[b]['mid_off']) if p>=16 else 0)
        nm=chord_scores(cv)[0][1]; votes[nm]=votes.get(nm,0)+1
    pos.append(dict(position=p,bar=p//4,beat_in_bar=p%4,low_chroma=low.tolist(),mid_chroma=mid.tolist(),mid_offbeat_chroma=mo.tolist(),
                    chord=cs[0][1],chord_score=cs[0][0],chord2=cs[1][1],chord2_score=cs[1][0],chord_from_low_only=cl[0][1],per_verse_votes=votes))
    print(f"  pos {p:2d} (bar {p//4} beat {p%4}): low[{top(low)}] mid_off[{top(mo)}] -> {cs[0][1]:3s} {cs[0][0]:.2f} (2nd {cs[1][1]:3s} {cs[1][0]:.2f}) votes {votes}")
# ---------- chord per half bar (2 beats) and per bar ----------
print('\nCHORD PER HALF BAR (2 beats):')
half=[]
for h in range(12):
    pp=(2*h,2*h+1)
    low=np.mean([pos[p]['low_chroma'] for p in pp],0); mo=np.mean([pos[p]['mid_offbeat_chroma'] for p in pp],0)
    comb=norm(low)+(norm(mo) if h>=8 else 0)
    cs=chord_scores(comb)
    # third evidence from the low band alone and from the mid band (instrumental bars: clean; vocal bars: contaminated)
    r=NAMES.index(cs[0][1].rstrip('m'))
    third_low=dict(major=float(low[(r+4)%12]),minor=float(low[(r+3)%12])); third_mid=dict(major=float(mo[(r+4)%12]),minor=float(mo[(r+3)%12]))
    votes={}
    for vb in VB:
        bl=[vb+p for p in pp if vb+p<NB]
        if not bl: continue
        cv=norm(np.mean([norm(beats[b]['low']) for b in bl],0))+(norm(np.mean([norm(beats[b]['mid_off']) for b in bl],0)) if h>=8 else 0)
        nm=chord_scores(cv)[0][1]; votes[nm]=votes.get(nm,0)+1
    half.append(dict(half_bar=h,bar=h//2,beats=[2*(h%2),2*(h%2)+1],chord=cs[0][1],score=cs[0][0],second=cs[1][1],second_score=cs[1][0],root=NAMES[r],
                     third_evidence_low_band=third_low,third_evidence_mid_band_offbeat=third_mid,per_verse_votes=votes))
    print(f"  bar {h//2} beats {2*(h%2)}-{2*(h%2)+1}: {cs[0][1]:3s} {cs[0][0]:.2f} (2nd {cs[1][1]:3s} {cs[1][0]:.2f}) | 3rd low maj {third_low['major']:.3f} min {third_low['minor']:.3f} | 3rd mid maj {third_mid['major']:.3f} min {third_mid['minor']:.3f} | votes {votes}")
# ---------- key ----------
KS_MAJ=np.array([6.35,2.23,3.48,2.33,4.38,4.09,2.52,5.19,2.39,3.66,2.29,2.88]); KS_MIN=np.array([6.33,2.68,3.52,5.38,2.60,3.53,2.54,4.75,3.98,2.69,3.34,3.17])
def ks(c):
    res=[]
    for r in range(12):
        res.append((float(np.corrcoef(c,np.roll(KS_MAJ,r))[0,1]),NAMES[r]+' major')); res.append((float(np.corrcoef(c,np.roll(KS_MIN,r))[0,1]),NAMES[r]+' minor'))
    res.sort(reverse=True); return res[:5]
agg={'instrumental_bars_low+mid':np.mean([norm(beats[b]['low'])+norm(beats[b]['mid_off']) for b in inst],0),
     'all_bars_low_band_only_(vocal_free)':np.mean([norm(beats[b]['low']) for b in allb],0),
     'all_bars_mid_band_(with_vocal)':np.mean([norm(beats[b]['mid']) for b in allb],0),
     'intro_beats_1_14_mid':np.mean([norm(beats[b]['mid']) for b in range(1,15)],0)}
key={}
print('\nKEY (Krumhansl-Schmuckler):')
for k,c in agg.items():
    r=ks(c); key[k]=dict(chroma={NAMES[i]:float(norm(c)[i]) for i in range(12)},top5=[dict(key=n,r=s) for s,n in r])
    print(f"  {k}: "+', '.join(f"{n} {s:.2f}" for s,n in r)+'   | chroma '+top(c,7))
json.dump(dict(tuning=tun,positions=pos,half_bars=half,key_profiles=key,verse_onset_beats=VB,
               beats=[dict(beat=b['beat'],t=b['t'],low=norm(b['low']).tolist(),mid=norm(b['mid']).tolist(),mid_off=norm(b['mid_off']).tolist()) for b in beats]),open(O+'/key_chords.json','w'))
