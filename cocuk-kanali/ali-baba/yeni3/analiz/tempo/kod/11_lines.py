# Step 3: metric position of the 28 sung lines.
#  - acoustic onset of the first syllable from the ISOLATED VOCAL (spectral-flux peak after the
#    preceding quiet valley; includes an initial consonant such as "Ç" or "K")
#  - vowel onset (voiced band 90-1200 Hz reaches within 6 dB of the first-syllable peak)
#  - downbeat of the line's bar on the 116.00 BPM lattice (verse onset beat + 4*(line-1)),
#    given on the mix timeline and converted to the vocal-stem timeline (measured linear lag)
#  - per-verse local phase check of the lattice with both methods, vocal-only tempo regression
import numpy as np, json, scipy.signal as ss
from common import *
P=60/116.0; PHI=0.0015
VB=[12,36,64,90,115,143,167]
v=load_vocal(); lines=json.load(open(O+'/lines_words.json'))
al=json.load(open(O+'/align_check.json'))

# ---- mix -> vocal timeline: lag(t) = a + b t (mix lags vocal), from per-line envelope correlation ----
tm=np.array([L['words'][0]['start'] for L in lines]); el=np.array([r['env_lag_ms'] for r in al['per_line']])
b_lag,a_lag=np.polyfit(tm,el,1); resid=el-(a_lag+b_lag*tm)
def mix2voc(t): return t-(a_lag+b_lag*t)/1000.0
print('lag model: mix lags vocal by %.2f ms %+.4f ms/s * t ; residual sd %.2f ms'%(a_lag,b_lag,resid.std()))

# ---- vocal features ----
NFv=512; HPv=32
f,t,S=stft_mag(v,NFv,HPv)
fl=flux(S,f,90,8000)
k5=np.hanning(9); k5/=k5.sum(); sm=np.convolve(fl,k5,mode='same')     # ~3 ms effective smoothing
sm/=np.percentile(sm,99.5)
def env_db(y,win_ms=5.0):
    n=int(SR*win_ms/1000); return 20*np.log10(np.sqrt(np.convolve(y**2,np.ones(n)/n,mode='same'))+1e-7)
sosv=ss.butter(4,[90,1200],btype='band',fs=SR,output='sos'); ev=env_db(ss.sosfiltfilt(sosv,v)); eb=env_db(v,10.0); eb5=env_db(v,5.0)
def at(e,tt): return e[int(round(tt*SR))]

def acoustic_onset(t0,pre=0.09,post=0.03):
    """Acoustic start of a syllable in the vocal stem.
    1) energy dip: minimum of the 5 ms broadband envelope in [t0-pre, t0+post] (silence, or the closure of a stop
       in a legato join);  2) onset = first local maximum of the spectral flux after that dip whose height is at least
       half of the largest flux within the following 80 ms.  The flux peak marks the moment of fastest spectral rise."""
    a=int((t0-pre)*SR); b=int((t0+post)*SR)
    seg=eb5[a:b]; mn=seg.min()
    # last sample of the dip (within 1 dB of the minimum, or below -70 dB = silence)
    idx=np.where((seg<=mn+1.0)|(seg<=-70.0))[0]; t_dip=(a+idx[-1])/SR
    w=(t>=t_dip)&(t<=t_dip+0.08); tw=t[w]; sw=sm[w]
    thr=0.5*sw.max()
    for k in range(1,len(sw)-1):
        if sw[k]>=thr and sw[k]>=sw[k-1] and sw[k]>=sw[k+1]:
            y0,y1,y2=sw[k-1],sw[k],sw[k+1]; d=0.0 if (y0-2*y1+y2)==0 else 0.5*(y0-y2)/(y0-2*y1+y2)
            return float(tw[k]+d*HPv/SR),float(t_dip),float(sw[k])
    k=int(np.argmax(sw)); return float(tw[k]),float(t_dip),float(sw[k])
def vowel_onset(t_on):
    a=int(t_on*SR); b=int((t_on+0.15)*SR); pk=ev[a:b].max()
    idx=np.where(ev[a:b]>=pk-6.0)[0]
    return float((a+idx[0])/SR),float(pk)

out_lines=[]
for L in lines:
    vi,li=L['verse'],L['line']; w0=L['words'][0]; t0=w0['start']
    nb=VB[vi-1]+4*(li-1)
    db_mix=PHI+nb*P; db_voc=mix2voc(db_mix)
    on,tval,h=acoustic_onset(t0); vo,pk=vowel_onset(on)
    # quietest point between the previous word and this line (cut-point candidate), level re line peak
    a=int((on-0.20)*SR); bq=int(on*SR); kq=a+int(np.argmin(eb[a:bq])); 
    lpk=eb[int(on*SR):int(L['words'][-1]['end']*SR)].max()
    # end of the line's sound: last time the 10 ms envelope is above (line peak - 40 dB) before the next line / +1.2 s
    t_last=L['words'][-1]['end']
    out_lines.append(dict(verse=vi,line=li,first_word=w0['text'],text=' '.join(w['text'] for w in L['words']),
        word_start_from_words_file=t0,onset=round(on,4),vowel_onset=round(vo,4),
        beat_number_on_lattice=nb,downbeat_mix_timeline=round(db_mix,4),downbeat=round(db_voc,4),
        offset_sec=round(on-db_voc,4),offset_beats=round((on-db_voc)/P,4),
        vowel_offset_sec=round(vo-db_voc,4),vowel_offset_beats=round((vo-db_voc)/P,4),
        words_file_offset_sec=round(t0-db_voc,4),
        quietest_point_before_line=round(kq/SR,4),quietest_level_db_re_line_peak=round(float(eb[kq]-lpk),1),
        last_word_end_from_words_file=t_last,last_word_end_beats_after_downbeat=round((t_last-db_voc)/P,3)))
    assert abs(on-db_voc)<P/4, (vi,li,on,db_voc)
print('\n v L first        words   onset   vowel   downbeat  off(ms) off(beats) vowel-off(ms) quiet-before(dB)')
for r in out_lines:
    print(f" {r['verse']} {r['line']} {r['first_word']:11s} {r['word_start_from_words_file']:6.2f} {r['onset']:7.3f} {r['vowel_onset']:7.3f} {r['downbeat']:8.3f}  {1000*r['offset_sec']:+6.1f}  {r['offset_beats']:+.3f}    {1000*r['vowel_offset_sec']:+6.1f}      {r['quietest_level_db_re_line_peak']:6.1f}")
off=np.array([r['offset_sec'] for r in out_lines]); voff=np.array([r['vowel_offset_sec'] for r in out_lines]); woff=np.array([r['words_file_offset_sec'] for r in out_lines])
def stats(a): return dict(mean_ms=float(1000*a.mean()),median_ms=float(1000*np.median(a)),sd_ms=float(1000*a.std(ddof=1)),min_ms=float(1000*a.min()),max_ms=float(1000*a.max()),
                          median_beats=float(np.median(a)/P),mean_beats=float(a.mean()/P),sd_beats=float(a.std(ddof=1)/P))
st={'acoustic_onset_all28':stats(off),'vowel_onset_all28':stats(voff),'words_file_start_all28':stats(woff)}
for li in (1,2,3,4):
    m=np.array([r['line']==li for r in out_lines])
    st[f'acoustic_onset_line{li}']=stats(off[m]); st[f'vowel_onset_line{li}']=stats(voff[m])
for k,vv in st.items(): print(f"  {k:26s} mean {vv['mean_ms']:+6.1f} ms median {vv['median_ms']:+6.1f} sd {vv['sd_ms']:5.1f} range {vv['min_ms']:+6.1f}..{vv['max_ms']:+6.1f} | median {vv['median_beats']:+.3f} beats")

# ---- rhythm of every word inside its line (beats after the line's downbeat) ----
rh={}
for L,r in zip(lines,out_lines):
    key=f"L{L['line']}"
    pos=[]
    for w in L['words']:
        try:
            on,_,_=acoustic_onset(w['start'],pre=0.07,post=0.03)
            if abs(on-w['start'])>0.08: on=w['start']
        except Exception: on=w['start']
        pos.append(dict(text=w['text'],start_words_file=w['start'],beats_words_file=round((w['start']-r['downbeat'])/P,3),onset_refined=round(on,4),beats_refined=round((on-r['downbeat'])/P,3)))
    r['words']=pos
print('\nword positions (beats after the line downbeat, refined onsets):')
for r in out_lines:
    print(f"  v{r['verse']} L{r['line']}: "+'  '.join(f"{w['text']}@{w['beats_refined']:+.2f}" for w in r['words']))

# ---- vocal-only tempo: regress onsets against lattice beat numbers ----
nbv=np.array([r['beat_number_on_lattice'] for r in out_lines],float)
def fit(tt,nn):
    A=np.vstack([nn,np.ones(len(nn))]).T; coef,res,_,_=np.linalg.lstsq(A,tt,rcond=None)
    pred=A@coef; s=np.sqrt(((tt-pred)**2).sum()/(len(tt)-2)); se=s/np.sqrt(((nn-nn.mean())**2).sum())
    return coef[0],coef[1],s,se
pv,c0,s,se=fit(np.array([r['vowel_onset'] for r in out_lines]),nbv)
pa,c0a,sa,sea=fit(np.array([r['onset'] for r in out_lines]),nbv)
voc=dict(from_vowel_onsets=dict(beat_period_s=float(pv),bpm=float(60/pv),bpm_se=float(60/pv**2*se),intercept_s=float(c0),residual_sd_ms=float(1000*s)),
         from_acoustic_onsets=dict(beat_period_s=float(pa),bpm=float(60/pa),bpm_se=float(60/pa**2*sea),intercept_s=float(c0a),residual_sd_ms=float(1000*sa)),
         note='onsets of the 28 lines (vocal-stem timeline) regressed on the lattice beat numbers 12,16,...; independent of the mix except for the integer beat numbers')
# within-verse only (line-to-line spacing, 3 intervals of 4 beats per verse)
iv=[]
for vi in range(1,8):
    o=[r['vowel_onset'] for r in out_lines if r['verse']==vi]; iv+=list(np.diff(o)/4)
voc['within_verse_line_spacing']=dict(mean_beat_period_s=float(np.mean(iv)),bpm=float(60/np.mean(iv)),sd_ms_per_beat=float(1000*np.std(iv,ddof=1)),n_intervals=len(iv))
print('\nvocal-only tempo:',json.dumps(voc,indent=0)[:600])

# ---- per-verse local lattice phase with both methods (fixed P) ----
E=np.load(O+'/env.npz'); te,envA,envB=E['t'],E['envA'],E['envB']
loc=[]
for vi,vb in enumerate(VB):
    a=PHI+(vb-2)*P; b=PHI+(vb+18)*P
    def best_phase(env,period,nph=600):
        ph=a+np.arange(nph)/nph*period
        sc=np.array([grid_score(env,te,period,p,a,b) for p in ph]); return ph[sc.argmax()],sc.max()/env[(te>=a)&(te<=b)].mean()
    pA,sA=best_phase(envA,P); pB,sB=best_phase(envB,P); pA8,sA8=best_phase(envA,P/2)
    dA=((pA-PHI-P/2+P/2)%P)-P/2          # method A sits on the off-beat: compare with lattice + P/2
    dB=((pB-PHI+P/2)%P)-P/2
    dA8=((pA8-PHI+P/4)%(P/2))-P/4
    loc.append(dict(verse=vi+1,window=[round(a,3),round(b,3)],
        methodA_flux_beat_phase_dev_from_lattice_plus_half_beat_ms=float(1000*dA),methodA_score=float(sA),
        methodA_eighth_lattice_dev_ms=float(1000*dA8),
        methodB_kick_phase_dev_from_lattice_ms=float(1000*dB),methodB_score=float(sB)))
    print(f"  verse {vi+1}: method A (flux) lands on lattice+half beat {1000*dA:+.1f} ms (eighth-lattice dev {1000*dA8:+.1f} ms); method B (kick) dev {1000*dB:+.1f} ms")
json.dump(dict(lines=out_lines,offset_stats=st,vocal_only_tempo=voc,per_verse_local_phase=loc,
               mix_to_vocal_timeline=dict(lag_ms_at_t0=float(a_lag),lag_slope_ms_per_s=float(b_lag),residual_sd_ms=float(resid.std()),
                    formula='t_vocal = t_mix - (lag_ms_at_t0 + lag_slope_ms_per_s * t_mix)/1000')),
          open(O+'/lines_step3.json','w'),ensure_ascii=False,indent=1)
