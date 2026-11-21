#!/usr/bin/env python3
# Verification of the yeni3 backing (measurements only; nobody listened to anything).
# usage: dogrula.py <output folder> <scratch folder used by build.py> [variant ...]
# Writes <output folder>/dogrulama.json and prints a report. Exit code 1 if any hard check fails.
import json, os, re, subprocess, sys
import numpy as np, soundfile as sf, mido, pyloudnorm
from scipy.signal import resample_poly, butter, sosfiltfilt

O, W = sys.argv[1:3]
VARS = sys.argv[3:] or ['dogal', 'ezgi']
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
def specpeak(x, sr, lo=300.0, hi=6000.0):
    """Strongest spectral peak in a wide band (for the glockenspiel, whose partials are not harmonic)."""
    Nf = 1 << 17; X = np.abs(np.fft.rfft((x - x.mean()) * np.hanning(len(x)), Nf)); F = np.fft.rfftfreq(Nf, 1 / sr)
    a, b = np.searchsorted(F, [lo, hi]); k = a + int(np.argmax(X[a:b]))
    a0, b0, c0 = np.log(X[k - 1] + 1e-20), np.log(X[k] + 1e-20), np.log(X[k + 1] + 1e-20)
    return (k + 0.5 * (a0 - c0) / (a0 - 2 * b0 + c0 + 1e-20)) * sr / Nf
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
    EV[V] = Mt['events']; rep = REPORT[V] = {'key': Mt['key']}
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

    print('[4] beat grid measured in altyapi (kick onsets)')
    a = X['altyapi'].mean(1)
    lp = sosfiltfilt(butter(4, [35, 150], 'bandpass', fs=sr, output='sos'), a)
    e, hop, win = envelope(lp, sr, win=0.004, hop=0.0005)
    tt = []; bb = []
    for bi, (ch, kind, k, vb) in enumerate(bars):
        if kind == 'final': continue
        for bt in range(4):
            t0 = (bi * 4 + bt) * BEAT; i0 = int((t0 - 0.03) / hop); i1 = int((t0 + 0.06) / hop)
            if i0 < 0: i0 = 0
            seg = e[i0:i1]; de = np.diff(seg); j = int(np.argmax(de))
            tt.append((i0 + j) * hop + win / 2); bb.append(bi * 4 + bt)
    tt = np.array(tt); bb = np.array(bb); sl, ic = np.polyfit(bb, tt, 1); res = tt - (sl * bb + ic); dev = tt - bb * BEAT
    check(abs(sl - BEAT) < 2e-5 and abs(np.median(dev)) < 0.012 and res.std() < 0.004,
          f'{len(tt)} kick onsets: fitted beat {sl:.6f} s (nominal {BEAT:.6f}; => bar {4 * sl:.5f} s, {60 / sl:.3f} BPM), '
          f'steepest-rise time minus grid: median {1000 * np.median(dev):+.2f} ms, min {1000 * dev.min():+.2f}, max {1000 * dev.max():+.2f}, residual sd {1000 * res.std():.2f} ms')
    rep['grid'] = {'kick_onsets': len(tt), 'fitted_beat_s': round(float(sl), 6), 'fitted_bar_s': round(float(4 * sl), 5), 'fitted_bpm': round(float(60 / sl), 3),
                   'onset_minus_grid_ms_median': round(float(1000 * np.median(dev)), 2), 'min': round(float(1000 * dev.min()), 2), 'max': round(float(1000 * dev.max()), 2)}

    print('[5] MIDI files vs zaman json')
    for part, fn in (('lead', f'{O}/midi/altyapi_{V}.mid'), ('ezgi_alti', f'{O}/midi/ezgi_alti_{V}.mid')):
        mid = mido.MidiFile(fn); t = 0; tempo = 500000; ons = {}
        for m in mid.tracks[0]:
            t += m.time
            if m.type == 'set_tempo': tempo = m.tempo
            if m.type == 'note_on' and m.velocity > 0: ons.setdefault((m.channel, m.note), []).append(t * tempo / 1e6 / mid.ticks_per_beat)
        chn = {v: int(k) for k, v in Mt['chn'].items()}
        miss = 0; mx = 0
        for n in Z['ezgi_notalari']:
            if n['parti'] != part: continue
            c = ons.get((chn[n['enstruman']], n['midi']), []); dd = min([abs(x - n['baslangic']) for x in c] or [9])
            mx = max(mx, dd if dd < 9 else 0); miss += dd > 0.002
        cnt = sum(1 for n in Z['ezgi_notalari'] if n['parti'] == part)
        check(miss == 0, f'{os.path.basename(fn)}: {cnt} "{part}" notes of the json found in the MIDI at their time (max deviation {1000 * mx:.3f} ms; MIDI tempo {tempo} us/beat)')

    print('[6] pitch and time of the melody notes, detected in the solo stems')
    stem = lambda n: sf.read(f'{W}/{V}/st_{n}.wav', dtype='float64')[0][CUT:CUT + N].mean(1)
    S = {n: stem(n) for n in ('trompet', 'glockenspiel', 'klarnet', 'glockenspiel_hafif')}
    S['ezgi_alti (teslim dosyası)'] = X['ezgi_alti'].mean(1)
    ENV = {n: envelope(x, sr) for n, x in S.items()}
    rep['notes'] = {}
    def run(label, stemname, notes, method, ptol=0.30, ttol=(-0.010, 0.050), expect=lambda n: n['midi']):
        x = S[stemname]; e, hop, win = ENV[stemname]; bad = []; perr = []; terr = []
        for n in notes:
            t0, du = n['baslangic'], n['sure']
            i0 = int((t0 + 0.035) * sr); i1 = int((t0 + max(0.16, min(du, 0.45) - 0.01)) * sr)
            f = yin(x[i0:i1], sr) if method == 'yin' else specpeak(x[int((t0 + 0.012) * sr):i1], sr)
            pe = f2m(f) - expect(n) if np.isfinite(f) else 99; te = onset(e, hop, win, t0, du) - t0
            perr.append(pe); terr.append(te)
            if abs(pe) > ptol or not (ttol[0] <= te <= ttol[1]): bad.append((n['olcu'], n['vurus'], n['nota'], round(float(pe), 2), round(float(1000 * te), 1)))
        perr = np.array(perr); terr = np.array(terr) * 1000
        ok = check(not bad, f'{label}: {len(notes)} notes checked, {len(notes) - len(bad)} matched (pitch within {ptol} st and onset within {1000 * ttol[0]:.0f}..+{1000 * ttol[1]:.0f} ms); '
                   f'pitch error mean {100 * perr.mean():+.1f} cents, max |err| {100 * np.abs(perr).max():.1f} cents; '
                   f'half-level onset minus grid: median {np.median(terr):+.1f} ms, min {terr.min():+.1f}, max {terr.max():+.1f}')
        if bad: print('        first mismatches (bar, beat, note, pitch err st, onset ms):', bad[:8])
        rep['notes'][label] = {'checked': len(notes), 'matched': len(notes) - len(bad), 'pitch_err_cents_mean': round(float(100 * perr.mean()), 1),
                               'pitch_err_cents_max_abs': round(float(100 * np.abs(perr).max()), 1), 'onset_ms_median': round(float(np.median(terr)), 1),
                               'onset_ms_min': round(float(terr.min()), 1), 'onset_ms_max': round(float(terr.max()), 1)}
        return len(notes), len(notes) - len(bad)
    NT = Z['ezgi_notalari']
    sel = lambda part, ins, mono=True: [n for n in NT if n['parti'] == part and n['enstruman'] == ins and n['tek_ses'] == mono]
    tot = [0, 0]
    for lab, st, notes, meth, kw in (
            ('lead trompet', 'trompet', sel('lead', 'trompet'), 'yin', {}),
            ('lead glockenspiel (+1 oktav)', 'glockenspiel', sel('lead', 'glockenspiel'), 'peak', {'ttol': (-0.010, 0.030)}),
            ('ezgi_alti klarnet', 'klarnet', sel('ezgi_alti', 'klarnet'), 'yin', {}),
            ('ezgi_alti glockenspiel (+1 oktav)', 'glockenspiel_hafif', sel('ezgi_alti', 'glockenspiel_hafif'), 'peak', {'ttol': (-0.010, 0.030)}),
            ('ezgi_alti teslim dosyası (klarnet perdesi)', 'ezgi_alti (teslim dosyası)', sel('ezgi_alti', 'klarnet'), 'yin', {})):
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
    want = {'C': {'ans': ['E5', 'E5', 'D5', 'D5', 'C5'], 'glk': ['E6', 'E6', 'D6', 'D6', 'C6'], 'pa': ['C5', 'C5', 'C5', 'G4', 'A4', 'A4', 'G4']},
            'G': {'ans': ['B4', 'B4', 'A4', 'A4', 'G4'], 'glk': ['B5', 'B5', 'A5', 'A5', 'G5'], 'pa': ['G5', 'G5', 'G5', 'D5', 'E5', 'E5', 'D5']}}.get(Mt['key'])
    if want:
        okp = True; nb = 0
        for bi, (ch, kind, k, vb) in enumerate(bars):
            g = lambda part, ins: [n['nota'] for n in NT if n['olcu'] == bi and n['parti'] == part and n['enstruman'] == ins]
            b = lambda part, ins: [n['vurus'] for n in NT if n['olcu'] == bi and n['parti'] == part and n['enstruman'] == ins]
            if kind in ('ans', 'ans2', 'intro_ans', 'intro_ansfill'):
                okp &= g('lead', 'trompet') == want['ans'] and g('lead', 'glockenspiel') == want['glk'] and b('lead', 'trompet') == [0, .5, 1, 1.5, 2]; nb += 1
            if kind == 'voc':
                okp &= g('ezgi_alti', 'klarnet') == want['pa'] and b('ezgi_alti', 'klarnet') == [0, .5, 1, 1.5, 2, 2.5, 3]; nb += 1
            if kind == 'voc3':
                okp &= g('ezgi_alti', 'klarnet') == [want['pa'][0]] * 8 and b('ezgi_alti', 'klarnet') == [i * .5 for i in range(8)]; nb += 1
            if kind == 'voc4':
                okp &= b('ezgi_alti', 'klarnet') == [0, .5, 1, 1.5, 2] and [n[:-1] for n in g('ezgi_alti', 'klarnet')] == [n[:-1] for n in want['ans']]; nb += 1
        check(okp, f'note names in zaman json match the task: loud answer {want["ans"]} (+glockenspiel {want["glk"]}), phrase A under the vocal {want["pa"]} ({nb} bars checked)')

    print('[7] the separately rendered stems add up to the band render (so the stem checks apply to the mix)')
    band = sf.read(f'{W}/{V}/band.wav', dtype='float64')[0][CUT:CUT + N]
    ssum = sum(sf.read(f'{W}/{V}/st_{n}.wav', dtype='float64')[0][CUT:CUT + N] for n in ('bas', 'banjo', 'akordeon', 'piyano', 'glockenspiel', 'trompet', 'brass', 'davul'))
    resid = db(rms(band - ssum) / rms(band))
    check(resid < -40, f'band render minus sum of 8 stems: {resid:.1f} dB relative to the band')
    f = np.linspace(1, 0, int(0.4 * sr)); bm = band * Mt['gain']; bm[-len(f):] *= f[:, None]
    d2 = db(rms(X['altyapi'] - bm) / rms(bm)); corr = float(np.corrcoef(X['altyapi'].mean(1), bm.mean(1))[0, 1])
    print(f'       delivered altyapi vs gain-only band (difference = limiter action): {d2:.1f} dB, correlation {corr:.5f}')
    rep['stems_sum_residual_db'] = round(float(resid), 1); rep['limiter_difference_db'] = round(float(d2), 1)

    print('[8] levels per verse bar (altyapi, dBFS RMS); slot bars 6 and 7 must be at least 8 dB below the normal bars')
    A2 = X['altyapi']; E2 = X['ezgi_alti']; tab = []
    for k in range(NV):
        v0 = INTRO + k * VB
        tab.append([db(rms(A2[int((v0 + i) * BAR * sr):int((v0 + i + 1) * BAR * sr)])) for i in range(VB)])
        print(f'       verse {k + 1}: ' + ' '.join(f'{v:6.1f}' for v in tab[-1]))
    tab = np.array(tab); normal = 10 * np.log10((10 ** (tab[:, :6] / 10)).mean(1)); d6 = normal - tab[:, 6]; d7 = normal - tab[:, 7]
    dq = tab[:, :6].min(1) - tab[:, 6:].max(1)
    # bar 7 without its last half beat (the snare pickup)
    t7 = np.array([db(rms(A2[int((INTRO + k * VB + 7) * BAR * sr):int(((INTRO + k * VB + 7) * BAR + 3.4 * BEAT) * sr)])) for k in range(NV)])
    check(d6.min() >= 8 and d7.min() >= 8, f'slot bar 6: {d6.min():.1f}..{d6.max():.1f} dB below the mean of bars 0-5; slot bar 7 (incl. snare pickup): {d7.min():.1f}..{d7.max():.1f} dB; '
          f'bar 7 before the pickup: {(normal - t7).min():.1f}..{(normal - t7).max():.1f} dB; quietest normal bar minus loudest slot bar: {dq.min():.1f} dB')
    rep['slot'] = {'bar6_below_normal_db_min': round(float(d6.min()), 1), 'bar6_max': round(float(d6.max()), 1), 'bar7_below_normal_db_min': round(float(d7.min()), 1),
                   'bar7_max': round(float(d7.max()), 1), 'bar7_before_pickup_min': round(float((normal - t7).min()), 1),
                   'quietest_normal_minus_loudest_slot_db_min': round(float(dq.min()), 1),
                   'normal_bars_dbfs_mean': round(float(normal.mean()), 1), 'slot_bars_dbfs_mean': round(float(tab[:, 6:].mean()), 1)}
    # the tail of bar 5 must not ring into the slot: level in the first 150 ms of bar 6 vs the same span of bar 7
    print('[9] under-vocal stem: default level and audibility proxy')
    act = np.zeros(len(A2), bool); sil = np.ones(len(A2), bool)
    for bi, (ch, kind, k, vb) in enumerate(bars):
        if kind in ('voc', 'voc3', 'voc4'): act[int(bi * BAR * sr):int((bi + 1) * BAR * sr)] = True
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
    rep['ezgi_alti_level'] = {'rms_rel_band_db': round(float(rel), 1), 'f0_band_stem_minus_band_db_median': round(float(np.median(snr)), 1),
                              'f0_band_p10': round(float(np.percentile(snr, 10)), 1), 'f0_band_min': round(float(snr.min()), 1),
                              'octave_band_median': round(float(np.median(snr2)), 1), 'stem_rms_dbfs_active': round(float(db(rms(E2[act]))), 1),
                              'stem_peak_dbfs': round(float(db(np.abs(E2).max())), 1)}
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
        ta = sorted((e[0], e[1], e[3], (e[2] - 0) % 12) for e in ea); tb = sorted((e[0], e[1], e[3], (e[2] - 7) % 12) for e in eb)
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
json.dump(REPORT, open(f'{O}/dogrulama.json', 'w'), ensure_ascii=False, indent=1)
print('\nRESULT:', 'ALL CHECKS PASSED' if not FAIL else f'{len(FAIL)} CHECK(S) FAILED')
for f_ in FAIL: print('  -', f_)
sys.exit(1 if FAIL else 0)
