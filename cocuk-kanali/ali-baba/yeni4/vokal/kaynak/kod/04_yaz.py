# Write the chosen vocal stem as v2_2_vokal.wav (mono 44.1 kHz, 24-bit PCM) on the timeline of the ffmpeg-decoded mix,
# verify it, and assemble rapor.json.
#   usage: python3 04_yaz.py <name>        (name = mdx | rof; the decision text is read from kod/karar.json)
# Processing: mono = (L+R)/2 of the separator's stereo vocal file, an integer-sample shift if (and only if) the measured
# lag is at least half a sample, nothing else (no gain, no normalisation, no filtering, no dither).
import sys, json, os, time, subprocess, numpy as np, soundfile as sf
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from common import *

name = sys.argv[1]
KOD = __file__.rsplit('/', 1)[0]
P = stem_paths()
hz = json.load(open(f'{CACHE}/hizala_{name}.json'))
cmp_ = json.load(open(CACHE + '/karsilastir.json'))
karar = json.load(open(KOD + '/karar.json'))
assert karar['chosen'] == name, (karar['chosen'], name)

# ---- measured lag: the waveform methods agree; the sum check (when present) is the most precise
lag_wave = hz['per_segment_summary']['wave_lag_ms']['median_ms']
ppm_wave = hz['per_segment_summary']['wave_lag_ms']['clock_ppm']
lag_sum = hz['sum_check']['median_lag_ms'] if 'sum_check' in hz else None
ppm_sum = hz['sum_check']['clock_ppm'] if 'sum_check' in hz else None
lag_ms = lag_sum if lag_sum is not None else lag_wave
lag_samples = lag_ms * SR / 1000
shift = int(round(lag_samples))                 # stem late by `shift` samples -> advance it
vs = load_stem(P[name]['vocals'], mono=False)
mono = vs.mean(1) if vs.ndim > 1 else vs
n_mix = len(load_mix())
y = mono.copy()
if shift > 0:
    y = np.r_[y[shift:], np.zeros(shift)]
elif shift < 0:
    y = np.r_[np.zeros(-shift), y[:shift]]
if len(y) < n_mix: y = np.r_[y, np.zeros(n_mix - len(y))]
y = y[:n_mix]
assert np.abs(y).max() < 1.0
outp = O + '/v2_2_vokal.wav'
sf.write(outp, y, SR, subtype='PCM_24')

# ---- verification of the written file
z, sr = sf.read(outp, dtype='float64'); info = sf.info(outp)
ver = dict(file=outp, samplerate=sr, channels=info.channels, subtype=info.subtype, frames=int(info.frames), duration_s=info.frames / sr,
           max_abs_difference_to_source_mono=float(np.abs(z - y).max()),
           exact_in_24_bit=bool(np.abs(z - y).max() == 0.0),
           peak=float(np.abs(z).max()), peak_dbfs=float(20 * np.log10(np.abs(z).max())), rms_dbfs=rms_db(z),
           identical_to_A_v2_2_vokal_mdx_wav_within_half_16bit_lsb=None)
old = A + '/v2_2_vokal_mdx.wav'
if name == 'mdx' and os.path.exists(old):
    o, _ = sf.read(old, dtype='float64')
    ver['identical_to_A_v2_2_vokal_mdx_wav_within_half_16bit_lsb'] = bool(len(o) == len(z) and np.abs(o - z).max() <= 0.5 / 32768 + 1e-12)
    ver['max_abs_difference_to_A_v2_2_vokal_mdx_wav_in_16bit_lsb'] = float(np.abs(o[:len(z)] - z[:len(o)]).max() * 32768)
# re-measure the lag of the written file with the same script
r = subprocess.run([sys.executable, KOD + '/03_hizala.py', 'cikti', outp], capture_output=True, text=True, check=True)
print(r.stdout)
hz2 = json.load(open(f'{CACHE}/hizala_cikti.json'))
ver['lag_of_written_file_ms'] = dict(waveform_median=hz2['per_segment_summary']['wave_lag_ms']['median_ms'],
                                     waveform_min=hz2['per_segment_summary']['wave_lag_ms']['min_ms'],
                                     waveform_max=hz2['per_segment_summary']['wave_lag_ms']['max_ms'],
                                     waveform_clock_ppm=hz2['per_segment_summary']['wave_lag_ms']['clock_ppm'],
                                     envelope_median=hz2['per_segment_summary']['env_lag_ms']['median_ms'],
                                     envelope_clock_ppm=hz2['per_segment_summary']['env_lag_ms']['clock_ppm'],
                                     dspec_median=hz2['per_segment_summary']['dspec_lag_ms']['median_ms'],
                                     wave_corr_median=hz2['per_segment_summary']['wave_corr_median'])
# strict sample check of the written file: compensate * vocal + instrumental (mono) against the mono mix at integer lags
if P[name]['instrumental'] and 'sum_check' in hz:
    ins_m = load_stem(P[name]['instrumental'])[:n_mix]; xm = load_mix()
    comp = hz['sum_check']['compensate_c']; gm = hz['sum_check']['gain_mix_g']
    sm_ = comp * z + ins_m; a_, b_ = 20 * SR, 80 * SR; res_l = {}
    for L in range(-8, 9):
        res_l[L] = rms_db(sm_[a_ + L:b_ + L] - gm * xm[a_:b_]) - rms_db(gm * xm[a_:b_])
    best = min(res_l, key=res_l.get)
    ver['sum_check_of_written_file'] = dict(method='compensate*written vocal + mono instrumental stem against g*mono mix, 20-80 s, integer lags -8..+8',
                                            best_lag_samples=int(best), residual_db_at_best_lag=float(res_l[best]),
                                            residual_db_at_plus_minus_1_sample=[float(res_l[-1]), float(res_l[1])])
# levels of the written file (its own scale, i.e. NOT divided by the separator gain)
R = regions(); N = len(z)
m_sw = mask_from(R['sung_words'], N); m_in = mask_from(R['inst'], N); m_pre = mask_from(R['pre'], N); m_tl = mask_from(R['tails'], N)
lev = dict(sung_words_rms_dbfs=rms_db(z[m_sw]), inst_rms_dbfs=rms_db(z[m_in]), inst_rel_sung_db=rms_db(z[m_in]) - rms_db(z[m_sw]),
           breath_zone_rms_dbfs=rms_db(z[m_pre]), tails_rms_dbfs=rms_db(z[m_tl]),
           inst_per_stretch_dbfs=[rms_db(z[int(a * SR):int(b * SR)]) for a, b in R['inst']],
           inst_per_stretch_rel_sung_db=[rms_db(z[int(a * SR):int(b * SR)]) - rms_db(z[m_sw]) for a, b in R['inst']])

hzall = {}
for nm in P:
    h = json.load(open(f'{CACHE}/hizala_{nm}.json'))
    hzall[nm] = dict(sum_check={k: v for k, v in h.get('sum_check', {}).items() if k != 'windows'} or None,
                     sum_check_windows=h.get('sum_check', {}).get('windows'),
                     per_segment_summary=h['per_segment_summary'], per_segment=h['per_segment'])
bek = json.load(open(CACHE + '/bekle_rof.json')) if os.path.exists(CACHE + '/bekle_rof.json') else None
rap = dict(
    about='Choice and preparation of the vocal source of v2_2 (first AI take). Output: v2_2_vokal.wav, mono 44.1 kHz 24-bit, '
          'sample-aligned with v2_2.mp3 as decoded by ffmpeg (44.1 kHz). All times in this report are on that timeline.',
    written_utc=time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime()),
    chosen=dict(name=name, model=karar['models'][name], source_file=P[name]['vocals'], compared_candidates=list(P.keys()),
                summary=karar['summary'], reasons=karar['reasons']),
    candidates={nm: dict(model=karar['models'].get(nm), vocals=P[nm]['vocals'], instrumental=P[nm]['instrumental']) for nm in P},
    roformer_wait=bek,
    candidate_not_available=karar.get('candidate_not_available'),
    measurement_notes=karar.get('measurement_notes'),
    known_weak_points_of_the_chosen_stem=karar.get('known_weak_points_of_the_chosen_stem'),
    timeline=dict(convention='lag > 0: stem late against the mix', measured_lag_ms=lag_ms, measured_lag_samples=lag_samples,
                  measured_clock_difference_ppm=ppm_sum if ppm_sum is not None else ppm_wave,
                  waveform_method_lag_ms=lag_wave, waveform_method_clock_ppm=ppm_wave, sum_check_lag_ms=lag_sum, sum_check_clock_ppm=ppm_sum,
                  correction_applied_samples=shift,
                  correction_note=('no shift was needed: the stem is already sample-aligned with the mix' if shift == 0 else
                                   f'stem advanced by {shift} samples' if shift > 0 else f'stem delayed by {-shift} samples'),
                  why_zero=karar.get('why_zero_lag'),
                  methods='S: vocals+instrumental against the stereo mix, generalised cross-correlation, 32x interpolation, 5 s windows; '
                          'W: 250-3000 Hz waveform cross-correlation mix<->vocal stem per sung segment (35 segments), 32x interpolation; '
                          'E: 1-4 kHz envelope cross-correlation per segment; D: stem-weighted log-magnitude derivative correlation per segment '
                          '(D carries a known positive bias of about half a millisecond from the stem-energy weighting and is only a cross-check)',
                  per_candidate=hzall),
    output=dict(verification=ver, levels_own_scale=lev,
                processing='mono = (L+R)/2 of the separator output (16-bit stereo) written as 24-bit PCM, so every value is exact; '
                           'no gain, no normalisation, no filtering, no dither, no time or pitch processing',
                scale_note=karar.get('scale_note')),
    comparison=cmp_,
    bleed_inside_the_sung_frames=(json.load(open(CACHE + '/sarki_ici_sizinti.json')) if os.path.exists(CACHE + '/sarki_ici_sizinti.json') else None),
    not_verified=karar['not_verified'],
    reproduce='kod/calistir.sh  (the mix is decoded on demand by common.py; 01 wait for the Roformer file; 03 lag per candidate; '
              '02 comparison; 05 bleed inside the sung frames; karar.json = the decision written after reading the numbers; '
              '04 write + verify + rapor.json)')
json.dump(rap, open(O + '/rapor.json', 'w'), indent=1, ensure_ascii=False)
print('written', outp, 'and', O + '/rapor.json')
print(json.dumps(ver, indent=1))
print(json.dumps(lev, indent=1))
