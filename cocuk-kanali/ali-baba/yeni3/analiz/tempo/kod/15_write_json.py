# Assemble tempo.json (the deliverable) from the step results.
import numpy as np, json
from common import *
J=lambda n: json.load(open(O+'/'+n))
t1=J('tempo_step1.json'); pf=J('phase_fine.json'); dr=J('drift_fine.json'); lat=J('lattice.json'); de=J('downbeat_evidence.json')
bn=J('bass_notes.json'); l3=J('lines_step3.json'); al=J('align_check.json'); als=J('align_spectro.json')
P,PHI=lattice(); VB=[12,36,64,90,115,143,167]
m2v=l3['mix_to_vocal_timeline']
scale=1-m2v['lag_slope_ms_per_s']/1000.0
P_voc=P*scale; bpm_voc=60/P_voc
E=np.load(CACHE+'/env.npz'); te,envA,envB=E['t'],E['envA'],E['envB']
nb0,nb1=12,195
on=PHI+np.arange(nb0,nb1)*P; offb=on+P/2
def at(env,tt): return np.interp(tt,te,env)
ratioA=float(at(envA,offb).mean()/at(envA,on).mean()); ratioB=float(at(envB,on+0.004).mean()/at(envB,offb+0.004).mean())
# kick present on every beat of the body?
def pk(env,g,w=0.05):
    return np.array([env[(te>=q-w)&(te<=q+w)].max() for q in g])
kb=pk(envB,on); thr=0.25*np.median(kb)
kick_every_beat=dict(beats_checked=int(len(kb)),beats_with_kick_rise_above_quarter_of_median=int((kb>thr).sum()),
                     weakest_beats=[dict(beat=int(nb0+i),t=round(float(on[i]),3),rel=round(float(kb[i]/np.median(kb)),2)) for i in np.argsort(kb)[:4]])

# ---------- tempo ----------
A=t1['A_spectral_flux_fullband']; B=t1['B_lowfreq_40_120Hz']; lib=pf['librosa_beat_track']
tempo=dict(
  search_range_bpm=[110,122],
  method_A_fullband_spectral_flux=dict(description='onset envelope = half-wave rectified log-magnitude spectral flux 30 Hz-16 kHz (hop 5.8 ms); tempo/phase = (BPM, phase) maximising the mean envelope on the beat grid; autocorrelation as a second read-out',
       global_grid_search=A['global'],autocorrelation_bpm_at_1_4_8_16_beats=A['acf_global'],windows_20s=A['windows_20s'],
       fine_search_step_0p001=dr['fine_global_grid_search_step_0.001bpm']['A_fullband_flux']),
  method_B_kick_lowfreq_40_120Hz=dict(description='kick/bass band 40-120 Hz amplitude envelope, log-rise half-wave rectified; same grid search and autocorrelation',
       global_grid_search=B['global'],autocorrelation_bpm_at_1_4_8_16_beats=B['acf_global'],windows_20s=B['windows_20s'],
       fine_search_step_0p001=dr['fine_global_grid_search_step_0.001bpm']['B_kick_lf']),
  third_opinion_librosa_beat_track=dict(tempo_bpm=lib['tempo_bpm'],median_inter_beat_s=lib['median_ibi_s'],n_beats=lib['n_beats'],
       beat_phase_circular_mean_s=lib['circ_mean_phase_s'],phase_concentration_R=lib['phase_concentration_R'],
       note='librosa quantises to its 5.8 ms hop (89 frames = 0.51664 s = 116.13 BPM); like method A it locks to the OFF-beat eighth (phase about 0.274 s = half a beat + ~15 ms)'),
  per_window_summary=dict(window_s=20,hop_s=10,bpm_min_A=min(w['bpm'] for w in A['windows_20s']),bpm_max_A=max(w['bpm'] for w in A['windows_20s']),
       bpm_min_B=min(w['bpm'] for w in B['windows_20s']),bpm_max_B=max(w['bpm'] for w in B['windows_20s']),
       max_abs_phase_dev_from_global_grid_ms_A=max(abs(w['dev_from_global_grid_ms']) for w in A['windows_20s']),
       max_abs_phase_dev_from_global_grid_ms_B=max(abs(w['dev_from_global_grid_ms']) for w in B['windows_20s']),
       note='window search step 0.02 BPM; a 20 s window resolves about +-0.03 BPM'),
  fine_drift_check=dict(description='10 s windows every 5 s: position (ms) of the steepest rise of full-rate band envelopes folded over an exact 116.000 BPM beat; a straight line = constant tempo slightly different from 116.000',
       window_centres_s=dr['window_centres_s'],bands={k:v for k,v in dr.items() if isinstance(v,dict) and 'dev_ms' in v}),
  refined_lattice_mix_timeline=lat,
  vocal_only=l3['vocal_only_tempo'],
  result=dict(bpm_mix_timeline=lat['bpm'],bpm_vocal_stem_timeline=bpm_voc,beat_period_s_mix=P,beat_period_s_vocal_stem=P_voc,
       tempo_stable=True,
       statement='Tempo is constant (machine grid). Mix: 116.006 BPM; the isolated-vocal file runs 78 ppm faster than the decoded mix, so on the vocal file the same grid is 116.015 BPM. Both round to 116.0; the difference from exactly 116.000 is 5 ms (mix) / 13 ms (vocal file) over 100 s and less than 1 ms inside one 2-bar chunk.'))

# ---------- beat phase ----------
bands_fine={k:{kk:vv for kk,vv in v.items() if kk!='profile'} for k,v in pf.items() if k!='librosa_beat_track'}
beat_phase=dict(
  lattice_mix_timeline=dict(formula='beat n at phase_first_beat_s + n*beat_period_s',phase_first_beat_s=PHI,beat_period_s=P),
  lattice_vocal_stem_timeline=dict(formula='t_vocal = t_mix - (lag_ms_at_t0 + lag_slope_ms_per_s*t_mix)/1000',phase_first_beat_s=float(PHI-(m2v['lag_ms_at_t0']+m2v['lag_slope_ms_per_s']*PHI)/1000),beat_period_s=P_voc),
  method_A_phase_s=A['global']['phase_first_beat_s'],method_B_phase_s=B['global']['phase_first_beat_s'],
  methods_compared=dict(difference_s=float(A['global']['phase_first_beat_s']-B['global']['phase_first_beat_s']),half_beat_s=P/2,
       eighth_note_lattice_disagreement_ms=float(1000*((A['global']['phase_first_beat_s']-B['global']['phase_first_beat_s'])-P/2)),
       statement='The two methods agree on the eighth-note lattice within about 6 ms but choose different halves: full-band flux (A) and librosa lock to the off-beat eighth, the kick band (B) to the on-beat eighth.'),
  half_beat_question=dict(
       observation='Drum/accompaniment pattern is "boom-chick": kick + bass note + hat on one eighth, chord strum/"chick" (300 Hz-8 kHz) + hat on the other eighth.',
       fullband_flux_offbeat_over_onbeat=ratioA,kick_env_onbeat_over_offbeat=ratioB,kick_every_beat=kick_every_beat,
       band_attack_position_inside_beat_ms_coarse_116_000_fold=bands_fine,
       decision='beat = the kick/bass eighth',
       reasons=['kick drum sounds on every one of these eighths (four on the floor) and the bass notes change there (root/fifth)',
                'the file itself starts on that eighth (first transient at t = 0.00 s) and the intro accents fall on it',
                'all 28 sung lines begin within -41..+14 ms of such an eighth; with the opposite choice every line and almost every stressed syllable would be syncopated by exactly half a beat',
                'full-band onset methods prefer the other eighth only because the mid/high "chick" has more spectral flux than the kick'],
       confidence='high'),
  per_verse_local_phase_check=l3['per_verse_local_phase'],
  per_verse_note='Deviation (ms) of three local estimates from the global lattice in a 20-beat window around each verse. Hats and kick stay within +-7 ms and show no trend, so one global lattice is valid at every verse; only the BAR phase changes between verses.')

# ---------- downbeat ----------
rows=bn['rows']
def seq(b0,b1): return ' '.join(rows[b]['pc'] for b in range(b0,min(b1,len(rows))))
barmap=[]
for i,vb in enumerate(VB):
    end=VB[i+1] if i+1<len(VB) else vb+28
    bars=[seq(b,min(b+4,end)) for b in range(vb,end,4)]
    gap=end-vb-16
    barmap.append(dict(verse=i+1,onset_beat_number=vb,onset_beat_mod4_on_a_global_4_grid=vb%4,beats_until_next_verse=end-vb,gap_beats_after_L4=gap,gap_bars=gap/4,
                       bass_pitch_class_per_beat_in_4_beat_groups_from_verse_onset=bars))
pcs=bn['pc_by_position_mod4']
turn={p:int(pcs[str(p)].get('B',0)+pcs[str(p)].get('C',0)) for p in range(4)}
tot={p:int(sum(pcs[str(p)].values())) for p in range(4)}
fold=de['fold_mod4_relative_to_verse_onset']
def f4(key): return [round(v[0],3) for v in fold[key]]
ib=de['intro_beats']
gl=de['gap_beat_listing']
brk=[g for g in gl if g['verse']==3 and g['beat']==89][0]
downbeat=dict(
  bars_are='4 beats (2.069 s); the original has an irregular number of beats between verses, so the bar phase is anchored per verse',
  verse_onset_beat_numbers=VB,verse_onset_beat_spacing=list(np.diff(VB).astype(int).tolist()),verse_onset_beat_mod4_on_one_global_4_grid=[b%4 for b in VB],
  hypotheses=[
    dict(id='H0',statement='each sung line starts ON the downbeat of its bar (line onset beat = beat 1)',line_offset_beats='about -0.03 (acoustic) / +0.01 (vowel)',verdict='RECOMMENDED'),
    dict(id='H2',statement='bar lines lie two beats later: each line starts on beat 3 of the previous bar (half-bar pickup)',line_offset_beats='about -2.03',verdict='not supported; cannot be excluded by drum accents alone (the drum loop repeats every beat)'),
    dict(id='H1/H3',statement='bar lines one beat earlier or later (line starts on beat 2 or 4)',verdict='rejected: bass root (A) is on the line-onset beat and two beats later, the fifth (E) on the beats between, in all 7 verses'),
    dict(id='H_half',statement='the beat is the "chick" eighth and lines are half-beat pickups',verdict='rejected, see beat_phase.half_beat_question')],
  recommended='H0',
  evidence=dict(
    E1_intro=dict(text='The file starts with a 4-beat guitar/banjo pattern that repeats from t=0: strongest on-beat attacks on beats 0, 4, 8, a chord colour change (G) on beats 3 and 7, drums enter with a 2-beat fill on beats 10-11, and verse 1 starts on beat 12 = 3 bars after the start.',
        onbeat_mid_attack_strength_beats_0_to_11=[round(b['mid_on'],2) for b in ib[:12]],accompaniment_top_pitch_classes_beats_0_to_11=[b['mid_top'] for b in ib[:12]],
        kick_strength_beats_8_to_13=[round(b['kick'],2) for b in ib[8:14]]),
    E2_bass_pattern=dict(text='Bass per beat, counted from each verse onset: position 0 = A (root), 1 = E (fifth), 2 = A, 3 = E or a turnaround note (B or C leading back to A). The turnaround note occurs only on position 3, i.e. on the last beat before a line-onset-type beat.',
        bass_pitch_class_counts_by_position=pcs,turnaround_B_or_C_count_by_position=turn,beats_counted_by_position=tot,
        bassA_share_by_position=f4('bassA_all')),
    E3_harmony=dict(text='Accompaniment chroma by position: tonic colour strongest on position 0, dominant (E major triad) strongest on position 3, extra colour tones (F, C) on position 2. The only real chord change inside a verse (to the dominant) happens at the start of line 4 (position 12 = a line onset).',
        tonic_share_by_position=f4('tonA_all'),dominant_share_by_position=f4('domE_all'),F_C_colour_share_by_position=f4('colFC_all')),
    E4_same_alignment_in_all_verses=dict(text='The 16-beat chroma sequence under the vocal of verses 2-7 matches verse 1 best at shift 0 beats (not at +-2 or +-4): the accompaniment is locked to the sung lines identically in every verse.',
        best_shift_per_verse=[c['best_shift'] for c in de['cross_verse_alignment_vs_verse1']],
        similarity_at_shift_0=[round(c['sim_by_shift']['0'],2) for c in de['cross_verse_alignment_vs_verse1']],
        best_other_shift_similarity=[round(max(v for k,v in c['sim_by_shift'].items() if k!='0'),2) for c in de['cross_verse_alignment_vs_verse1']]),
    E5_structure_between_verses=dict(text='After line 4 the band continues in 4-beat groups that start exactly where line 4 ends, and a turnaround bar-end (bass B/C, no off-beat kick) sits on the last beat before the next verse in 4 of 6 transitions. The two irregular transitions are an inserted 2-beat break before verse 4 (everything stops on the off-beat at 46.30 s) and one extra beat before verse 5. So the irregular bars are in the instrumental gaps, not inside the sung verses.',
        original_bar_map=barmap,break_before_verse4=dict(beat=89,t=round(brk['t'],3),offbeat_mid_flux_rel=round(brk['mid_off'],2),offbeat_high_flux_rel=round(brk['hi_off'],2))),
    E6_periodicity=dict(text='Beat-feature self-similarity is higher at lag 4 than at lag 2 and at lag 8 than at lag 6: a 4-beat unit exists.',selfsim_by_lag_beats={k:round(v,3) for k,v in de['beat_feature_selfsim_by_lag'].items()}),
    E7_weak_or_neutral=dict(text='Drum accents do not separate H0 from H2: kick and hats repeat every beat. Small 4-beat cues: off-beat low-frequency hit after position 1, slightly more cymbal energy on position 0, slightly more low-band pickup after position 3.',
        offbeat_kick_flux_by_position=f4('kick_off_all'),cymbal_energy_by_position=f4('air_energy_all'),offbeat_low_flux_by_position=f4('low_off_all')),
    E8_lyrics=dict(text='Judgement, not measurement: every line is a closed unit that starts with a syllable exactly on a beat and ends on/after the 4th beat (L1: syllables on 0, 0.5, 1.5, 1.9, 3.0; L4: 0, 1, 2, 3). With H0 that is "one line = one bar", which is also how Old MacDonald is phrased; with H2 every line would straddle a bar line.',
        typical_word_positions_beats=l3['typical_word_positions'])),
  confidence=dict(beat_lattice_and_tempo='high',line_onsets_are_on_a_strong_beat_not_pickups='high',
       that_strong_beat_is_beat_1_rather_than_beat_3='medium-high (harmonic and structural evidence, all pointing the same way; no drum-accent proof; not checked by ear)'),
  practical_consequence='For re-placing the lines it does not matter whether H0 or H2 is true: the line onset sits on a root-bass beat in both, and the new form puts each line at the start of a bar. Use the downbeat times given per line.')

# ---------- lines ----------
lines=[]
for r in l3['lines']:
    q=dict(r); lines.append(q)
st=l3['offset_stats']
summary=dict(
  bpm=round(bpm_voc,3),bpm_note='on the timeline of dinle_2_vokal.wav (the file the lines are cut from); 116.006 on the decoded dinle_2.mp3; use 116.0 for the new backing',
  bpm_mix_timeline=round(lat['bpm'],4),recommended_bpm_for_new_backing=116.0,
  beat_sec=round(P_voc,6),bar_sec=round(4*P_voc,6),beat_sec_at_116_0=round(60/116.0,6),bar_sec_at_116_0=round(240/116.0,6),
  tempo_stable=True,meter='4/4 at 116 (drum loop is a 1-beat boom-chick; harmonic unit 4 beats)',
  lines_start_on_downbeat=True,
  typical_offset_beats=round(st['acoustic_onset_all28']['median_beats'],4),typical_offset_ms=round(st['acoustic_onset_all28']['median_ms'],1),
  offset_spread=dict(acoustic_onset=st['acoustic_onset_all28'],vowel_onset=st['vowel_onset_all28'],per_line_type={k:v for k,v in st.items() if 'line' in k and 'all' not in k}),
  statement='All 28 lines start ON the downbeat, none is a pickup. The first sound of a line (including consonants like "Ç", "K") begins on average 18 ms before the downbeat (range -41..+14 ms, SD 14 ms = 0.03 beat); the first vowel is reached on average 9 ms after it (median +3 ms, range -19..+55 ms). Line 2 ("Çiftliğinde") has the largest spread between the two: consonant 34 ms early, vowel 37 ms late. A half-beat pickup would be -259 ms.',
  placement_recipe='To keep the same feel on a new 116 BPM backing: for each line (or the L3+L4 chunk) put the sample at time `downbeat` of dinle_2_vokal.wav exactly on the new bar line, i.e. new_time = new_bar_start + (t - downbeat). Start the cut at least 60 ms before the downbeat (earliest sound is 41 ms early); `quietest_point_before_line` gives a clean cut point before L1, L2 and L3 (dip of -41 dB or deeper); L3->L4 is legato (dip only -11..-27 dB) and should stay one chunk.',
  confidence='beat grid/tempo and "on the beat, no pickup": high. Bar-level choice (line start = beat 1, not beat 3): medium-high. Nothing was checked by ear.')
out=dict(
  about='Tempo-grid analysis of dinle_2 (full mix + isolated vocal). All times in seconds. Unless stated otherwise, times are on the timeline of dinle_2_vokal.wav.',
  inputs=dict(mix='dinle_2.mp3 (decoded with ffmpeg to 44.1 kHz mono)',vocal='dinle_2_vokal.wav',words='dinle_2_words.json'),
  summary=summary,tempo=tempo,beat_phase=beat_phase,
  timeline_alignment_mix_vs_vocal_stem=dict(
     statement='The isolated vocal is not sample-locked to the decoded mp3: waveform correlation is weak (phase not preserved), and its events drift from about 4 ms later than the mix at the start to about 4 ms earlier at the end (78 ppm). Measured with two envelope/spectrogram correlations per sung line; a straight line fits within about 1.5 ms. Downbeats are converted with this line.',
     model=m2v,envelope_method_per_line=[dict(verse=r['verse'],line=r['line'],lag_ms=round(r['env_lag_ms'],2),corr=round(r['env_corr'],3)) for r in al['per_line']],
     spectro_method_per_line=[dict(verse=r['verse'],line=r['line'],lag_ms=round(r['lag_ms'],2)) for r in als['per_line']],
     waveform_correlation_median_abs=al['wave_median_abs_corr'],uncertainty_ms=2),
  downbeat=downbeat,
  onset_definitions=dict(
     onset='acoustic start of the first syllable in the isolated vocal: first spectral-flux peak (512-sample window, 0.73 ms hop, 90 Hz-8 kHz) after the energy dip that precedes the word; includes initial consonants. Agrees with a plain -20 dB envelope threshold within 6 ms (mean +3 ms) on the 19 lines preceded by silence.',
     vowel_onset='first time after `onset` at which the voiced band (90-1200 Hz, 5 ms RMS) is within 6 dB of the first-syllable peak; a proxy for the perceived attack',
     downbeat='time of the bar line the line belongs to (hypothesis H0), on the vocal-file timeline; downbeat_mix_timeline is the same instant on the decoded mp3',
     offset='offset_sec = onset - downbeat; offset_beats = offset_sec / beat period; negative = before the downbeat',
     accuracy='onset about +-5 ms for vowel-initial lines, +-10 ms for consonant-initial and legato (L4) lines; downbeat about +-3 ms relative to the drum transients plus +-2 ms timeline conversion'),
  lines=lines,
  line_rhythm_typical_word_positions_beats=l3['typical_word_positions'],
  extra_repeats_not_used=dict(note='the two extra "Dinle bak, dinle bak" after verse 7 start on lattice beats 195 and 207 (about 100.86 s and 107.07 s on the mix timeline); not analysed further'),
  not_verified='No listening was possible. Everything above is measurement. In particular the bar-level decision (H0 vs H2) and the claim that the placement "feels" the same are not verified by ear.',
  reproduce='run kod/run_all.sh (scripts 00..15); detailed intermediate results are in the other *.json files of this folder')
json.dump(out,open(O+'/tempo.json','w'),ensure_ascii=False,indent=1)
print('wrote',O+'/tempo.json')
print(json.dumps(summary,ensure_ascii=False,indent=1)[:2500])
