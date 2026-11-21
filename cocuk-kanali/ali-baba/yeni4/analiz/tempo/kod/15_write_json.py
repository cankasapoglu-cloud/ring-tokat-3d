# Assemble the deliverable tempo.json from the intermediate results.
import json, numpy as np
from common import *
J=lambda n: json.load(open(O+'/'+n))
t1=J('tempo_step1.json'); ph=J('phase_fine.json'); dr=J('drift_fine.json'); L=J('lattice.json'); dbe=J('downbeat_evidence.json')
sg=J('segments.json'); kc=J('key_chords.json'); vp=J('vocal_pitch_rough.json'); bn=J('bass_notes.json')
P=L['beat_period_s']; PHI=L['phase_first_beat_s']; BPM=L['bpm']
A_=t1['A_spectral_flux_fullband']; B_=t1['B_lowfreq_40_120Hz']; C_=t1['C_hats_8_16k_flux']
def cph(p): return ((p+P/2)%P)-P/2
segs=sg['segments']; S=sg['offset_summary']
# gaps that matter for cutting
gaps=[]
for v in range(1,8):
    q={s['name']:s for s in segs if s['verse']==v}
    gaps.append(dict(verse=v,L1_end_to_L2_onset_ms=round((q['L2']['onset']-q['L1']['end'])*1000),L2_end_to_ses_onset_ms=round((q['ses']['onset_words_file']-q['L2']['end'])*1000),
                     ses_end_to_diye_onset_ms=round((q['diye']['onset_words_file']-q['ses']['end'])*1000),diye_end_to_L4_onset_ms=round((q['L4']['onset']-q['diye']['end'])*1000),
                     L4_end_to_next_bar_line_ms=round((q['L4']['bar_downbeat']+4*P-q['L4']['end'])*1000)))
half=kc['half_bars']
def lab(h):
    c=h['chord']; r=h['root']
    return c
chords_bar=[]
QUALITY_NOTE={'D':'Dm','C':'C','G':'Gm','A':'A'}
for bar in range(6):
    hs=[h for h in half if h['bar']==bar]
    chords_bar.append(dict(bar=bar,beats_0_1=QUALITY_NOTE[hs[0]['root']],beats_2_3=QUALITY_NOTE[hs[1]['root']],
        measured_best_template=[hs[0]['chord'],hs[1]['chord']],root_votes_of_7_verses=[hs[0]['per_verse_votes'],hs[1]['per_verse_votes']],
        vocal_present=bar<4))
chords_text=' | '.join(f"bar {c['bar']}: {c['beats_0_1']} (beats 0-1) {c['beats_2_3']} (beats 2-3)" for c in chords_bar)
kf=vp['key_fit_for_new_backing']['ranking']; kfd={r['key']:r for r in kf}
out={
 'about':'Tempo grid, bar lines, segment positions, key/chords and rough sung pitches of v2_2 (first AI take, FULL MIX only: no separated vocal exists yet). All times in seconds on the timeline of v2_2.mp3 decoded by ffmpeg (44.1 kHz mono; ffmpeg removes the mp3 encoder delay).',
 'inputs':dict(mix='v2_2.mp3 (48 kHz stereo mp3, 105.0 s; decoded with ffmpeg to 44.1 kHz mono)',words='v2_2_words.json (105 words, 20 ms grid)'),
 'summary':dict(
    bpm=round(BPM,3),recommended_bpm_for_new_backing=105.0,beat_sec=round(P,6),bar_sec=round(4*P,6),beat_sec_at_105_0=round(60/105,6),bar_sec_at_105_0=round(240/105,6),
    bpm_note='machine grid at 105.00 BPM (refined lattice 105.003 +- 0.001 on the decoded mp3; an exact 105.000 grid drifts only 2.7 ms over 100 s). The value 104.96 guessed from the word timestamps was a rounding effect of their 20 ms grid.',
    tempo_stable=True,meter='4/4; kick on every beat (four on the floor), hats/chord strum on the off-beat eighths; verse = 24 beats = 6 bars',
    beat_phase_first_beat_s=round(PHI,4),beat_formula='beat n at phase_first_beat_s + n*beat_sec ; verse v (1..7) downbeat = beat 15 + 24*(v-1)',
    verse_downbeats=[round(v['first_downbeat'],4) for v in sg['verses']],verse_spacing_beats=dbe['verse_onset_beat_diffs'],
    segments_start_on_beat=True,
    typical_offset_ms={k:round(S[k]['adopted_onset']['median_ms'],1) for k in ('L1','L2','ses','diye','L4')},
    offset_spread_sd_ms={k:round(S[k]['adopted_onset']['sd_ms'],1) for k in ('L1','L2','ses','diye','L4')},
    statement_segments='All 35 segments start on their expected beat: L1, L2, ses and L4 on the downbeat of bars 0,1,2,3 of the verse, "diye bagirir" on beat 2 of bar 2 (offset 2.0 beats). No pickups. L1 ("Ali", vowel) sits within about +-20 ms of the bar line (median -2 ms). L2 and L4 begin with the fricative "c" of "ciftliginde", whose noise starts 25-45 ms (L2) and 37-62 ms (L4) BEFORE the bar line, so that the vowel lands on the beat. "diye" starts on beat 2 of its bar, 0 to +31 ms late (median +9 ms). The sung animal sounds start -37..+16 ms around the bar line (words file only).',
    original_key='D minor',original_key_confidence='high for the chord roots and the loop (identical in all 42 bars), medium-high for the chord qualities (Gm and C clear; minor third of Dm and major third of A weak but consistent)',
    original_chord_loop='Dm - C - Gm - A, two beats each, i.e. a 2-bar loop | Dm C | Gm A | that runs three times per verse and restarts on Dm exactly at every verse downbeat',
    chords_per_bar=chords_text,
    tuning_cents_re_A440=round(kc['tuning']['adopted_cents_re_A440'],1),tuning_note='about +2..+6 cents, i.e. standard A=440 within measurement error (bass-register peaks +3.7/+5.5, mid register +1.7, librosa +4)',
    sung_pitch_classes='D E F G A (D4..A4); F natural is sung in every verse ("bagirir" G-F-E, the animal word E/F, last line F-E-D). The vocal is NOT the traditional Old MacDonald tune and was composed over D minor harmony.',
    key_for_new_backing='C major',
    key_for_new_backing_reason='The task offered G major or C major. All five sung pitch classes D E F G A are inside C major; in G major the sung F natural (about 15 %% of the sung time, present in 7/7 verses) is outside the scale and collides with the F sharp of the V7 chord. Fit score under the planned harmony I I IV I: C major %.2f, F major %.2f, G major %.2f (D minor original loop key for reference %.2f).'%(kfd['C major']['score'],kfd['F major']['score'],kfd['G major']['score'],kfd['D minor (original loop key, for reference: i i iv i)']['score']),
    key_for_new_backing_confidence='medium-high that C major fits better than G major; MEDIUM that the result is pleasant at all, because the vocal was written over Dm-C-Gm-A: in C major the lines L2 and L4 end on D (= re, not the tonic) and the sung F is a suspended fourth against the E of the C chord. Not checked by ear.',
    confidence='tempo, beat phase and constancy: high. Bar lines at the verse onsets: high (band entry, 24-beat verse period, 2-bar chord loop restarting on the tonic chord there); beat 1 rather than beat 3: medium-high (no drum accent to prove it; harmonic rhythm supports it). Segment offsets: +-10 ms where refined on the mix, +-25 ms where only the words file was available (see refined_reliable). Nothing was checked by ear.'),
 'tempo':dict(search_range_bpm=t1['search_range_bpm'],
    method_A_fullband_spectral_flux=dict(description='onset envelope = half-wave rectified log-magnitude spectral flux 30 Hz-16 kHz (hop 5.8 ms); (BPM, phase) maximising the mean envelope on the beat grid; autocorrelation as cross-check',
        global_grid_search=A_['global'],autocorrelation_bpm_at_1_4_8_24_beats=A_['acf_global'],windows_20s=A_['windows_20s'],fine_search_step_0p001=dr['fine_global_grid_search_step_0.001bpm']['A_fullband_flux']),
    method_B_kick_lowfreq_40_120Hz=dict(description='kick band 40-120 Hz amplitude envelope, log-rise half-wave rectified; same grid search and autocorrelation',
        global_grid_search=B_['global'],autocorrelation_bpm_at_1_4_8_24_beats=B_['acf_global'],windows_20s=B_['windows_20s'],fine_search_step_0p001=dr['fine_global_grid_search_step_0.001bpm']['B_kick_lf']),
    method_C_hats_8_16kHz_flux=dict(description='spectral flux 8-16 kHz (hats/shaker); locks to the off-beat eighth',global_grid_search=C_['global'],autocorrelation_bpm_at_1_4_8_24_beats=C_['acf_global'],windows_20s=C_['windows_20s'],
        fine_search_step_0p001=dr['fine_global_grid_search_step_0.001bpm']['C_hats_8_16k_flux']),
    third_opinion_librosa_beat_track=dict(tempo_bpm=ph['librosa_beat_track']['tempo_bpm'],median_inter_beat_s=ph['librosa_beat_track']['median_ibi_s'],n_beats=ph['librosa_beat_track']['n_beats'],
        body_linear_fit_bpm=ph['librosa_beat_track']['body_linear_fit_bpm'],beat_phase_circular_mean_s=ph['librosa_beat_track']['body_circ_mean_phase_s'],phase_concentration_R=ph['librosa_beat_track']['phase_concentration_R'],
        note='librosa quantises to its 5.8 ms hop and locks to the OFF-beat eighth (phase 0.297 s = half a beat + 11 ms); its linear-fit tempo over the body is 105.00'),
    per_window_summary=dict(window_s=20,hop_s=10,bpm_min_A=min(w['bpm'] for w in A_['windows_20s']),bpm_max_A=max(w['bpm'] for w in A_['windows_20s']),
        bpm_min_B=min(w['bpm'] for w in B_['windows_20s']),bpm_max_B=max(w['bpm'] for w in B_['windows_20s']),
        max_abs_phase_dev_from_global_grid_ms_A=max(abs(cph(w['dev_from_global_grid_ms']/1000))*1000 for w in A_['windows_20s']),
        max_abs_phase_dev_from_global_grid_ms_B=max(abs(w['dev_from_global_grid_ms']) for w in B_['windows_20s']),
        note='window search step 0.02 BPM; a 20 s window resolves about +-0.03 BPM. Two A windows lock to the off-beat eighth (deviation about half a beat); folded to the eighth-note lattice they agree within 2 ms.'),
    fine_drift_check=dict(description='10 s windows every 5 s: position (ms) of the steepest rise of full-rate band envelopes folded over an exact 105.000 BPM beat; a straight line = constant tempo, slope = tempo correction',
        window_centres_s=dr['window_centres_s'],bands={k:v for k,v in dr.items() if isinstance(v,dict) and 'dev_ms' in v}),
    refined_lattice=L,
    vocal_only_from_words_file=sg['vocal_only_tempo'],
    result=dict(bpm=BPM,beat_period_s=P,bar_period_s=4*P,tempo_stable=True,
        statement='Tempo is constant (machine grid): 105.00 BPM. Methods A, B, C, librosa and the words-file regression (104.99) agree; no window deviates by more than 0.06 BPM (window resolution) and the beat phase stays within +-3 ms of one straight lattice over the whole song. Use exactly 105.0 BPM for the new backing (bar = 2.285714 s).')),
 'beat_phase':dict(lattice=dict(formula='beat n at phase_first_beat_s + n*beat_period_s',phase_first_beat_s=PHI,beat_period_s=P),
    method_A_phase_s=A_['global']['phase_first_beat_s'],method_B_phase_s=B_['global']['phase_first_beat_s'],method_C_phase_s=C_['global']['phase_first_beat_s'],
    methods_compared=dict(A_minus_lattice_ms=round(cph(A_['global']['phase_first_beat_s']-PHI)*1000,1),B_minus_lattice_ms=round(cph(B_['global']['phase_first_beat_s']-PHI)*1000,1),
        C_minus_lattice_minus_half_beat_ms=round(cph(C_['global']['phase_first_beat_s']-PHI-P/2)*1000,1),
        statement='Full-band flux (A, -3 ms) and kick low-frequency rise (B, +4 ms) pick the SAME beat phase: the eighth that carries the kick. Hats (C) and librosa pick the other eighth (off-beat), 4 ms / 11 ms off the exact half beat. Beat = kick eighth.'),
    band_attack_position_inside_beat_ms={k:dict(peak_ms=round(v['peak_phase_s']*1000,1),max_rise_ms=round(cph(v['max_rise_phase_s'])*1000,1),rise_at_sixteenths_rel=v['rise_at_sixteenths_rel']) for k,v in ph.items() if k!='librosa_beat_track'},
    per_verse_local_phase_check=[dict(verse=v['verse'],**v['local_attack_minus_lattice_ms']) for v in sg['verses']],
    per_verse_note='steepest rise of the on-beat attack inside the 24 beats of each verse minus the global lattice: 120-300 Hz +2.0..+4.7 ms, 300-2000 Hz -0.2..-1.2 ms, no trend -> one global lattice is valid for every verse',
    confidence='high'),
 'downbeat':dict(bars_are='4 beats (2.2857 s)',verse_onset_beat_numbers=dbe['verse_onset_beats'],verse_onset_beat_spacing=dbe['verse_onset_beat_diffs'],
    verses=sg['verses'],
    irregularities='None inside the song body: all six verse-to-verse distances are exactly 24 beats (6 bars); every verse = 4 sung bars + 2 instrumental bars. Only the INTRO is odd: 15 beats (not 16) before verse 1, i.e. the audio starts on beat 2 of a 4-bar intro (bar lines of the intro at 1.714, 4.000, 6.286 s); the intro has no kick and no chords, only off-beat percussion.',
    evidence=dict(
        E1_band_entry='kick (40-120 Hz) and the chord instrument are absent in beats 0-14 (level about 0.05 of the body) and enter together exactly on beat 15 = first syllable of verse 1',
        E2_verse_period='beat-feature self-similarity is by far highest at lag 24 beats (%.2f; lag 4: %.2f, lag 8: %.2f); the vocal (4 bars) / instrumental (2 bars) change happens at position 16 = a multiple of 4 (overall level drops from about 1.05 to 0.8 there)'%(dbe['beat_feature_selfsim_by_lag']['24'],dbe['beat_feature_selfsim_by_lag']['4'],dbe['beat_feature_selfsim_by_lag']['8']),
        E3_harmonic_rhythm='chord loop Dm C | Gm A (2 beats per chord) starts on the tonic chord Dm at positions 0, 8, 16 of every verse and the dominant A fills the last two beats before each of them',
        E4_lyrics='the five sung units start at positions 0.0, 4.0, 8.0, 10.0 and 12.0 beats from the verse onset (medians %s)'%([q['median_start_beats'] for q in sg['typical_word_positions'] if q['index'] in (0,5,8,10,12)]),
        E5_weak='drums give no bar accent (kick on every beat, same hats); nothing separates "verse onset = beat 1" from "= beat 3" except E1-E3'),
    fold_mod4_relative_to_verse_onset=dbe['fold_mod4_relative_to_verse_onset'],
    confidence=dict(beat_lattice='high',bar_lines_at_verse_onsets_and_every_4_beats_after='high (medium-high for beat 1 vs beat 3, which does not matter for re-placing the segments)')),
 'onset_definitions':dict(
    onset='start of the first word of the segment. Where refined_reliable is true: first time after the preceding energy dip at which the band-subtracted mix envelope (300-3400 Hz for vowel/voiced starts, 2-7 kHz for "c" starts; band = 90th percentile of the same beat phase in the instrumental bars) reaches 25 % of the first-syllable peak. Otherwise the words-file start (20 ms grid).',
    end='end of the last word of the segment from the words file (not refined; reverb/breath tails are not included)',
    bar_downbeat='lattice time of the downbeat of the bar the segment belongs to: verse downbeat + 4 beats x bar_in_verse (L1 bar 0, L2 bar 1, ses bar 2, diye bar 2, L4 bar 3)',
    offset='offset_sec = onset - bar_downbeat; offset_beats = offset_sec / beat period. For "diye" the expected value is 2 beats; deviation_from_expected_beat_ms removes that.',
    accuracy='refined onsets about +-10 ms; words-file onsets about +-25 ms; bar_downbeat about +-3 ms relative to the drum transients'),
 'segments':segs,
 'segment_offset_summary':S,
 'gaps_between_segments_for_cutting_ms':dict(per_verse=gaps,note='from the words file: L2 runs straight into the sung animal sound (0-40 ms gap) and "diye" follows the second animal sound after 100-340 ms; the sung animal sounds therefore cannot be cut out on silence everywhere, cross-fades of a few tens of ms will be needed (to be checked on the separated vocal)'),
 'typical_word_positions_beats_from_verse_downbeat':sg['typical_word_positions'],
 'key':dict(
    statement='The ORIGINAL band of v2_2 is in D minor (not G major, not C major): 2-bar loop Dm - C - Gm - A (i - VII - iv - V), two beats per chord, identical in all six bars of every verse and in the instrumental bars.',
    how='No bass guitar exists: 40-120 Hz is only the kick (about 52 Hz). The chord instrument plays on the off-beat half of each beat with its lowest notes A2..G3 (95-275 Hz), below the sung range, so root/fifth are read there without vocal interference: A2+D3(+F3) = Dm, C3+G3 (+E in the mid register) = C, G/Bb2/D3/F3 = Gm (Bb is the strongest low partial), A2+E3 (+C#) = A.',
    chords_per_bar=chords_bar,chords_text=chords_text,half_bar_detail=half,positions_detail=kc['positions'],
    scale='D natural minor (D E F G A Bb C) with C# only inside the dominant A chord; relative major F major',
    krumhansl_profiles=kc['key_profiles'],
    krumhansl_note='global key-profile correlation is NOT reliable here (the note A dominates the low register as fifth of Dm and root of A; the mid register is dominated by the vocal) - it is reported only for completeness; the decision rests on the chord loop',
    tuning=kc['tuning'],
    confidence=dict(roots_and_loop='high (per-verse votes agree in 5-7 of 7 verses for every half bar, 7/7 in the vocal-free bars)',chord_quality='Gm high (Bb), C high (E), Dm medium-high (F weak but present, no F#), A medium (C# weak; in the last beat of the loop a D sounds on top = Asus4 or anticipation of Dm)',
                    key_D_minor='high',not_verified='not checked by ear'),
    low_register_notes_per_beat_from_10_bass_notes=dict(note='strongest harmonic-sum note 36-135 Hz per beat (it is the LOWEST chord note, not a bass line): A A C G/A | C C A G | ... consistent with the loop above',pc_by_position_in_verse=bn['pc_by_position_in_verse'])),
 'vocal_pitch_rough':dict(flag=vp['flag'],method='harmonic-comb salience (harmonics 1-5) on a 93 ms STFT, 10 ms hop, 130-700 Hz, per word: median, stable note runs, frame share; cross-check pyworld harvest on the 200-1500 Hz band. Octave is uncertain by construction (G3 results for "bir"/"diye" are octave errors of G4, pyworld gives G4).',
    verse_1=[w for w in vp['words'] if w['verse']==1],verse_2=[w for w in vp['words'] if w['verse']==2],
    consensus_per_word_index_over_7_verses=vp['consensus_per_word_index'],
    melody_summary='L1: D4 (Ali, rising to G4) A4 (Baba\'nin) G4 (bir) G4-F4 (ciftligi) E4 (var) | L2: D4-G4 (ciftliginde) F4/E4 alternating (animal word) D4 (var) | ses: D4, A4 | diye G4, bagirir G4-F4-E4 | L4: D4-G4 (ciftliginde) F4-E4 (Ali) F4-E4-D4 (Baba\'nin)',
    sung_pitch_class_duration_share=vp['sung_pitch_class_duration_share'],
    key_fit_for_new_backing=vp['key_fit_for_new_backing']),
 'timeline_note':'Bar lines and onsets are on the timeline of v2_2.mp3 as decoded by ffmpeg. A separated vocal file can be shifted by a few ms and can run some tens of ppm faster/slower (the previous take: -4 ms, 78 ppm): re-measure the lag before cutting (method: yeni3/analiz/tempo/kod/09_align_fine.py and 12_align_spectro.py).',
 'not_verified':'No listening was possible. Everything above is measurement on the full mix. Unverified by ear: that the bar lines feel right, that the refined onsets are the perceived starts, the octave and exact notes of the sung melody, and above all that the D-minor vocal sounds acceptable over a C major (or any major) backing with the traditional tune.',
 'reproduce':'run kod/run_all.sh; intermediate results: tempo_step1.json, phase_fine.json, drift_fine.json, lattice.json, downbeat_evidence.json, bass_notes.json, key_chords.json, segments.json, vocal_pitch_rough.json'}
json.dump(out,open(O+'/tempo.json','w'),ensure_ascii=False,indent=1)
print('wrote',O+'/tempo.json'); print(json.dumps(out['summary'],ensure_ascii=False,indent=1)); print(json.dumps(gaps))
