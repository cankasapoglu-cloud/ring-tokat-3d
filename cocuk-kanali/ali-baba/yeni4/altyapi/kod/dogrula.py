#!/usr/bin/env python3
# Verification of the yeni4 backing for the v2_2 form (measurements only; nobody listened to anything).
# Adapted from yeni3/altyapi/kod/dogrula.py.
# usage: dogrula.py <output folder> <scratch folder used by build.py> [variant ...]
# Writes <output folder>/dogrulama.json (or the file named in $DOGRULAMA_JSON) and prints a report. Exit code 1 if any hard check fails.
import json, os, re, subprocess, sys
import numpy as np, soundfile as sf, mido, pyloudnorm
from scipy.signal import resample_poly, butter, sosfiltfilt

O, W = sys.argv[1:3]
VARS = sys.argv[3:] or ['G', 'C']
db = lambda v: 20 * np.log10(np.maximum(v, 1e-12))
rms = lambda x: float(np.sqrt((np.asarray(x) ** 2).mean()))
FAIL = []
def check(ok, msg):
    print(('  OK   ' if ok else '  FAIL ') + msg)
    if not ok: FAIL.append(msg)
    return bool(ok)

def yin(x, sr, fmin=120.0, fmax=2500.0, thr=0.15):
    """YIN f0 estimate of a monophonic window (no prior knowledge of the expected pitch), refined on the FFT peak."""
    x = x - x.mean(); tmax = int(sr / fmin) + 2; tmin = max(2, int(sr / fmax)); Wn = len(x) - tmax
    if Wn < 2 * tmax or rms(x) < 1e-7: return np.nan
    a = x[:Wn]; d = np.empty(tmax + 1); d[0] = 0
    c = np.cumsum(np.concatenate([[0], x ** 2]))
    acf = np.correlate(x, a, 'valid')[:tmax + 1]                  # sum a[j]*x[j+tau]
    for tau in range(1, tmax + 1): d[tau] = c[Wn] - c[0] + c[tau + Wn] - c[tau] - 2 * acf[tau]
    cm = np.ones(tmax + 1); cs = np.cumsum(d[1:]); cm[1:] = d[1:] * np.arange(1, tmax + 1) / np.maximum(cs, 1e-20)
    tau = None
    for t in range(tmin, tmax):
        if cm[t] < thr and cm[t] <= cm[t - 1] and cm[t] <= cm[t + 1]: tau = t; break
    if tau is None: tau = tmin + int(np.argmin(cm[tmin:tmax]))
    f = sr / tau
    # refine: spectral peak within +-1 semitone of the YIN estimate
    Nf = 1 << 17; X = np.abs(np.fft.rfft(x * np.hanning(len(x)), Nf)); F = np.fft.rfftfreq(Nf, 1 / sr)
    lo, hi = np.searchsorted(F, [f * 2 ** (-1 / 12), f * 2 ** (1 / 12)])
    if hi - lo < 3: return f
    k = lo + int(np.argmax(X[lo:hi]))
    if 0 < k < len(X) - 1:
        a0, b0, c0 = np.log(X[k - 1] + 1e-20), np.log(X[k] + 1e-20), np.log(X[k + 1] + 1e-20)
        k = k + 0.5 * (a0 - c0) / (a0 - 2 * b0 + c0 + 1e-20)
    return k * sr / Nf
def stmag(x, sr, t_start, f, win=0.030):
    """Magnitude of the component at frequency f in a short Hann window starting at t_start."""
    i0 = int(t_start * sr); n = int(win * sr)
    if i0 < 0 or i0 + n > len(x): return 0.0
    t = np.arange(n) / sr
    return float(np.abs(np.sum(x[i0:i0 + n] * np.hanning(n) * np.exp(-2j * np.pi * f * t))))
def bandpeak(x, sr, lo, hi):
    """Strongest spectral peak in a fixed band (no knowledge of the expected note)."""
    Nf = 1 << 17; X = np.abs(np.fft.rfft((x - x.mean()) * np.hanning(len(x)), Nf)); F = np.fft.rfftfreq(Nf, 1 / sr)
    a, b = np.searchsorted(F, [lo, hi]); k = a + int(np.argmax(X[a:b]))
    a_, b_, c_ = np.log(X[k - 1] + 1e-20), np.log(X[k] + 1e-20), np.log(X[k + 1] + 1e-20)
    return (k + 0.5 * (a_ - c_) / (a_ - 2 * b_ + c_ + 1e-20)) * sr / Nf
def glockpitch(x, sr, t0, dur, expected, lo=450.0, hi=2200.0):
    """Glockenspiel (FluidR3): the partials are not harmonic, the upper ones are stronger than the fundamental during the
    attack, and earlier notes keep ringing through later ones, so a plain pitch detector does not work on this stem.
    Peaks are listed in the range where every glockenspiel fundamental of this song lies (C5..C7).
    Returns (f_present, f_blind):
      f_present = the peak nearest to the expected fundamental (nan if none within a semitone)   -> used for pass/fail
      f_blind   = the lowest peak that newly appears at the onset (level 45-75 ms after the onset at least 1.5 x the level
                  just before it); if none is new (a repeated note meets its own ringing predecessor), the peak that is
                  strongest after the onset                                                      -> reported for information"""
    i0 = int((t0 + 0.012) * sr); i1 = int((t0 + max(0.16, min(dur, 0.45) - 0.01)) * sr); seg = x[i0:i1]
    Nf = 1 << 17; X = np.abs(np.fft.rfft((seg - seg.mean()) * np.hanning(len(seg)), Nf)); F = np.fft.rfftfreq(Nf, 1 / sr)
    a, b = np.searchsorted(F, [lo, hi]); thr = 0.03 * X[a:b].max(); cands = []
    for k in range(a + 1, b - 1):
        if X[k] > thr and X[k] >= X[k - 1] and X[k] > X[k + 1]:
            a_, b_, c_ = np.log(X[k - 1] + 1e-20), np.log(X[k] + 1e-20), np.log(X[k + 1] + 1e-20)
            f = (k + 0.5 * (a_ - c_) / (a_ - 2 * b_ + c_ + 1e-20)) * sr / Nf
            if cands and f / cands[-1][0] < 1.03:
                if X[k] > cands[-1][1]: cands[-1] = (f, X[k])
            else: cands.append((f, X[k]))
    if not cands: return np.nan, np.nan
    fe = 440 * 2 ** ((expected - 69) / 12); near = min(cands, key=lambda c: abs(np.log2(c[0] / fe)))
    f_present = near[0] if abs(12 * np.log2(near[0] / fe)) < 1 else np.nan
    late = [(f, stmag(x, sr, t0 + 0.045, f), stmag(x, sr, t0 - 0.034, f)) for f, m in cands]
    new = [f for f, ma, mb in late if ma > 1.5 * mb]
    f_blind = new[0] if new else max(late, key=lambda c: c[1])[0]
    return f_present, f_blind
f2m = lambda f: 69 + 12 * np.log2(f / 440.0)
def envelope(x, sr, win=0.003, hop=0.0005):
    h = int(hop * sr); w = int(win * sr); c = np.cumsum(np.concatenate([[0], x ** 2]))
    idx = np.arange(0, len(x) - w, h); return np.sqrt((c[idx + w] - c[idx]) / w), h / sr, w / sr
def onset(e, hop, win, t0, dur):
    """Time at which the envelope first reaches half of the note's peak, after the dip that precedes the note."""
    i = lambda t: int(max(0, (t - win / 2) / hop))
    pk = e[i(t0):i(t0 + min(dur, 0.25)) + 1].max()
    a, b = i(t0 - 0.04), i(t0 + 0.03); m = a + int(np.argmin(e[a:b + 1]))
    seg = e[m:i(t0 + 0.2)]; j = np.argmax(seg >= 0.5 * pk)
    return (m + j) * hop + win / 2
def lufs_ffmpeg(p):
    e = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', p, '-af', 'ebur128=peak=true', '-f', 'null', '-'], capture_output=True, text=True).stderr
    tail = e[e.rindex('Summary:'):]
    return float(re.search(r'I:\s+(-?[\d.]+) LUFS', tail).group(1)), float(re.search(r'LRA:\s+(-?[\d.]+) LU', tail).group(1)), \
        float(re.search(r'Peak:\s+(-?[\d.]+) dBFS', tail).group(1))

REPORT = {}
EV = {}
for V in VARS:
    print(f'\n================ variant {V} ================')
    Z = json.load(open(f'{O}/zaman_{V}.json')); Mt = json.load(open(f'{W}/{V}/meta.json'))
    sr = Mt['sr']; BEAT = Mt['BEAT']; BAR = Mt['BAR']; N = Mt['N']; CUT = Mt['CUT']; bars = Mt['bars']; TOTAL = Mt['TOTAL']
    INTRO, VB, NV = Mt['INTRO'], Mt['VB'], Mt['NV']
    EV[V] = Mt['events']; rep = REPORT[V] = {'key': Mt['key'], 'bpm': Mt['bpm']}
    SB = list(Mt['SLOT_BARS']); FB = Mt['FILL_BAR']; AK = Mt['ALT_KINDS']; TONV = globals().setdefault('TONV', {}); TONV[V] = Mt['TON']
    files = {k: f'{O}/{k}_{V}.wav' for k in ('altyapi', 'ezgi_alti', 'rehber')}
    X = {}
    print('[1] files, format, duration')
    for k, p in files.items():
        inf = sf.info(p); x, _ = sf.read(p, dtype='float64'); X[k] = x
        check(inf.samplerate == 44100 and inf.channels == 2 and inf.subtype == 'PCM_16' and inf.format == 'WAV',
              f'{os.path.basename(p)}: {inf.channels} ch, {inf.samplerate} Hz, {inf.subtype}, {inf.frames} frames = {inf.frames / sr:.4f} s')
    check(len({len(x) for x in X.values()}) == 1, 'the three files have the same length')
    dur = len(X['altyapi']) / sr
    check(abs(dur - Z['dosya_suresi_sn']) < 0.001, f'duration {dur:.4f} s = zaman json {Z["dosya_suresi_sn"]} s')
    check(Z['toplam_olcu'] == 64 and abs(Z['olcu_sn'] - 240 / Mt['bpm']) < 1e-5, f'{Z["toplam_olcu"]} bars, bar {Z["olcu_sn"]} s, beat {Z["vurus_sn"]} s, BPM {Z["tempo_bpm"]}')
    check(len(Z['kitalar']) == 7 and all(len(v['olcu_baslangiclari']) == 8 and len(v['akorlar']) == 8 for v in Z['kitalar']), '7 verses x 8 bars in zaman json')
    tail = dur - Z['son_vurus_sn']
    v = Z['kitalar']; e0 = INTRO + NV * VB
    okt = all(abs(v[k]['olcu_baslangiclari'][i] - (INTRO + k * VB + i) * BAR) < 6e-5 for k in range(NV) for i in range(VB)) and \
        all(abs(v[k]['hayvan_sesi']['ses1_baslangic'] - (INTRO + k * VB + SB[0]) * BAR) < 6e-5 and abs(v[k]['hayvan_sesi']['ses2_baslangic'] - (INTRO + k * VB + SB[1]) * BAR) < 6e-5
            and abs(v[k]['diye_bagirir']['baslangic'] - ((INTRO + k * VB + FB) * BAR + 2 * BEAT)) < 6e-5 for k in range(NV)) and \
        all(abs(b['baslangic'] - b['olcu'] * BAR) < 6e-5 for b in Z['giris']['olculer'] + Z['bitis']['olculer']) and [b['olcu'] for b in Z['bitis']['olculer']] == list(range(e0, e0 + Mt['END']))
    check(okt, f'zaman json: verse v starts at bar 4 + 8 v; animal calls on the downbeats of verse bars {SB[0]} and {SB[1]} (verse 1: {v[0]["hayvan_sesi"]["ses1_baslangic"]} s, {v[0]["hayvan_sesi"]["ses2_baslangic"]} s); '
          f'"diye bagirir" on beat 2 of verse bar {FB} (verse 1: {v[0]["diye_bagirir"]["baslangic"]} s); intro and ending bar times on the grid')
    DEGS = [b['dereceler'] for b in v[0]['olculer']]
    check(DEGS == [['I', 'I', 'IV', 'I'], ['I', 'V7', 'I', 'I'], ['I', 'I', 'IV', 'I'], ['I'] * 4, ['I'] * 4, ['I'] * 4, ['I', 'I', 'IV', 'I'], ['I', 'V7', 'I', 'I']]
          and all([b['dereceler'] for b in v[k]['olculer']] == DEGS for k in range(NV)), f'harmony per beat of the 8 verse bars as specified: {[" ".join(d) for d in DEGS]} = {[" ".join(a) for a in v[0]["akorlar"]]}')
    check(2.3 <= tail <= 2.8, f'ring-out tail after the final hit: {tail:.3f} s (final hit at {Z["son_vurus_sn"]} s, music end {Z["muzik_bitis_sn"]} s)')
    endlvl = db(np.abs(X['altyapi'][-int(0.02 * sr):]).max())
    check(endlvl < -60, f'file ends in silence (last 20 ms peak {endlvl:.1f} dBFS)')
    rep.update(duration_s=round(dur, 4), bars=Z['toplam_olcu'], bar_s=Z['olcu_sn'], beat_s=Z['vurus_sn'], tail_after_final_hit_s=round(tail, 3))

    print('[2] rehber = altyapi + ezgi_alti')
    dmax = np.abs(X['rehber'] - X['altyapi'] - X['ezgi_alti']).max() * 32768
    check(dmax <= 1.5, f'max |rehber - (altyapi + ezgi_alti)| = {dmax:.2f} LSB (16 bit)')
    rep['rehber_minus_sum_max_lsb'] = round(float(dmax), 2)

    print('[3] loudness, peaks')
    meter = pyloudnorm.Meter(sr)
    for k in ('altyapi', 'rehber', 'ezgi_alti'):
        x = X[k]; I, LRA, TPf = lufs_ffmpeg(files[k]); Ip = meter.integrated_loudness(x)
        sp = db(np.abs(x).max()); tp = db(np.abs(resample_poly(x, 4, 1, axis=0)).max()); clip = int((np.abs(x) >= 0.999).sum())
        rep[k] = {'lufs_ffmpeg': I, 'lufs_pyloudnorm': round(float(Ip), 2), 'lra': LRA, 'sample_peak_dbfs': round(float(sp), 2),
                  'true_peak_dbtp_4x': round(float(tp), 2), 'true_peak_ffmpeg': TPf, 'clipped_samples': clip}
        msg = f'{k}: {I:.1f} LUFS (ffmpeg ebur128; pyloudnorm {Ip:.2f}), LRA {LRA}, sample peak {sp:.2f} dBFS, true peak {tp:.2f} dBTP (4x) / {TPf} (ffmpeg), samples >= 0.999: {clip}'
        if k == 'altyapi': check(abs(I + 14) <= 0.5 and tp < -1.0 and clip == 0, msg)
        elif k == 'rehber': check(tp < -1.0 and clip == 0, msg)
        else: print('       ' + msg)
    print(f'       limiter: max gain reduction {Mt["max_gr_db"]:.2f} dB, >0.5 dB during {100 * Mt["gr_frac_gt_0p5db"]:.2f} % of the time, >2 dB during {100 * Mt["gr_frac_gt_2db"]:.2f} %; '
          f'largest at {[(round(t, 2), round(g, 1)) for t, g in Mt["gr_worst"]]} (s, dB)')
    rep['limiter'] = {'max_gain_reduction_db': round(Mt['max_gr_db'], 2), 'time_over_0p5db_pct': round(100 * Mt['gr_frac_gt_0p5db'], 2),
                      'time_over_2db_pct': round(100 * Mt['gr_frac_gt_2db'], 2), 'master_gain_db': round(float(db(Mt['gain'])), 2), 'ceiling_dbfs': Mt['ceil_db']}

    print('[4] beat grid measured in the audio')
    a = X['altyapi'].mean(1)
    hp = sosfiltfilt(butter(4, [6000, 14000], 'bandpass', fs=sr, output='sos'), a)      # hi-hat / snare / tambourine band
    e, hop, win = envelope(hp, sr, win=0.002, hop=0.00025)
    tt = []; bb = []
    for bi, (ch, kind, k, vb) in enumerate(bars):
        for bt in range(4):
            if kind == 'final' and bt in (1, 2): continue            # no beat hits there (snare roll only)
            t0 = (bi * 4 + bt) * BEAT; i0 = max(0, int((t0 - 0.02) / hop)); i1 = int((t0 + 0.03) / hop)
            seg = e[i0:i1]; pk = seg.max(); m = int(np.argmin(seg[:max(1, int(0.02 / hop))])); j = m + int(np.argmax(seg[m:] >= 0.5 * pk))
            tt.append((i0 + j) * hop + win / 2); bb.append(bi * 4 + bt)
    tt = np.array(tt); bb = np.array(bb); sl, ic = np.polyfit(bb, tt, 1); res = tt - (sl * bb + ic); dev = tt - bb * BEAT
    check(abs(sl - BEAT) < 2e-5 and abs(np.median(dev)) < 0.008 and res.std() < 0.004,
          f'{len(tt)} beat onsets (6-14 kHz band: hi-hat/snare/tambourine): fitted beat {sl:.6f} s (nominal {BEAT:.6f}; => bar {4 * sl:.5f} s, {60 / sl:.3f} BPM), '
          f'half-level onset minus grid: median {1000 * np.median(dev):+.2f} ms, min {1000 * dev.min():+.2f}, max {1000 * dev.max():+.2f}, residual sd {1000 * res.std():.2f} ms')
    rep['grid'] = {'beat_onsets': len(tt), 'fitted_beat_s': round(float(sl), 6), 'fitted_bar_s': round(float(4 * sl), 5), 'fitted_bpm': round(float(60 / sl), 3),
                   'onset_minus_grid_ms_median': round(float(1000 * np.median(dev)), 2), 'min': round(float(1000 * dev.min()), 2), 'max': round(float(1000 * dev.max()), 2)}

    # second measurement on the solo drum stem: first rise of the kick (no other instrument in the way)
    dstem = sf.read(f'{W}/{V}/st_davul.wav', dtype='float64')[0][CUT:CUT + N].mean(1); t2 = []; b2 = []
    for bi, (ch, kind, k, vb) in enumerate(bars):
        if kind in ('final', 'roll', 'intro_ansfill', 'ansfill'): continue
        for bt in range(4):
            if kind in ('voc', 'intro_a') and bt == 3: continue          # tom fill there
            if kind == 'fillin' and bt < 2: continue                     # snare/tom fill there
            t0 = (bi * 4 + bt) * BEAT; i0 = max(0, int((t0 - 0.005) * sr)); seg = np.abs(dstem[i0:int((t0 + 0.03) * sr)])
            t2.append((i0 + int(np.argmax(seg >= 0.25 * seg.max()))) / sr); b2.append(bi * 4 + bt)
    t2 = np.array(t2); b2 = np.array(b2); sl2, ic2 = np.polyfit(b2, t2, 1); dv2 = 1000 * (t2 - b2 * BEAT)
    check(abs((sl2 - BEAT) * b2.max()) < 0.002, f'drum stem, {len(t2)} kick hits: fitted beat {sl2:.6f} s, drift over the whole song {1000 * (sl2 - BEAT) * b2.max():+.2f} ms, '
          f'kick first rise minus grid: mean {dv2.mean():+.2f} ms (first 16 beats {dv2[:16].mean():+.2f}, last 16 {dv2[-16:].mean():+.2f}), sd {dv2.std():.2f} ms')
    rep['grid'].update(kick_stem_fitted_beat_s=round(float(sl2), 6), drift_whole_song_ms=round(float(1000 * (sl2 - BEAT) * b2.max()), 2), kick_rise_minus_grid_ms_mean=round(float(dv2.mean()), 2))
    print('[5] MIDI files vs zaman json')
    chn = {v: int(k) for k, v in Mt['chn'].items()}
    def midi_ons(fn):
        mid = mido.MidiFile(fn); t = 0; tempo = 500000; ons = {}
        for m in mid.tracks[0]:
            t += m.time
            if m.type == 'set_tempo': tempo = m.tempo
            if m.type == 'note_on' and m.velocity > 0: ons.setdefault((m.channel, m.note), []).append(t * tempo / 1e6 / mid.ticks_per_beat)
        return ons, tempo
    for part, fn, fr in (('lead', f'{O}/midi/altyapi_{V}.mid', f'{W}/{V}/band.mid'), ('ezgi_alti', f'{O}/midi/ezgi_alti_{V}.mid', f'{W}/{V}/alt.mid')):
        ons, tempo = midi_ons(fn); onr, _ = midi_ons(fr); miss = 0; mx = 0; missr = 0; mxr = 0; cnt = 0
        for n in Z['ezgi_notalari']:
            if n['parti'] != part: continue
            cnt += 1; key = (chn[n['enstruman']], n['midi'])
            dd = min([abs(x - n['baslangic']) for x in ons.get(key, [])] or [9]); mx = max(mx, dd if dd < 9 else 0); miss += dd > 0.002
            adv = Mt['adv_ticks'].get(n['enstruman'], 0) * Mt['BEAT_MIDI'] / Mt['TPB']; tr_ = n['baslangic'] + Mt['PRE'] * Mt['BEAT_MIDI'] - adv
            dr = min([abs(x - tr_) for x in onr.get(key, [])] or [9]); mxr = max(mxr, dr if dr < 9 else 0); missr += dr > 0.002
        check(miss == 0 and missr == 0, f'{os.path.basename(fn)}: {cnt} "{part}" notes of the json found on the grid in the score MIDI (max deviation {1000 * mx:.3f} ms) and in the '
              f'rendered MIDI at grid minus the documented advance (max deviation {1000 * mxr:.3f} ms); MIDI tempo {tempo} us/beat')
    print('       documented note advances (ms):', Z['gecikme_telafisi']['one_alma_ms'])
    print('[6] pitch and time of the melody notes, detected in the solo stems')
    stem = lambda n: sf.read(f'{W}/{V}/st_{n}.wav', dtype='float64')[0][CUT:CUT + N].mean(1)
    S = {n: stem(n) for n in ('trompet', 'glockenspiel', 'klarnet', 'glockenspiel_hafif')}
    S['ezgi_alti (teslim dosyası)'] = X['ezgi_alti'].mean(1)
    ENV = {n: envelope(x, sr) for n, x in S.items()}
    rep['notes'] = {}
    def run(label, stemname, notes, method, ptol=0.30, ttol=(-0.015, 0.050), expect=lambda n: n['midi']):
        x = S[stemname]; e, hop, win = ENV[stemname]; bad = []; perr = []; terr = []; fallback = [0, 0, 0]
        for n in notes:
            t0, du = n['baslangic'], n['sure']
            i0 = int((t0 + 0.035) * sr); i1 = int((t0 + max(0.16, min(du, 0.45) - 0.01)) * sr)
            if method == 'yin': f = yin(x[i0:i1], sr)
            elif method == 'band': f = bandpeak(x[i0:i1], sr, 300.0, 1100.0)
            else:
                f, fb = glockpitch(x, sr, t0, du, expect(n)); agree = bool(np.isfinite(fb) and abs(f2m(fb) - expect(n)) <= ptol)
                prev = [m for m in notes if 0 < t0 - m['baslangic'] < 0.7 * BEAT]              # the note just before (an eighth earlier)
                fallback[0] += 1; fallback[1] += agree; fallback[2] += (not agree) and any(m['midi'] == n['midi'] for m in prev)
            pe = f2m(f) - expect(n) if np.isfinite(f) else 99; te = onset(e, hop, win, t0, du) - t0
            perr.append(pe); terr.append(te)
            if abs(pe) > ptol or not (ttol[0] <= te <= ttol[1]): bad.append((n['olcu'], n['vurus'], n['nota'], round(float(pe), 2), round(float(1000 * te), 1)))
        perr = np.array(perr); terr = np.array(terr) * 1000
        rep['notes'].setdefault('_glock_blind', {})
        ok = check(not bad, f'{label}: {len(notes)} notes checked, {len(notes) - len(bad)} matched (pitch within {ptol} st and onset within {1000 * ttol[0]:.0f}..+{1000 * ttol[1]:.0f} ms); '
                   f'pitch error mean {100 * perr.mean():+.1f} cents, max |err| {100 * np.abs(perr).max():.1f} cents; '
                   f'half-level onset minus grid: median {np.median(terr):+.1f} ms, min {terr.min():+.1f}, max {terr.max():+.1f}')
        if bad: print('        first mismatches (bar, beat, note, pitch err st, onset ms):', bad[:8])
        rep['notes'][label] = {'checked': len(notes), 'matched': len(notes) - len(bad), 'pitch_err_cents_mean': round(float(100 * perr.mean()), 1),
                               'pitch_err_cents_max_abs': round(float(100 * np.abs(perr).max()), 1), 'onset_ms_median': round(float(np.median(terr)), 1),
                               'onset_ms_min': round(float(terr.min()), 1), 'onset_ms_max': round(float(terr.max()), 1)}
        if method == 'glock':
            print(f'        (glockenspiel: pass/fail = expected fundamental present as a spectral peak; the blind "lowest newly appearing partial" estimate agrees for {fallback[1]} of {fallback[0]} notes; '
                  f'{fallback[2]} of the {fallback[0] - fallback[1]} others repeat the pitch of the note just before, which is still ringing)')
            rep['notes'].setdefault('_glock_blind', {})[label] = {'checked': fallback[0], 'blind_agrees': fallback[1], 'disagree_but_repeated_pitch': fallback[2]}
        return len(notes), len(notes) - len(bad)
    NT = Z['ezgi_notalari']
    sel = lambda part, ins, mono=True: [n for n in NT if n['parti'] == part and n['enstruman'] == ins and n['tek_ses'] == mono]
    tot = [0, 0]
    for lab, st, notes, meth, kw in (
            ('lead trompet', 'trompet', sel('lead', 'trompet'), 'yin', {}),
            ('lead glockenspiel (+1 oktav)', 'glockenspiel', sel('lead', 'glockenspiel'), 'glock', {'ttol': (-0.010, 0.030)}),
            ('ezgi_alti klarnet', 'klarnet', sel('ezgi_alti', 'klarnet'), 'yin', {}),
            ('ezgi_alti glockenspiel (+1 oktav)', 'glockenspiel_hafif', sel('ezgi_alti', 'glockenspiel_hafif'), 'glock', {'ttol': (-0.010, 0.030)}),
            ('ezgi_alti teslim dosyası (klarnet+glockenspiel karışık; 300-1100 Hz en güçlü tepe)', 'ezgi_alti (teslim dosyası)', sel('ezgi_alti', 'klarnet'), 'band', {'ttol': (-0.020, 0.050)})):
        c, m = run(lab, st, notes, meth, **kw); tot[0] += c; tot[1] += m
    # chords of the final bar on the trumpet and glockenspiel stems: every expected partial must be a spectral peak
    cb = []
    for ins in ('trompet', 'glockenspiel'):
        for n in sel('lead', ins, mono=False):
            x = S[ins]; i0 = int((n['baslangic'] + 0.05) * sr); seg = x[i0:i0 + int(0.5 * sr)]
            Nf = 1 << 17; Xs = np.abs(np.fft.rfft(seg * np.hanning(len(seg)), Nf)); F = np.fft.rfftfreq(Nf, 1 / sr)
            f0 = 440 * 2 ** ((n['midi'] - 69) / 12); a_, b_ = np.searchsorted(F, [f0 * 2 ** (-1 / 12), f0 * 2 ** (1 / 12)])
            k = a_ + int(np.argmax(Xs[a_:b_])); pe = f2m(F[k]) - n['midi']
            cb.append(abs(pe) < 0.3 and Xs[k] > 0.05 * Xs.max())
    check(all(cb), f'final chords (bar 63, beats 0 and 3): {len(cb)} chord notes on trumpet/glockenspiel stems, {sum(cb)} found as spectral peaks at the expected pitch')
    rep['notes']['final_chord_notes'] = {'checked': len(cb), 'matched': int(sum(cb))}
    rep['notes_total'] = {'checked': tot[0] + len(cb), 'matched': tot[1] + int(sum(cb))}
    # intended pitches (as required by the task)
    want = {'C': {'ans': ['E5', 'E5', 'D5', 'D5', 'C5'], 'glk': ['E6', 'E6', 'D6', 'D6', 'C6'], 'pa': ['C5', 'C5', 'C5', 'G4', 'A4', 'A4', 'G4'],
                  'lpa': ['C5', 'C5', 'C5', 'G4', 'A4', 'A4', 'G4']},
            'G': {'ans': ['B4', 'B4', 'A4', 'A4', 'G4'], 'glk': ['B5', 'B5', 'A5', 'A5', 'G5'], 'pa': ['G5', 'G5', 'G5', 'D5', 'E5', 'E5', 'D5'],
                  'lpa': ['G4', 'G4', 'G4', 'D4', 'E4', 'E4', 'D4']}}.get(Mt['key'])
    if want:
        okp = True; nb = {}
        for bi, (ch, kind, k, vb) in enumerate(bars):
            g = lambda part, ins: [n['nota'] for n in NT if n['olcu'] == bi and n['parti'] == part and n['enstruman'] == ins]
            b = lambda part, ins: [n['vurus'] for n in NT if n['olcu'] == bi and n['parti'] == part and n['enstruman'] == ins]
            PAB = [0, .5, 1, 1.5, 2, 2.5, 3]
            if kind in ('ans', 'ans2', 'intro_ans', 'intro_ansfill', 'ansfill'):
                okp &= g('lead', 'trompet') == want['ans'] and g('lead', 'glockenspiel') == want['glk'] and b('lead', 'trompet') == [0, .5, 1, 1.5, 2] and not g('ezgi_alti', 'klarnet')
            elif kind == 'intro_a':
                okp &= g('lead', 'trompet') == want['lpa'] and b('lead', 'trompet') == PAB and not g('ezgi_alti', 'klarnet')
            elif kind in AK:
                okp &= g('ezgi_alti', 'klarnet') == want['pa'] and b('ezgi_alti', 'klarnet') == PAB and not g('lead', 'trompet')
            elif kind == 'fillin':
                okp &= g('ezgi_alti', 'klarnet') == [want['pa'][0]] * 4 and b('ezgi_alti', 'klarnet') == [2, 2.5, 3, 3.5] and not g('lead', 'trompet')
            elif kind == 'slot':
                okp &= not [n for n in NT if n['olcu'] == bi]
            nb[kind] = nb.get(kind, 0) + 1
        vk = [bars[INTRO + i][1] for i in range(VB)]
        okp &= vk == ['voc', 'ans', 'voc_cut', 'slot', 'slot', 'fillin', 'voc', 'ansfill'] and all([bars[INTRO + k * VB + i][1] for i in range(VB)] == vk for k in range(NV))
        check(okp, f'note names and beats in zaman json match the task: loud answer {want["ans"]} (+glockenspiel {want["glk"]}), phrase A under the vocal {want["pa"]}, '
                   f'repeated do under "diye bagirir" 4 x {want["pa"][0]} on beats 2, 2.5, 3, 3.5 of verse bar {FB}, intro phrase A (loud lead) {want["lpa"]}; nothing melodic in the slot bars; '
                   f'verse bar kinds {vk}; bars per kind {nb}')
        rep['bar_kinds'] = nb

    print('[7] the separately rendered stems add up to the band render (so the stem checks apply to the mix)')
    band = sf.read(f'{W}/{V}/band.wav', dtype='float64')[0][CUT:CUT + N]
    ssum = sum(sf.read(f'{W}/{V}/st_{n}.wav', dtype='float64')[0][CUT:CUT + N] for n in ('bas', 'banjo', 'akordeon', 'piyano', 'glockenspiel', 'trompet', 'brass', 'davul'))
    resid = db(rms(band - ssum) / rms(band))
    check(resid < -40, f'band render minus sum of 8 stems: {resid:.1f} dB relative to the band')
    f = np.linspace(1, 0, int(0.4 * sr)); bm = band * Mt['gain']; bm[-len(f):] *= f[:, None]
    d2 = db(rms(X['altyapi'] - bm) / rms(bm)); corr = float(np.corrcoef(X['altyapi'].mean(1), bm.mean(1))[0, 1])
    print(f'       delivered altyapi vs gain-only band (difference = limiter action): {d2:.1f} dB, correlation {corr:.5f}')
    rep['stems_sum_residual_db'] = round(float(resid), 1); rep['limiter_difference_db'] = round(float(d2), 1)

    print(f'[8] levels per verse bar (altyapi, dBFS RMS); slot bars {SB[0]} and {SB[1]} must be at least 8 dB below the normal bars')
    A2 = X['altyapi']; E2 = X['ezgi_alti']; tab = []
    seg = lambda t0, t1: A2[int(t0 * sr):int(t1 * sr)]
    for k in range(NV):
        v0 = INTRO + k * VB
        tab.append([db(rms(seg((v0 + i) * BAR, (v0 + i + 1) * BAR))) for i in range(VB)])
        print(f'       verse {k + 1}: ' + ' '.join(f'{v:6.1f}' for v in tab[-1]))
    tab = np.array(tab); NB = [i for i in range(VB) if i not in SB]; FULLB = [i for i in NB if i != FB]
    pm = lambda cols: 10 * np.log10((10 ** (tab[:, cols] / 10)).mean(1))
    normal = pm(NB); full = pm(FULLB); dA = normal - tab[:, SB[0]]; dB_ = normal - tab[:, SB[1]]
    dq = tab[:, NB].min(1) - tab[:, SB].max(1)
    check(dA.min() >= 8 and dB_.min() >= 8 and dq.min() >= 8,
          f'slot bar {SB[0]}: {dA.min():.1f}..{dA.max():.1f} dB below the mean of the six normal bars {NB}; slot bar {SB[1]}: {dB_.min():.1f}..{dB_.max():.1f} dB; '
          f'against the five full-band bars {FULLB}: {(full - tab[:, SB[0]]).min():.1f} / {(full - tab[:, SB[1]]).min():.1f} dB (smallest); quietest normal bar minus loudest slot bar: {dq.min():.1f} dB')
    rep['slot'] = {'slot_bars': SB, 'first_slot_below_normal_db_min': round(float(dA.min()), 1), 'first_slot_max': round(float(dA.max()), 1),
                   'second_slot_below_normal_db_min': round(float(dB_.min()), 1), 'second_slot_max': round(float(dB_.max()), 1),
                   'quietest_normal_minus_loudest_slot_db_min': round(float(dq.min()), 1),
                   'normal_bars_dbfs_mean': round(float(normal.mean()), 1), 'slot_bars_dbfs_mean': round(float(tab[:, SB].mean()), 1)}
    # bar 5: beats 0-1 = fill (drums + bass only), beats 2-3 = full groove
    stm = {n: sf.read(f'{W}/{V}/st_{n}.wav', dtype='float64')[0][CUT:CUT + N] for n in ('bas', 'banjo', 'akordeon', 'piyano', 'glockenspiel', 'trompet', 'brass', 'davul')}
    GRV = ('banjo', 'akordeon', 'piyano', 'brass'); h1 = []; h2 = []; quiet = []; pres = []; drb = []; ref2 = []; fl = []
    for k in range(NV):
        t5 = (INTRO + k * VB + FB) * BAR; a0, a1, a2 = int(t5 * sr), int((t5 + 2 * BEAT - 0.005) * sr), int((t5 + 2 * BEAT) * sr); a3 = int((t5 + BAR) * sr)
        h1.append(db(rms(A2[a0:a1]))); h2.append(db(rms(A2[a2:a3])))
        oth_ = sum(stm[n] for n in ('banjo', 'akordeon', 'piyano', 'glockenspiel', 'trompet', 'brass'))
        quiet.append(db(rms(oth_[a0:a1])) - db(rms(oth_[a2:a3])))                      # melodic/chord stems in the fill half vs. the groove half
        drb.append(db(rms((stm['davul'] + stm['bas'])[a0:a1])) - db(rms(sum(stm.values())[a0:a1])))
        pres.append(min(db(rms(stm[n][a2:a3])) for n in GRV))
        t0b = (INTRO + k * VB) * BAR                                                   # reference: beats 2-3 of verse bar 0 (a normal vocal bar)
        ref2.append(db(rms(A2[int((t0b + 2 * BEAT) * sr):int((t0b + BAR) * sr)])))
        fl.append(max(db(rms(stm[n][a2:a3])) - db(rms(stm[n][int((t0b + 2 * BEAT) * sr):int((t0b + BAR) * sr)])) for n in ('banjo', 'akordeon', 'piyano')) )
    h1, h2, quiet, drb, ref2 = map(np.array, (h1, h2, quiet, drb, ref2))
    check(quiet.max() < -40 and np.abs(drb).max() < 0.05,
          f'verse bar {FB}, beats 0-1 (fill): banjo+accordion+piano+brass+trumpet+glockenspiel stems are {-quiet.max():.0f} dB or more below their own level in beats 2-3; '
          f'drums+bass make up the whole band there (difference to the 8-stem sum {np.abs(drb).max():.3f} dB); altyapi level {h1.mean():.1f} dBFS')
    check(np.abs(h2 - ref2).max() < 3.0 and min(pres) > -60,
          f'verse bar {FB}, beats 2-3 (full groove back): altyapi {h2.mean():.1f} dBFS, i.e. {(h2 - ref2).min():+.1f}..{(h2 - ref2).max():+.1f} dB against beats 2-3 of verse bar 0 ({ref2.mean():.1f} dBFS); '
          f'banjo, accordion, piano and brass stems all sound there (quietest of them {min(pres):.1f} dB raw); beats 2-3 are {(h2 - tab[:, SB].max(1)).min():.1f} dB or more above the slot bars')
    rep['fill_bar'] = {'bar': FB, 'beats01_dbfs': round(float(h1.mean()), 1), 'beats23_dbfs': round(float(h2.mean()), 1), 'beats23_minus_bar0_beats23_db': [round(float((h2 - ref2).min()), 1), round(float((h2 - ref2).max()), 1)],
                       'chord_and_lead_stems_in_beats01_rel_beats23_db_max': round(float(quiet.max()), 1)}
    oth = {}
    for nme, i0b, nb in (('intro', 0, INTRO), ('ending', INTRO + NV * VB, Mt['END'])):
        oth[nme] = [round(float(db(rms(A2[int((i0b + i) * BAR * sr):int((i0b + i + 1) * BAR * sr)]))), 1) for i in range(nb)]
    tl = db(rms(A2[int(TOTAL * BAR * sr):])); print(f'       intro bars: {oth["intro"]}   ending bars: {oth["ending"]}   tail after bar 64: {tl:.1f} dBFS')
    # does the band of bar 5 ring into the animal slot? level of the first 250 ms of bar 6 against the same span of bar 7
    h6 = np.array([db(rms(A2[int((INTRO + k * VB + SB[0]) * BAR * sr):int(((INTRO + k * VB + SB[0]) * BAR + 0.25) * sr)])) for k in range(NV)])
    h7 = np.array([db(rms(A2[int((INTRO + k * VB + SB[1]) * BAR * sr):int(((INTRO + k * VB + SB[1]) * BAR + 0.25) * sr)])) for k in range(NV)])
    print(f'       first 250 ms of slot bar {SB[0]}: {h6.mean():.1f} dBFS, of slot bar {SB[1]}: {h7.mean():.1f} dBFS (difference = ring-over of bar {SB[0] - 1} into the first animal call: {(h6 - h7).mean():+.1f} dB)')
    rep['slot_head'] = {'first_slot_first_250ms_dbfs': round(float(h6.mean()), 1), 'second_slot_first_250ms_dbfs': round(float(h7.mean()), 1)}
    rep['intro_ending_bars_dbfs'] = oth
    print('[9] under-vocal stem: default level and audibility proxy')
    act = np.zeros(len(A2), bool); sil = np.ones(len(A2), bool)
    for bi, (ch, kind, k, vb) in enumerate(bars):
        if kind in AK: act[int(bi * BAR * sr):int((bi + 1) * BAR * sr)] = True
        if kind == 'fillin': act[int((bi * BAR + 2 * BEAT) * sr):int((bi + 1) * BAR * sr)] = True
    rel = db(rms(E2[act]) / rms(A2[act]))
    # the stem must be silent outside its bars (except reverb tails right after them)
    out_lvl = db(rms(E2[~act]) + 1e-12) - db(rms(E2[act]))
    snr = []; snr2 = []
    am = A2.mean(1); em = E2.mean(1)
    for n in sel('ezgi_alti', 'klarnet'):
        i0 = int((n['baslangic'] + 0.02) * sr); i1 = int((n['baslangic'] + max(0.2, min(n['sure'], 0.5))) * sr)
        w = np.hanning(i1 - i0); Fa = np.abs(np.fft.rfft(am[i0:i1] * w, 1 << 15)) ** 2; Fe = np.abs(np.fft.rfft(em[i0:i1] * w, 1 << 15)) ** 2; F = np.fft.rfftfreq(1 << 15, 1 / sr)
        f0 = 440 * 2 ** ((n['midi'] - 69) / 12)
        for hh, lst in ((1, snr), (2, snr2)):
            a_, b_ = np.searchsorted(F, [hh * f0 * 2 ** (-1 / 6), hh * f0 * 2 ** (1 / 6)]); lst.append(10 * np.log10(Fe[a_:b_].sum() / Fa[a_:b_].sum()))
    snr = np.array(snr); snr2 = np.array(snr2)
    check(abs(rel - Mt['alt_db']) < 0.6, f'ezgi_alti RMS relative to altyapi in the bars where it plays: {rel:.1f} dB (default set to {Mt["alt_db"]} dB before limiting); '
          f'stem level outside its bars: {out_lvl:.1f} dB rel. to its active level')
    print(f'       stem vs band energy in the third-octave band around each clarinet note ({len(snr)} notes): median {np.median(snr):+.1f} dB, 10th pct {np.percentile(snr, 10):+.1f}, min {snr.min():+.1f}; '
          f'around the glockenspiel octave (2 f0): median {np.median(snr2):+.1f} dB, min {snr2.min():+.1f}')
    lead = sum(sf.read(f'{W}/{V}/st_{n}.wav', dtype='float64')[0][CUT:CUT + N] for n in ('trompet', 'brass', 'glockenspiel')).mean(1)
    rest = sum(sf.read(f'{W}/{V}/st_{n}.wav', dtype='float64')[0][CUT:CUT + N] for n in ('bas', 'banjo', 'akordeon', 'piyano', 'davul')).mean(1)
    ref = []
    for n in sel('lead', 'trompet'):
        if bars[n['olcu']][1] not in ('ans', 'intro_ans', 'ansfill'): continue
        i0 = int((n['baslangic'] + 0.02) * sr); i1 = int((n['baslangic'] + max(0.2, min(n['sure'], 0.5))) * sr)
        w = np.hanning(i1 - i0); Fa = np.abs(np.fft.rfft(rest[i0:i1] * w, 1 << 15)) ** 2; Fe = np.abs(np.fft.rfft(lead[i0:i1] * w, 1 << 15)) ** 2; F = np.fft.rfftfreq(1 << 15, 1 / sr)
        f0 = 440 * 2 ** ((n['midi'] - 69) / 12); a_, b_ = np.searchsorted(F, [f0 * 2 ** (-1 / 6), f0 * 2 ** (1 / 6)]); ref.append(10 * np.log10(Fe[a_:b_].sum() / Fa[a_:b_].sum()))
    ansmask = np.zeros(len(A2), bool)
    for bi, (ch, kind, k, vb) in enumerate(bars):
        if kind in ('ans', 'ansfill') and k < NV: ansmask[int(bi * BAR * sr):int((bi + 1) * BAR * sr)] = True
    lead_rel = db(rms(lead[ansmask[:len(lead)]]) / rms(rest[ansmask[:len(rest)]]))
    print(f'       for comparison, the LOUD lead (trumpet+brass+glockenspiel) in the answer bars: RMS {lead_rel:+.1f} dB relative to the rest of the band; '
          f'same third-octave proxy around the trumpet notes: median {np.median(ref):+.1f} dB')
    rep['loud_lead_reference'] = {'rms_rel_rest_of_band_db': round(float(lead_rel), 1), 'f0_band_lead_minus_rest_db_median': round(float(np.median(ref)), 1)}
    rep['ezgi_alti_level'] = {'rms_rel_band_db': round(float(rel), 1), 'f0_band_stem_minus_band_db_median': round(float(np.median(snr)), 1),
                              'f0_band_p10': round(float(np.percentile(snr, 10)), 1), 'f0_band_min': round(float(snr.min()), 1),
                              'octave_band_median': round(float(np.median(snr2)), 1), 'stem_rms_dbfs_active': round(float(db(rms(E2[act]))), 1),
                              'stem_peak_dbfs': round(float(db(np.abs(E2).max())), 1)}
    Lc, Rc = X['altyapi'][:, 0], X['altyapi'][:, 1]; cc = float(np.corrcoef(Lc, Rc)[0, 1]); mono = meter.integrated_loudness(np.repeat(X['altyapi'].mean(1)[:, None], 2, 1))
    dc = np.abs(X['altyapi'].mean(0)).max()
    print(f'[9b] stereo/mono: L-R correlation {cc:.3f}; mono fold-down (L+R)/2 loudness {mono:.2f} LUFS (stereo {rep["altyapi"]["lufs_pyloudnorm"]}); DC offset {db(dc):.0f} dBFS')
    rep['mono'] = {'lr_correlation': round(cc, 3), 'mono_fold_down_lufs': round(float(mono), 2)}
    print('[10] raw stem levels (dB RMS over verses 1-2, before master gain)')
    lv = {}
    for nme in ('davul', 'bas', 'banjo', 'akordeon', 'piyano', 'brass', 'trompet', 'glockenspiel', 'klarnet', 'glockenspiel_hafif'):
        x = sf.read(f'{W}/{V}/st_{nme}.wav', dtype='float64')[0][CUT:CUT + N]
        lv[nme] = round(float(db(rms(x[int(INTRO * BAR * sr):int((INTRO + 2 * VB) * BAR * sr)]))), 1)
    print('       ' + ', '.join(f'{k} {v}' for k, v in lv.items()))
    rep['raw_stem_levels_db'] = lv

if len(VARS) == 2:
    a, b = VARS
    print(f'\n================ {a} vs {b}: identical except for transposition ================')
    ok = True; diffs = {}
    for ch in EV[a]:
        ea, eb = EV[a][ch], EV[b][ch]
        if len(ea) != len(eb): ok = False; diffs[ch] = 'different number of notes'; continue
        # compare after sorting by (time, duration, velocity, pitch class relative to the key)
        ka = sorted((e[0], e[1], e[3], e[2]) for e in ea); kb = sorted((e[0], e[1], e[3], e[2]) for e in eb)
        same_rhythm = [x[:3] for x in ka] == [x[:3] for x in kb]
        ta = sorted((e[0], e[1], e[3], (e[2] - TONV[a]) % 12) for e in ea); tb = sorted((e[0], e[1], e[3], (e[2] - TONV[b]) % 12) for e in eb)
        d_ = sorted({x[3] - y[3] for x, y in zip(ka, kb)})
        diffs[ch] = {'notes': len(ea), 'same_times_durations_velocities': same_rhythm, 'pitch_shift_semitones_seen': d_,
                     'same_scale_degrees': ta == tb if ch != 'davul' else ka == kb}
        ok &= same_rhythm and diffs[ch]['same_scale_degrees']
        print(f'       {ch:20s} {len(ea):5d} notes, same times/durations/velocities: {same_rhythm}, same scale degrees: {diffs[ch]["same_scale_degrees"]}, pitch shifts seen ({a} minus {b}): {d_}')
    check(ok, 'all channels: same rhythm, durations, velocities and scale degrees; only the key (and register per part) differs')
    da = sf.read(f'{W}/{a}/st_davul.wav')[0]; dbb = sf.read(f'{W}/{b}/st_davul.wav')[0]
    check(da.shape == dbb.shape and np.abs(da - dbb).max() == 0, 'drum stems of the two variants are bit-identical')
    za, zb = (json.load(open(f'{O}/zaman_{v}.json')) for v in VARS)
    same_t = all(za[k] == zb[k] for k in ('tempo_bpm', 'vurus_sn', 'olcu_sn', 'toplam_olcu', 'muzik_bitis_sn', 'son_vurus_sn', 'dosya_suresi_sn')) and \
        [v['olcu_baslangiclari'] for v in za['kitalar']] == [v['olcu_baslangiclari'] for v in zb['kitalar']] and \
        [(n['baslangic'], n['sure'], n['parti'], n['enstruman']) for n in za['ezgi_notalari']] == [(n['baslangic'], n['sure'], n['parti'], n['enstruman']) for n in zb['ezgi_notalari']]
    check(same_t, 'the two zaman json files have identical times (tempo, bars, verses, every melody note)')
    REPORT['variants_identical_except_transposition'] = {'ok': bool(ok and same_t), 'per_channel': diffs}

REPORT['failed_checks'] = FAIL
REPORT['note'] = 'All values are measurements made by code. Nothing here was judged by ear.'
json.dump(REPORT, open(os.environ.get('DOGRULAMA_JSON', f'{O}/dogrulama.json'), 'w'), ensure_ascii=False, indent=1)
print('\nRESULT:', 'ALL CHECKS PASSED' if not FAIL else f'{len(FAIL)} CHECK(S) FAILED')
for f_ in FAIL: print('  -', f_)
sys.exit(1 if FAIL else 0)
