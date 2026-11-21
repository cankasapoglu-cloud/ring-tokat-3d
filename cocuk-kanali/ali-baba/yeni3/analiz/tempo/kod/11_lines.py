# Step 3: metric position of the 28 sung lines.
#  - acoustic onset of the first syllable from the ISOLATED VOCAL (spectral-flux peak after the
#    preceding energy dip; includes an initial consonant such as "Ç" or "K"), cross-checked with a
#    plain envelope threshold (-20 dB re first-syllable peak) where the line is preceded by silence
#  - vowel onset (voiced band 90-1200 Hz reaches within 6 dB of the first-syllable peak)
#  - downbeat of the line's bar on the 116.00 BPM lattice (verse onset beat + 4*(line-1)),
#    on the mix timeline and converted to the vocal-stem timeline (measured linear lag)
#  - local checks per line / per verse that the lattice really sits on the kick there
#  - vocal-only tempo regression
import numpy as np, json, scipy.signal as ss
from common import *
P,PHI=lattice()      # refined lattice from 14_lattice.py
VB=[12,36,64,90,115,143,167]
x=load_mix(); v=load_vocal(); lines=json.load(open(O+'/lines_words.json'))
al=json.load(open(O+'/align_check.json')); al2=json.load(open(O+'/align_spectro.json'))

# ---- mix -> vocal timeline: lag(t) = a + b t (mix lags vocal). Two measurements, averaged ----
tm=np.array([L['words'][0]['start'] for L in lines])
el=np.array([r['env_lag_ms'] for r in al['per_line']]); es=np.array([r['lag_ms'] for r in al2['per_line']])
b1,a1=np.polyfit(tm,el,1); b2,a2=np.polyfit(tm,es,1)
a_lag=(a1+a2)/2; b_lag=(b1+b2)/2
def mix2voc(t): return t-(a_lag+b_lag*t)/1000.0
print('lag model: mix lags vocal by %.2f ms %+.4f ms/s * t  (envelope fit %.2f %+.4f ; spectro fit %.2f %+.4f)'%(a_lag,b_lag,a1,b1,a2,b2))

# ---- vocal features ----
NFv=512; HPv=32
f,t,S=stft_mag(v,NFv,HPv)
fl=flux(S,f,90,8000)
k5=np.hanning(9); k5/=k5.sum(); sm=np.convolve(fl,k5,mode='same'); sm/=np.percentile(sm,99.5)
def env_db(y,win_ms=5.0):
    n=int(SR*win_ms/1000); return 20*np.log10(np.sqrt(np.convolve(y**2,np.ones(n)/n,mode='same'))+1e-7)
sosv=ss.butter(4,[90,1200],btype='band',fs=SR,output='sos'); ev=env_db(ss.sosfiltfilt(sosv,v)); eb=env_db(v,10.0); eb5=env_db(v,5.0)

def acoustic_onset(t0,pre=0.09,post=0.03):
    """Acoustic start of a syllable in the vocal stem.
    1) energy dip: minimum of the 5 ms broadband envelope in [t0-pre, t0+post] (silence, or the closure of a stop
       in a legato join);  2) onset = first local maximum of the spectral flux after that dip whose height is at least
       half of the largest flux within the following 80 ms.  The flux peak marks the moment of fastest spectral rise."""
    a=int((t0-pre)*SR); b=int((t0+post)*SR)
    seg=eb5[a:b]; mn=seg.min()
    idx=np.where((seg<=mn+1.0)|(seg<=-70.0))[0]; t_dip=(a+idx[-1])/SR
    w=(t>=t_dip)&(t<=t_dip+0.08); tw=t[w]; sw=sm[w]
    thr=0.5*sw.max()
    for k in range(1,len(sw)-1):
        if sw[k]>=thr and sw[k]>=sw[k-1] and sw[k]>=sw[k+1]:
            y0,y1,y2=sw[k-1],sw[k],sw[k+1]; d=0.0 if (y0-2*y1+y2)==0 else 0.5*(y0-y2)/(y0-2*y1+y2)
            return float(tw[k]+d*HPv/SR),float(t_dip),float(mn)
    k=int(np.argmax(sw)); return float(tw[k]),float(t_dip),float(mn)
def vowel_onset(t_on):
    a=int(t_on*SR); b=int((t_on+0.15)*SR); pk=ev[a:b].max()
    idx=np.where(ev[a:b]>=pk-6.0)[0]
    return float((a+idx[0])/SR)
def env20_onset(t_on,t_dip):
    """independent check: first time after the dip where the 10 ms envelope exceeds (first-syllable peak - 20 dB)."""
    a=int(t_dip*SR); b=int((t_on+0.15)*SR); pk=eb[int(t_on*SR):b].max()
    if eb[a]>pk-30: return None          # not preceded by silence -> threshold method not applicable
    idx=np.where(eb[a:b]>=pk-20.0)[0]
    return float((a+idx[0])/SR)

# ---- mix: local kick check (40-120 Hz log-envelope rise) ----
E=np.load(CACHE+'/env.npz'); te,envA,envB=E['t'],E['envA'],E['envB']
def local_kick(tb):
    m=(te>=tb-0.06)&(te<=tb+0.06); k=np.argmax(envB[m]); return float(te[m][k]-tb),float(envB[m][k]/np.median(envB[(te>6)&(te<100)]+1e-12))
kick_ref=np.percentile(envB[(te>6)&(te<100)],95)

out_lines=[]
for i,L in enumerate(lines):
    vi,li=L['verse'],L['line']; w0=L['words'][0]; t0=w0['start']
    nb=VB[vi-1]+4*(li-1)
    db_mix=PHI+nb*P; db_voc=mix2voc(db_mix)
    on,tdip,dipdb=acoustic_onset(t0); vo=vowel_onset(on); e20=env20_onset(on,tdip)
    a=int((on-0.20)*SR); bq=int(on*SR); kq=a+int(np.argmin(eb[a:bq]))
    t_last=L['words'][-1]['end']
    lpk=eb[int(on*SR):int(t_last*SR)].max()
    # end of the line's sound: last time (up to the next line's onset, or +1.5 s) with envelope above line peak - 40 dB
    t_next=lines[i+1]['words'][0]['start']-0.03 if (i+1<len(lines) and lines[i+1]['verse']==vi) else t_last+1.5
    a2=int(L['words'][-1]['start']*SR); b2=int(t_next*SR); idx=np.where(eb[a2:b2]>=lpk-40.0)[0]; t_end=(a2+idx[-1])/SR
    kd,ks=local_kick(db_mix)
    m=(te>=db_mix-0.06)&(te<=db_mix+0.06)
    out_lines.append(dict(verse=vi,line=li,first_word=w0['text'],text=' '.join(w['text'] for w in L['words']),
        word_start_from_words_file=t0,onset=round(on,4),vowel_onset=round(vo,4),onset_env20_check=(round(e20,4) if e20 is not None else None),
        beat_number_on_lattice=nb,downbeat_mix_timeline=round(db_mix,4),downbeat=round(db_voc,4),
        offset_sec=round(on-db_voc,4),offset_beats=round((on-db_voc)/P,4),
        vowel_offset_sec=round(vo-db_voc,4),vowel_offset_beats=round((vo-db_voc)/P,4),
        words_file_offset_sec=round(t0-db_voc,4),
        kick_at_downbeat_rel_strength=round(float(envB[m].max()/kick_ref),2),kick_rise_peak_minus_lattice_ms=round(1000*kd,1),
        quietest_point_before_line=round(kq/SR,4),quietest_level_db_re_line_peak=round(float(eb[kq]-lpk),1),
        last_word_end_from_words_file=t_last,sound_end_minus40dB=round(t_end,4),sound_end_beats_after_downbeat=round((t_end-db_voc)/P,3),
        alt_H2_downbeat=round(db_voc+2*P,4),alt_H2_offset_beats=round((on-db_voc)/P-2,4)))
    assert abs(on-db_voc)<P/4, (vi,li,on,db_voc)
print('\n v L first        words   onset  (env20)  vowel   downbeat  off(ms) off(beats) vowel-off(ms) kick(rel, dev ms) quiet(dB) sound-end(beats)')
for r in out_lines:
    e20='   -   ' if r['onset_env20_check'] is None else f"{r['onset_env20_check']:7.3f}"
    print(f" {r['verse']} {r['line']} {r['first_word']:11s} {r['word_start_from_words_file']:6.2f} {r['onset']:7.3f} {e20} {r['vowel_onset']:7.3f} {r['downbeat']:8.3f}  {1000*r['offset_sec']:+6.1f}  {r['offset_beats']:+.3f}    {1000*r['vowel_offset_sec']:+6.1f}      {r['kick_at_downbeat_rel_strength']:.2f} {r['kick_rise_peak_minus_lattice_ms']:+5.1f}   {r['quietest_level_db_re_line_peak']:6.1f}   {r['sound_end_beats_after_downbeat']:.2f}")
off=np.array([r['offset_sec'] for r in out_lines]); voff=np.array([r['vowel_offset_sec'] for r in out_lines]); woff=np.array([r['words_file_offset_sec'] for r in out_lines])
def stats(a): return dict(n=int(len(a)),mean_ms=float(1000*a.mean()),median_ms=float(1000*np.median(a)),sd_ms=float(1000*a.std(ddof=1)),min_ms=float(1000*a.min()),max_ms=float(1000*a.max()),
                          median_beats=float(np.median(a)/P),mean_beats=float(a.mean()/P),sd_beats=float(a.std(ddof=1)/P),min_beats=float(a.min()/P),max_beats=float(a.max()/P))
st={'acoustic_onset_all28':stats(off),'vowel_onset_all28':stats(voff),'words_file_start_all28':stats(woff)}
for li in (1,2,3,4):
    m=np.array([r['line']==li for r in out_lines])
    st[f'acoustic_onset_line{li}']=stats(off[m]); st[f'vowel_onset_line{li}']=stats(voff[m])
for k,vv in st.items(): print(f"  {k:26s} mean {vv['mean_ms']:+6.1f} ms median {vv['median_ms']:+6.1f} sd {vv['sd_ms']:5.1f} range {vv['min_ms']:+6.1f}..{vv['max_ms']:+6.1f} | median {vv['median_beats']:+.3f} beats")
chk=np.array([r['onset']-r['onset_env20_check'] for r in out_lines if r['onset_env20_check'] is not None])
print('  flux-onset minus envelope(-20 dB)-onset where applicable: n=%d mean %+.1f ms sd %.1f max|.| %.1f ms'%(len(chk),1000*chk.mean(),1000*chk.std(),1000*np.abs(chk).max()))
st['flux_onset_minus_env20_onset']=dict(n=int(len(chk)),mean_ms=float(1000*chk.mean()),sd_ms=float(1000*chk.std()),max_abs_ms=float(1000*np.abs(chk).max()))
kd=np.array([r['kick_rise_peak_minus_lattice_ms'] for r in out_lines]); ks=np.array([r['kick_at_downbeat_rel_strength'] for r in out_lines])
print('  kick at the 28 downbeats: rise-peak minus lattice mean %+.1f ms sd %.1f (range %+.1f..%+.1f); strength re 95th pct: min %.2f median %.2f'%(kd.mean(),kd.std(),kd.min(),kd.max(),ks.min(),np.median(ks)))
st['kick_at_28_downbeats']=dict(rise_peak_minus_lattice_mean_ms=float(kd.mean()),sd_ms=float(kd.std()),min_ms=float(kd.min()),max_ms=float(kd.max()),rel_strength_min=float(ks.min()),rel_strength_median=float(np.median(ks)))

# ---- rhythm of every word inside its line (beats after the line's downbeat) ----
for L,r in zip(lines,out_lines):
    pos=[]
    for j,w in enumerate(L['words']):
        if j==0: on=r['onset']
        else:
            on,_,_=acoustic_onset(w['start'],pre=0.07,post=0.03)
            if abs(on-w['start'])>0.08: on=w['start']
        pos.append(dict(text=w['text'],start_words_file=w['start'],end_words_file=w['end'],beats_words_file=round((w['start']-r['downbeat'])/P,3),onset_refined=round(on,4),beats_refined=round((on-r['downbeat'])/P,3)))
    r['words']=pos
print('\nword positions (beats after the line downbeat, refined onsets):')
for r in out_lines:
    print(f"  v{r['verse']} L{r['line']}: "+'  '.join(f"{w['text']}@{w['beats_refined']:+.2f}" for w in r['words']))
# typical pattern per line type (median over verses, by word index, only where word counts agree)
typ={}
for li in (1,2,3,4):
    rows=[r for r in out_lines if r['line']==li]
    nw=np.bincount([len(r['words']) for r in rows]).argmax()
    sel=[r for r in rows if len(r['words'])==nw]
    typ[f'L{li}']=dict(n_verses_used=len(sel),words=[sel[0]['words'][j]['text'] for j in range(nw)],
        median_beats=[round(float(np.median([r['words'][j]['beats_refined'] for r in sel])),3) for j in range(nw)])
    print('  typical',f'L{li}',typ[f'L{li}'])

# ---- vocal-only tempo: regress onsets against lattice beat numbers ----
nbv=np.array([r['beat_number_on_lattice'] for r in out_lines],float)
def fit(tt,nn):
    A=np.vstack([nn,np.ones(len(nn))]).T; coef=np.linalg.lstsq(A,tt,rcond=None)[0]
    pred=A@coef; s=np.sqrt(((tt-pred)**2).sum()/(len(tt)-2)); se=s/np.sqrt(((nn-nn.mean())**2).sum())
    return coef[0],coef[1],s,se
pv,c0,s,se=fit(np.array([r['vowel_onset'] for r in out_lines]),nbv)
pa,c0a,sa,sea=fit(np.array([r['onset'] for r in out_lines]),nbv)
voc=dict(from_vowel_onsets=dict(beat_period_s=float(pv),bpm=float(60/pv),bpm_se=float(60/pv**2*se),residual_sd_ms=float(1000*s)),
         from_acoustic_onsets=dict(beat_period_s=float(pa),bpm=float(60/pa),bpm_se=float(60/pa**2*sea),residual_sd_ms=float(1000*sa)),
         note='onsets of the 28 lines (vocal-stem timeline) regressed on the lattice beat numbers; uses the mix only for the integer beat numbers')
iv=[]
for vi in range(1,8):
    o=[r['onset'] for r in out_lines if r['verse']==vi]; iv.append((o[3]-o[0])/12)
voc['within_verse_L1_to_L4_spacing']=dict(beat_period_s_per_verse=[round(float(q),5) for q in iv],mean_beat_period_s=float(np.mean(iv)),bpm=float(60/np.mean(iv)),bpm_sd_between_verses=float(np.std([60/q for q in iv],ddof=1)))
print('\nvocal-only tempo: vowel-onset fit %.3f +- %.3f BPM ; acoustic-onset fit %.3f +- %.3f BPM ; within-verse L1->L4 spacing %.3f BPM (sd %.2f)'%(60/pv,60/pv**2*se,60/pa,60/pa**2*sea,voc['within_verse_L1_to_L4_spacing']['bpm'],voc['within_verse_L1_to_L4_spacing']['bpm_sd_between_verses']))

# ---- per-verse local lattice phase with three estimates (fixed P) ----
sos=ss.butter(4,[8000,16000],btype='band',fs=SR,output='sos'); xa=ss.sosfiltfilt(sos,x)**2
nn=int(SR*0.003); ea=np.sqrt(np.convolve(xa,np.ones(nn)/nn,mode='same'))
loc=[]
for vi,vb in enumerate(VB):
    a=PHI+(vb-2)*P; b=PHI+(vb+18)*P
    def best_phase(env,period,nph=1200):
        ph=a+np.arange(nph)/nph*period
        sc=np.array([grid_score(env,te,period,p,a,b) for p in ph]); return ph[sc.argmax()]
    pA=best_phase(envA,P); pB=best_phase(envB,P)
    dA=((pA-PHI-P/2+P/2)%P)-P/2          # method A sits on the off-beat: compare with lattice + P/2
    dB=((pB-PHI+P/2)%P)-P/2
    # hats 8-16 kHz: folded envelope, steepest rise within +-60 ms of the lattice beat
    ia=int(a*SR); ib=int(b*SR); tt=np.arange(ia,ib)/SR; nbin=1034
    idx=np.minimum((((tt-PHI+P/2)%P)/P*nbin).astype(int),nbin-1)
    prof=np.bincount(idx,weights=ea[ia:ib],minlength=nbin)/np.maximum(np.bincount(idx,minlength=nbin),1)
    d=np.diff(prof); tb=(np.arange(1,nbin))/nbin*P-P/2
    m=np.abs(tb)<=0.06; dC=float(tb[m][np.argmax(d[m])])
    loc.append(dict(verse=vi+1,window_mix_timeline=[round(a,3),round(b,3)],
        methodA_fullband_flux_phase_minus_lattice_plus_half_beat_ms=round(float(1000*dA),1),
        methodB_kick_phase_minus_lattice_ms=round(float(1000*dB),1),
        hat_8_16k_steepest_rise_minus_lattice_ms=round(1000*dC,1)))
    print(f"  verse {vi+1}: A(full-band flux) = lattice + half beat {1000*dA:+.1f} ms ; B(kick) = lattice {1000*dB:+.1f} ms ; hats(8-16k) = lattice {1000*dC:+.1f} ms")
json.dump(dict(lines=out_lines,offset_stats=st,typical_word_positions=typ,vocal_only_tempo=voc,per_verse_local_phase=loc,
               mix_to_vocal_timeline=dict(lag_ms_at_t0=float(a_lag),lag_slope_ms_per_s=float(b_lag),
                    envelope_method=dict(intercept_ms=float(a1),slope_ms_per_s=float(b1)),spectro_method=dict(intercept_ms=float(a2),slope_ms_per_s=float(b2)),
                    formula='t_vocal = t_mix - (lag_ms_at_t0 + lag_slope_ms_per_s * t_mix)/1000')),
          open(O+'/lines_step3.json','w'),ensure_ascii=False,indent=1)
