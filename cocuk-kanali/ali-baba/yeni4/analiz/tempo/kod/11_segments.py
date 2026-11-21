# Step 3: the 35 sung segments (7 verses x L1, L2, ses, diye, L4) on the beat lattice.
#  - words from v2_2_words.json (20 ms grid, automatic alignment)
#  - bar lines: verse onset beat (nearest lattice beat to the first word) + 4 beats per bar; local phase check per verse
#  - onset refinement on the FULL MIX (no separated vocal exists): 300-3400 Hz ("vowel") and 2-7 kHz ("consonant")
#    envelopes at 1.45 ms hop, minus the beat-synchronous envelope of the band measured in the instrumental bars
#    (bars 4-5 of every verse, same phase inside the beat).  onset = first time after the preceding dip at which the
#    band-subtracted envelope reaches 25 % of the first-syllable peak.  Flagged unreliable when it disagrees with the
#    words file by more than 60 ms or when the vocal excess is small against the band.
import numpy as np, json, scipy.signal as ss, re
from common import *
P,PHI=lattice(); x=load_mix(); words=load_words()
assert len(words)==105, len(words)
VB=[int(round((words[15*v]['start']-PHI)/P)) for v in range(7)]
print('verse onset beats',VB,np.diff(VB).tolist())
NF=1024; HP=64; dt=HP/SR
f,t,S=ss.stft(x,SR,window='hann',nperseg=NF,noverlap=NF-HP,boundary='zeros',padded=True); S=np.abs(S)
def benv(lo,hi):
    e=np.sqrt((S[(f>=lo)&(f<=hi)]**2).sum(0)); k=np.hanning(7); k/=k.sum(); return np.convolve(e,k,mode='same')
ENV={'vowel_300_3400':benv(300,3400),'cons_2k_7k':benv(2000,7000)}
# band template: median over the instrumental beats, folded over one beat (bins of dt)
nbin=int(round(P/dt))
def template(e):
    rows=[]
    for vb in VB:
        for p in range(16,24):
            g=PHI+(vb+p)*P
            if g+P>t[-1]: continue
            rows.append(np.interp(g+np.arange(nbin)*P/nbin,t,e))
    return np.median(np.array(rows),0),np.percentile(np.array(rows),90,axis=0)
TPL={k:template(e) for k,e in ENV.items()}
def residual(k,ta,tb):
    """band-subtracted envelope on [ta,tb] (uses the 90th percentile of the band so that what remains is vocal excess)"""
    tt=np.arange(ta,tb,dt); e=np.interp(tt,t,ENV[k]); ph=((tt-PHI)%P)/P*nbin
    tpl=np.interp(ph,np.arange(nbin+1),np.append(TPL[k][1],TPL[k][1][0]))
    return tt,np.maximum(e-tpl,0),e,tpl
def refine(w0,first_text):
    cons=bool(re.match(r'^["“]?[çÇsSşŞkKtThHfF]',first_text))
    res={}
    for k in ENV:
        tt,r,e,tpl=residual(k,w0-0.16,w0+0.20)
        sm=np.convolve(r,np.ones(5)/5,mode='same')
        i0=int((0.16-0.13)/dt); i1=int((0.16+0.03)/dt)
        kmin=i0+int(np.argmin(sm[i0:i1]))
        ipk0=int(0.16/dt); pk=sm[ipk0:ipk0+int(0.14/dt)].max()
        idx=np.where(sm[kmin:]>=0.25*pk)[0]
        on=float(tt[kmin+idx[0]]) if len(idx) and pk>0 else None
        res[k]=dict(onset=on,peak_excess_over_band=float(pk/(tpl.mean()+1e-12)),dip_time=float(tt[kmin]),dip_level_rel_peak=float(sm[kmin]/(pk+1e-12)))
    pick='cons_2k_7k' if cons else 'vowel_300_3400'
    alt='vowel_300_3400' if cons else 'cons_2k_7k'
    on=res[pick]['onset']; rel=on is not None and abs(on-w0)<=0.06 and res[pick]['peak_excess_over_band']>=1.0 and res[pick]['dip_level_rel_peak']<0.25
    return on,rel,pick,res
# ---- local phase check per verse: steepest rise of the 120-300 Hz and 300-2000 Hz on-beat attack vs the lattice ----
def env_band(lo,hi,sm_ms=3.0):
    sos=ss.butter(4,[lo,hi],btype='band',fs=SR,output='sos'); y=ss.sosfiltfilt(sos,x)**2
    n=int(SR*sm_ms/1000); return np.sqrt(np.convolve(y,np.ones(n)/n,mode='same'))
EL=env_band(120,300); EM=env_band(300,2000)
def local_phase(e,b0,b1):
    ia=int((PHI+b0*P-P/2)*SR); ib=int((PHI+b1*P-P/2)*SR); tt=np.arange(ia,ib)/SR; nb=2286
    idx=np.minimum((((tt-PHI+P/2)%P)/P*nb).astype(int),nb-1)
    prof=np.bincount(idx,weights=e[ia:ib],minlength=nb)/np.maximum(np.bincount(idx,minlength=nb),1)
    k=np.hanning(9); k/=k.sum(); prof=np.convolve(prof,k,mode='same'); d=np.diff(prof); tb=np.arange(1,nb)/nb*P-P/2
    m=np.abs(tb)<=0.05; return float(tb[m][np.argmax(d[m])]*1000)
verses=[]; segs=[]
NAMES_SEG=[('L1',0,5,0,0.0),('L2',5,8,1,0.0),('ses',8,10,2,0.0),('diye',10,12,2,2.0),('L4',12,15,3,0.0)]
for v in range(7):
    W=words[15*v:15*v+15]; vb=VB[v]
    lp=dict(low_120_300_ms=local_phase(EL,vb,vb+24),mid_300_2000_ms=local_phase(EM,vb,vb+24))
    verses.append(dict(verse=v+1,onset_beat=vb,first_downbeat=PHI+vb*P,bar_downbeats=[PHI+(vb+4*k)*P for k in range(6)],
                       next_verse_downbeat=PHI+(vb+24)*P,local_attack_minus_lattice_ms=lp,animal_word=W[6]['text']))
    for name,a,b,bar,exp_beats in NAMES_SEG:
        ws=W[a:b]; w0=ws[0]['start']; w1=ws[-1]['end']
        dbt=PHI+(vb+4*bar)*P
        on,rel,pick,res=refine(w0,ws[0]['text'])
        onset=on if rel else w0
        segs.append(dict(verse=v+1,name=name,text=' '.join(w['text'] for w in ws),bar_in_verse=bar,beat_number_of_bar_downbeat=vb+4*bar,
            bar_downbeat=round(dbt,4),onset_words_file=w0,onset_refined=None if on is None else round(on,4),refined_reliable=bool(rel),refine_band=pick,
            onset=round(onset,4),end=w1,offset_sec=round(onset-dbt,4),offset_beats=round((onset-dbt)/P,4),
            offset_words_file_sec=round(w0-dbt,4),offset_words_file_beats=round((w0-dbt)/P,4),
            expected_beat_in_bar=exp_beats,deviation_from_expected_beat_ms=round((onset-dbt-exp_beats*P)*1000,1),
            deviation_words_file_ms=round((w0-dbt-exp_beats*P)*1000,1),
            end_beats_after_bar_downbeat=round((w1-dbt)/P,3),duration_s=round(w1-onset,3),
            refine_detail=res,
            words=[dict(text=w['text'],start=w['start'],end=w['end'],beats_from_verse_downbeat=round((w['start']-(PHI+vb*P))/P,3)) for w in ws]))
        s=segs[-1]
        print(f"v{v+1} {name:4s} bar {bar} db {dbt:7.3f} words {w0:6.2f} ({s['deviation_words_file_ms']:+6.1f} ms) refined {s['onset_refined']} rel={rel!s:5s} [{pick[:5]}] -> onset {onset:7.3f} off {s['offset_sec']:+.3f}s {s['offset_beats']:+.3f}b dev-from-expected {s['deviation_from_expected_beat_ms']:+6.1f} ms | end {w1:6.2f} ({s['end_beats_after_bar_downbeat']:.2f} b) | {s['text']}")
    print('   local attack vs lattice (ms):',lp)
def stats(a): a=np.array(a,float); return dict(n=int(len(a)),mean_ms=float(a.mean()),median_ms=float(np.median(a)),sd_ms=float(a.std()),min_ms=float(a.min()),max_ms=float(a.max()))
summ={}
for name in ('L1','L2','ses','diye','L4'):
    summ[name]=dict(adopted_onset=stats([s['deviation_from_expected_beat_ms'] for s in segs if s['name']==name]),
                    words_file=stats([s['deviation_words_file_ms'] for s in segs if s['name']==name]),
                    refined_only=stats([ (s['onset_refined']-s['bar_downbeat']-s['expected_beat_in_bar']*P)*1000 for s in segs if s['name']==name and s['refined_reliable']]) if any(s['name']==name and s['refined_reliable'] for s in segs) else None,
                    n_refined_reliable=sum(1 for s in segs if s['name']==name and s['refined_reliable']))
summ['all']=dict(adopted_onset=stats([s['deviation_from_expected_beat_ms'] for s in segs]),words_file=stats([s['deviation_words_file_ms'] for s in segs]),
                 n_refined_reliable=sum(1 for s in segs if s['refined_reliable']))
print(json.dumps(summ,indent=1))
# typical word positions (beats from the verse downbeat), median over 7 verses
typ=[]
for i in range(15):
    vals=[(words[15*v+i]['start']-(PHI+VB[v]*P))/P for v in range(7)]; ends=[(words[15*v+i]['end']-(PHI+VB[v]*P))/P for v in range(7)]
    typ.append(dict(index=i,text_verse1=words[i]['text'],median_start_beats=round(float(np.median(vals)),3),sd_start_beats=round(float(np.std(vals)),3),median_end_beats=round(float(np.median(ends)),3)))
print('typical word positions (beats from verse downbeat):',[(q['text_verse1'],q['median_start_beats']) for q in typ])
# vocal-only tempo from the words file: regression of the 35 segment onsets on their expected beat numbers
bn=np.array([s['beat_number_of_bar_downbeat']+s['expected_beat_in_bar'] for s in segs]); tw=np.array([s['onset_words_file'] for s in segs])
sl,ic=np.polyfit(bn,tw,1); r=tw-(ic+sl*bn)
voc=dict(beat_period_s=float(sl),bpm=float(60/sl),time_of_beat0_s=float(ic),residual_sd_ms=float(r.std()*1000),note='35 segment onsets of the words file regressed on lattice beat numbers')
print('vocal-only (words file) tempo:',voc)
json.dump(dict(verses=verses,segments=segs,offset_summary=summ,typical_word_positions=typ,vocal_only_tempo=voc),open(O+'/segments.json','w'),ensure_ascii=False,indent=1)
