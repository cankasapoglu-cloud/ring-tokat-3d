#!/usr/bin/env python3
# Reviewer measurements on the DELIVERED files only (no stems, no builder metadata except zaman_*.json for comparison).
# usage: 01_teslim_olcum.py <yeni4/altyapi folder> <out json>
import sys, json, subprocess, re
import numpy as np, soundfile as sf, pyloudnorm
from scipy.signal import butter, sosfiltfilt, resample_poly, find_peaks

SRC, OUT = sys.argv[1], sys.argv[2]
db = lambda v: 20 * np.log10(np.maximum(v, 1e-12))
rms = lambda x: float(np.sqrt(np.mean(np.square(x)))) if len(x) else 0.0
R = {}
P = lambda *a: print(*a, flush=True)

def band(x, lo, hi, sr, order=4):
    if lo is None: sos = butter(order, hi, 'low', fs=sr, output='sos')
    elif hi is None: sos = butter(order, lo, 'high', fs=sr, output='sos')
    else: sos = butter(order, [lo, hi], 'band', fs=sr, output='sos')
    return sosfiltfilt(sos, x)

def env(x, sr, hop=64, win=256):
    # short RMS envelope (hop 64 samples = 1.45 ms)
    n = (len(x) - win) // hop
    idx = np.arange(n)[:, None] * hop + np.arange(win)[None, :]
    return np.sqrt((x[idx] ** 2).mean(1)), hop / sr, win / 2 / sr

def onsets(e, dt, t0, min_gap=0.10, rel=0.12):
    # onset = steepest rise of the log envelope: peaks of the positive first difference of a smoothed envelope
    k = max(1, int(0.004 / dt)); es = np.convolve(e, np.ones(k) / k, 'same')
    d = np.diff(es, prepend=es[0]); d[d < 0] = 0
    pk, pr = find_peaks(d, height=rel * d.max(), distance=int(min_gap / dt))
    return pk * dt + t0, d[pk]

def blind_period(t, w, lo_bpm=90.0, hi_bpm=120.0, step=0.002, sub=1):
    # no prior tempo: scan the period, score = weighted resultant length of the onset phases (Rayleigh); sub = grid events per beat
    bpms = np.arange(lo_bpm, hi_bpm, step); best = (0, None)
    for i in range(0, len(bpms), 2000):
        T = 60 / bpms[i:i + 2000] / sub
        sc = np.abs((w[None, :] * np.exp(2j * np.pi * t[None, :] / T[:, None])).sum(1))
        j = int(np.argmax(sc))
        if sc[j] > best[0]: best = (float(sc[j]), float(T[j]))
    return best[1]
def grid_fit(t, T0):
    # refine t = a + T k by regression, starting from the blind period T0; keep onsets within 25 ms of the grid
    a, T = t[0], T0
    for it in range(6):
        best = None
        for a0 in (np.linspace(0, T, 80, endpoint=False) if it == 0 else [a]):
            k = np.round((t - a0) / T); r = t - (a0 + k * T)
            s = np.sum(np.abs(r) < 0.025)
            if best is None or s > best[0]: best = (s, a0)
        a0 = best[1]; k = np.round((t - a0) / T); r = t - (a0 + k * T); m = np.abs(r) < 0.025
        A = np.vstack([np.ones(m.sum()), k[m]]).T
        (a, T), *_ = np.linalg.lstsq(A, t[m], rcond=None)
    k = np.round((t - a) / T); r = t - (a + k * T); m = np.abs(r) < 0.025
    return float(a), float(T), int(m.sum()), float(np.std(r[m])), k[m], r[m]

for key in ('G', 'C'):
    P(f'\n=========== key {key} ===========')
    Z = json.load(open(f'{SRC}/zaman_{key}.json'))
    r = R[key] = {}
    X = {}
    for nme in ('altyapi', 'ezgi_alti', 'rehber'):
        p = f'{SRC}/{nme}_{key}.wav'; inf = sf.info(p)
        x, sr = sf.read(p, dtype='float64'); X[nme] = x
        xi, _ = sf.read(p, dtype='int16')
        nclip = int((np.abs(xi.astype(np.int32)) >= 32767).sum())
        peak = float(np.abs(x).max())
        tp4 = float(np.abs(resample_poly(x, 4, 1, axis=0)).max()); tp8 = float(np.abs(resample_poly(x, 8, 1, axis=0)).max())
        L = pyloudnorm.Meter(sr).integrated_loudness(x)
        ff = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', p, '-af', 'ebur128=peak=true', '-f', 'null', '-'], capture_output=True, text=True).stderr
        tail = ff[ff.rfind('Summary:'):]
        fI = float(re.search(r'I:\s+(-?[\d.]+) LUFS', tail).group(1)); fLRA = float(re.search(r'LRA:\s+(-?[\d.]+) LU', tail).group(1))
        fTP = float(re.search(r'Peak:\s+(-?[\d.]+) dBFS', tail).group(1))
        # runs of identical extreme samples (flat tops) as a clipping symptom
        mx = np.abs(xi).max(); flat = int(((np.abs(xi[1:]) == mx) & (np.abs(xi[:-1]) == mx)).sum())
        r[nme] = dict(channels=inf.channels, sr=inf.samplerate, subtype=inf.subtype, frames=inf.frames, dur=inf.frames / inf.samplerate,
                      sample_peak_dbfs=float(db(peak)), n_fullscale=nclip, flat_top_pairs=flat, tp4_dbtp=float(db(tp4)), tp8_dbtp=float(db(tp8)),
                      lufs_pyln=float(L), lufs_ffmpeg=fI, lra_ffmpeg=fLRA, tp_ffmpeg=fTP, dc=float(db(np.abs(x.mean(0)).max())))
        P(f'{nme}_{key}.wav: {inf.channels} ch {inf.samplerate} Hz {inf.subtype} {inf.frames} fr = {inf.frames / inf.samplerate:.4f} s | peak {db(peak):.2f} dBFS, '
          f'TP 4x {db(tp4):.2f} / 8x {db(tp8):.2f} / ffmpeg {fTP:.1f} dBTP | samples at full scale {nclip}, flat-top pairs at max {flat} | '
          f'{L:.2f} LUFS (pyloudnorm), {fI:.1f} LUFS LRA {fLRA:.1f} (ffmpeg)')
    a = X['altyapi']; e_ = X['ezgi_alti']; g_ = X['rehber']; N = len(a)
    dsum = np.abs(g_ - (a + e_)).max() * 32768
    r['rehber_minus_sum_lsb'] = float(dsum); P(f'max |rehber - (altyapi+ezgi_alti)| = {dsum:.2f} LSB')

    # ---------- grid from the json (as declared) and from my own arithmetic --------------------------------
    bpm = Z['tempo_bpm']; BEAT = 60 / bpm; BAR = 4 * BEAT
    jb = []   # (bar index, section kind, verse, bar in verse, start, beat times)
    for o in Z['giris']['olculer']: jb.append(o)
    for kv in Z['kitalar']:
        for o in kv['olculer']: jb.append(o)
    for o in Z['bitis']['olculer']: jb.append(o)
    r['json_bars'] = len(jb)
    errs = [abs(o['baslangic'] - i * BAR) for i, o in enumerate(jb)] + [abs(o['vurus_zamanlari'][b] - (i * BAR + b * BEAT)) for i, o in enumerate(jb) for b in range(4)]
    idx_ok = all(o['olcu'] == i for i, o in enumerate(jb))
    vstarts = [kv['baslangic'] for kv in Z['kitalar']]
    vexp = [(4 + 8 * v) * BAR for v in range(7)]
    r['json_grid_max_err_ms'] = 1000 * max(errs); r['json_bar_index_ok'] = idx_ok
    r['json_verse_starts'] = vstarts; r['json_verse_start_max_err_ms'] = 1000 * max(abs(x - y) for x, y in zip(vstarts, vexp))
    P(f'json: {len(jb)} bars, bpm {bpm}, bar {BAR:.6f} s; bar/beat times vs i*BAR + b*BEAT: max err {1000 * max(errs):.3f} ms; verse starts {vstarts} (max err vs (4+8v)*BAR {r["json_verse_start_max_err_ms"]:.3f} ms)')
    P(f'json: toplam_olcu {Z["toplam_olcu"]}, muzik_bitis {Z["muzik_bitis_sn"]} (64*BAR = {64 * BAR:.4f}), son_vurus {Z["son_vurus_sn"]}, dosya {Z["dosya_suresi_sn"]} s, file {N / sr:.4f} s')
    # per-verse anchors
    anch_err = 0
    for v, kv in enumerate(Z['kitalar']):
        v0 = (4 + 8 * v) * BAR
        exp = {'satir1': v0, 'cevap1': v0 + BAR, 'satir2': v0 + 2 * BAR, 'ses1': v0 + 3 * BAR, 'ses2': v0 + 4 * BAR, 'fill': v0 + 5 * BAR, 'diye': v0 + 5 * BAR + 2 * BEAT,
               'satir4': v0 + 6 * BAR, 'cevap2': v0 + 7 * BAR}
        got = {'satir1': kv['satir1']['baslangic'], 'cevap1': kv['cevap1']['baslangic'], 'satir2': kv['satir2']['baslangic'], 'ses1': kv['hayvan_sesi']['ses1_baslangic'],
               'ses2': kv['hayvan_sesi']['ses2_baslangic'], 'fill': kv['davul_gecisi']['baslangic'], 'diye': kv['diye_bagirir']['baslangic'], 'satir4': kv['satir4']['baslangic'],
               'cevap2': kv['cevap2']['baslangic']}
        anch_err = max(anch_err, max(abs(exp[k] - got[k]) for k in exp))
    r['json_anchor_max_err_ms'] = 1000 * anch_err; P(f'json verse anchors (L1, answer, L2, call1, call2, fill, diye, L4, answer) vs my arithmetic: max err {1000 * anch_err:.3f} ms')
    chords = [' '.join(o['dereceler']) for o in Z['kitalar'][0]['olculer']]
    r['json_verse_chords'] = chords; P('json verse-1 degrees per bar:', chords)
    r['json_chords_all_verses_equal'] = all([' '.join(o['dereceler']) for o in kv['olculer']] == chords for kv in Z['kitalar'])
    P('json intro degrees:', [' '.join(o['dereceler']) for o in Z['giris']['olculer']], '| ending:', [' '.join(o['dereceler']) for o in Z['bitis']['olculer']])

    # ---------- blind beat grid from the delivered mix -----------------------------------------------------
    mono = a.mean(1)
    res = {}
    for nm_, lo, hi in (('low 35-110 Hz (kick/bass)', 35, 110), ('high 6-14 kHz (hat/snare/tamb.)', 6000, 14000), ('snare body 160-260 Hz', 160, 260)):
        xb = band(mono, lo, hi, sr); e, dt, t0 = env(xb, sr)
        t, s = onsets(e, dt, t0, min_gap=0.12, rel=0.15)
        sub = 2 if hi == 14000 else 1
        Tb = blind_period(t, s, sub=sub)
        a0, T, n, sd, k, rr = grid_fit(t, Tb)
        T2 = T * sub; res_blind = 60 / (Tb * sub)
        res[nm_] = dict(blind_scan_bpm=res_blind, n_onsets=len(t), n_on_grid=n, period_s=T2, bpm=60 / T2, phase_s=a0 % T2 if a0 % T2 < T2 / 2 else a0 % T2 - T2, resid_sd_ms=1000 * sd,
                        drift_first_last_ms=1000 * float((T2 - BEAT) * (N / sr / BEAT)))
        P(f'blind grid, {nm_}: period scan 90-120 BPM without prior -> {res_blind:.3f} BPM; {len(t)} onsets, {n} within 25 ms of the refined grid; period {T2:.6f} s = {60 / T2:.4f} BPM (json {bpm}); phase of grid vs t=0: {1000 * res[nm_]["phase_s"]:+.2f} ms; '
          f'resid sd {1000 * sd:.2f} ms; accumulated difference vs nominal over the file {res[nm_]["drift_first_last_ms"]:+.2f} ms')
    r['blind_grid'] = res

    # ---------- every json beat: is there a low-band (kick) onset? ------------------------------------------
    xb = band(mono, 35, 110, sr); e, dt, t0 = env(xb, sr); tk, sk = onsets(e, dt, t0, min_gap=0.10, rel=0.04)
    miss = []; offs = []
    for i, o in enumerate(jb):
        for b, tb in enumerate(o['vurus_zamanlari']):
            j = np.argmin(np.abs(tk - tb)); d = tk[j] - tb
            if abs(d) <= 0.030: offs.append(d)
            else: miss.append((i, b, round(tb, 3)))
    offs = np.array(offs)
    r['kick_on_json_beats'] = dict(found=len(offs), of=len(jb) * 4, missing=miss, median_ms=float(1000 * np.median(offs)), min_ms=float(1000 * offs.min()), max_ms=float(1000 * offs.max()),
                                   first16_ms=float(1000 * offs[:16].mean()), last16_ms=float(1000 * offs[-16:].mean()))
    P(f'COARSE ONLY (mix low band = kick + bass through a 35-110 Hz filter, whose own rise time is ~20 ms; the stem-based kick timing is in 02_stem_olcum.py): low-band onset at json beats (+-30 ms): {len(offs)}/{len(jb) * 4}; onset(max slope) minus json: median {1000 * np.median(offs):+.2f} ms, min {1000 * offs.min():+.2f}, max {1000 * offs.max():+.2f}; '
      f'first 16 beats {1000 * offs[:16].mean():+.2f}, last 16 {1000 * offs[-16:].mean():+.2f}; missing (bar, beat, t): {miss}')

    # ---------- backbeat: snare body (160-260 Hz) + noise (2-5 kHz) energy per beat, by bar kind -------------
    xs = band(mono, 2000, 5000, sr)
    per = {}
    for i, o in enumerate(jb):
        v = [db(rms(xs[int(tb * sr):int((tb + 0.12) * sr)])) for tb in o['vurus_zamanlari']]
        per.setdefault(o['tur'], []).append(v)
    r['snare_band_per_beat_db'] = {k: [round(float(x), 1) for x in np.mean(v, 0)] for k, v in per.items()}
    P('2-5 kHz level in the first 120 ms of beats 0..3, mean per bar kind (snare+clap expected on beats 1 and 3 of full bars, not in slot bars):')
    for k, v in r['snare_band_per_beat_db'].items(): P(f'    {k:14s} {v}')

    # ---------- levels per bar ------------------------------------------------------------------------------
    m = pyloudnorm.Meter(sr, block_size=0.4)
    def lv(x, t0, t1):
        s = x[int(round(t0 * sr)):int(round(t1 * sr))]
        return float(db(rms(s))), float(m.integrated_loudness(s)) if len(s) > 0.45 * sr else None
    tab = {nme: [] for nme in ('altyapi', 'rehber')}
    for nme in tab:
        for kv in Z['kitalar']:
            tab[nme].append([lv(X[nme], o['baslangic'], o['bitis']) for o in kv['olculer']])
    for nme in tab:
        T_ = np.array([[c[0] for c in row] for row in tab[nme]]); Lk = np.array([[c[1] for c in row] for row in tab[nme]])
        P(f'{nme}: RMS dBFS per verse bar (rows = verses):'); [P('    ' + '  '.join(f'{v:6.1f}' for v in row)) for row in T_]
        P(f'{nme}: K-weighted loudness (LUFS, 400 ms blocks) per verse bar:'); [P('    ' + '  '.join(f'{v:6.1f}' for v in row)) for row in Lk]
        normal = [0, 1, 2, 5, 6, 7]
        d_rms = T_[:, normal].min(1) - T_[:, [3, 4]].max(1); d_lk = Lk[:, normal].min(1) - Lk[:, [3, 4]].max(1)
        d_mean = T_[:, normal].mean(1)[:, None] - T_[:, [3, 4]]
        r[f'{nme}_bar_rms'] = T_.round(2).tolist(); r[f'{nme}_bar_lufs'] = Lk.round(2).tolist()
        r[f'{nme}_slot_margin'] = dict(quietest_normal_minus_loudest_slot_rms_db=[float(d_rms.min()), float(d_rms.max())],
                                       quietest_normal_minus_loudest_slot_lufs=[float(d_lk.min()), float(d_lk.max())], mean_normal_minus_slot_rms_db=[float(d_mean.min()), float(d_mean.max())])
        P(f'{nme}: quietest normal bar minus loudest slot bar, per verse: RMS {d_rms.min():.1f}..{d_rms.max():.1f} dB; K-weighted {d_lk.min():.1f}..{d_lk.max():.1f} LU; mean of normal bars minus slot bars {d_mean.min():.1f}..{d_mean.max():.1f} dB')
    # bar 5 halves, slot bar sub-windows (first 250 ms = ring-over from bar 2)
    h = []
    for kv in Z['kitalar']:
        o = kv['olculer']; b5 = o[5]['vurus_zamanlari']; b0 = o[0]['vurus_zamanlari']
        h.append([lv(a, b5[0], b5[2])[0], lv(a, b5[2], o[5]['bitis'])[0], lv(a, b0[2], o[0]['bitis'])[0],
                  lv(a, o[3]['baslangic'], o[3]['baslangic'] + .25)[0], lv(a, o[3]['baslangic'] + .25, o[3]['bitis'])[0],
                  lv(a, o[4]['baslangic'], o[4]['baslangic'] + .25)[0], lv(a, o[4]['baslangic'] + .25, o[4]['bitis'])[0],
                  lv(e_, o[3]['baslangic'], o[3]['baslangic'] + .25)[0], lv(e_, o[3]['baslangic'] + .25, o[3]['bitis'])[0], lv(e_, o[2]['baslangic'], o[2]['bitis'])[0],
                  lv(e_, o[1]['baslangic'], o[1]['bitis'])[0], lv(e_, o[4]['baslangic'], o[4]['bitis'])[0], lv(e_, b5[0], b5[2])[0], lv(e_, b5[2], o[5]['bitis'])[0],
                  lv(e_, o[7]['baslangic'], o[7]['bitis'])[0], lv(e_, o[0]['baslangic'], o[0]['bitis'])[0], lv(e_, o[6]['baslangic'], o[6]['bitis'])[0]])
    h = np.array(h); cols = ['alt b5 beats0-1', 'alt b5 beats2-3', 'alt b0 beats2-3', 'alt b3 first250ms', 'alt b3 rest', 'alt b4 first250ms', 'alt b4 rest',
                             'ezgi b3 first250ms', 'ezgi b3 rest', 'ezgi b2', 'ezgi b1', 'ezgi b4', 'ezgi b5 beats0-1', 'ezgi b5 beats2-3', 'ezgi b7', 'ezgi b0', 'ezgi b6']
    r['sub_windows_db'] = {c: [float(h[:, i].min()), float(h[:, i].mean()), float(h[:, i].max())] for i, c in enumerate(cols)}
    P('sub-window RMS dBFS over the 7 verses (min / mean / max):')
    for c in cols: P(f'    {c:22s} {r["sub_windows_db"][c][0]:7.1f} {r["sub_windows_db"][c][1]:7.1f} {r["sub_windows_db"][c][2]:7.1f}')
    # under-vocal stem outside the verses: intro and ending must be silent
    i_end = Z['giris']['bitis']; e_beg = Z['bitis']['baslangic']
    last_voc_end = Z['kitalar'][-1]['olculer'][6]['bitis']
    r['ezgi_intro_db'] = lv(e_, 0, i_end)[0]; r['ezgi_ending_db'] = lv(e_, e_beg, N / sr)[0]; r['ezgi_peak_intro'] = float(db(np.abs(e_[:int(i_end * sr)]).max()))
    P(f'ezgi_alti in the intro (0..{i_end}): RMS {r["ezgi_intro_db"]:.1f} dBFS, peak {r["ezgi_peak_intro"]:.1f}; in the ending ({e_beg}..end): RMS {r["ezgi_ending_db"]:.1f} dBFS')

    # ---------- tail ----------------------------------------------------------------------------------------
    fh = Z['son_vurus_sn']
    e, dt, t0 = env(band(mono, 2000, 12000, sr), sr, hop=32, win=256)          # final hit = loudest 6 ms window (2-12 kHz) in the last 4 s of the file
    tt = np.arange(len(e)) * dt + t0; e2 = np.where(tt > N / sr - 4.0, e, 0); i_pk = int(np.argmax(e2))
    thr = e[max(0, i_pk - int(.05 / dt)):i_pk + 1]; j = int(np.argmax(thr >= .25 * e[i_pk])); t_hit = float(tt[max(0, i_pk - int(.05 / dt)) + j])   # 25 % rise point before that peak
    lvl = lambda t0_, t1_: float(db(rms(mono[int(t0_ * sr):int(t1_ * sr)])))
    r['tail'] = dict(final_hit_json=fh, final_hit_detected=t_hit, tail_after_hit_s=N / sr - t_hit, music_end_64bars=64 * BAR, tail_after_bar64_s=N / sr - 64 * BAR,
                     level_1p0_1p5_after_hit=lvl(fh + 1.0, fh + 1.5), level_before_fade=lvl(N / sr - 0.6, N / sr - 0.4), level_last_400ms=lvl(N / sr - 0.4, N / sr), level_last_20ms=lvl(N / sr - 0.02, N / sr),
                     peak_last_20ms=float(db(np.abs(a[-int(.02 * sr):]).max())), first_10ms_peak=float(db(np.abs(a[:441]).max())), first_1ms_peak=float(db(np.abs(a[:44]).max())))
    P(f'tail: final hit json {fh:.4f}, loudest hit of the last 4 s detected (25 % rise point, 2-12 kHz) at {t_hit:.4f} s; file end - hit = {N / sr - t_hit:.3f} s; end of bar 64 = {64 * BAR:.4f} s, file end - bar-64 end = {N / sr - 64 * BAR:.3f} s')
    P(f'      level 1.0-1.5 s after the hit {r["tail"]["level_1p0_1p5_after_hit"]:.1f} dBFS; 0.6-0.4 s before the end (just before the 0.4 s fade) {r["tail"]["level_before_fade"]:.1f}; last 400 ms {r["tail"]["level_last_400ms"]:.1f}; last 20 ms {r["tail"]["level_last_20ms"]:.1f} (peak {r["tail"]["peak_last_20ms"]:.1f})')
    P(f'      file start: peak in the first 1 ms {r["tail"]["first_1ms_peak"]:.1f} dBFS, first 10 ms {r["tail"]["first_10ms_peak"]:.1f} dBFS (music starts at sample 0, no lead-in silence)')
    X_ = None
    R[key]['_env10'] = None
    np.save(f'{OUT}.{key}.env.npy', np.array([rms(mono[i:i + 441]) for i in range(0, N - 441, 441)]))

# ---------- G vs C: envelopes ---------------------------------------------------------------------------
eg = np.load(f'{OUT}.G.env.npy'); ec = np.load(f'{OUT}.C.env.npy')
n = min(len(eg), len(ec)); eg, ec = eg[:n], ec[:n]
cc = float(np.corrcoef(db(eg[:-300]), db(ec[:-300]))[0, 1])
dd = db(eg) - db(ec); act = (eg > 10 ** (-45 / 20))
R['G_vs_C'] = dict(len_equal=bool(R['G']['altyapi']['frames'] == R['C']['altyapi']['frames']), env10ms_log_corr=cc, env_diff_db_mean=float(dd[act].mean()), env_diff_db_sd=float(dd[act].std()),
                   env_diff_db_p1=float(np.percentile(dd[act], 1)), env_diff_db_p99=float(np.percentile(dd[act], 99)))
P(f'\nG vs C (altyapi, 10 ms RMS envelopes): log-envelope correlation {cc:.4f}; G minus C: mean {dd[act].mean():+.2f} dB, sd {dd[act].std():.2f}, 1..99 pct {np.percentile(dd[act], 1):+.1f}..{np.percentile(dd[act], 99):+.1f} dB')
# high band onset envelope lag (drums are not transposed -> must align at lag 0)
for key in ('G', 'C'): pass
xg, sr = sf.read(f'{SRC}/altyapi_G.wav'); xc, _ = sf.read(f'{SRC}/altyapi_C.wav')
hg = band(xg.mean(1), 7000, 14000, sr); hc = band(xc.mean(1), 7000, 14000, sr)
eg2, dt, _ = env(hg, sr, hop=16, win=64); ec2, _, _ = env(hc, sr, hop=16, win=64)
L = 400; c = [float(np.dot(eg2[L:-L], ec2[L + l:len(ec2) - L + l])) for l in range(-L // 4, L // 4 + 1)]
lag = (int(np.argmax(c)) - L // 4) * dt
R['G_vs_C']['hi_band_env_lag_ms'] = 1000 * lag; R['G_vs_C']['hi_band_env_corr'] = float(np.corrcoef(eg2, ec2)[0, 1])
P(f'G vs C, 7-14 kHz envelope (drums, not transposed): best lag {1000 * lag:+.2f} ms, correlation {R["G_vs_C"]["hi_band_env_corr"]:.4f}')
# per-bar level difference
bpm = json.load(open(f'{SRC}/zaman_G.json'))['tempo_bpm']; BAR = 240 / bpm
pb = [float(db(rms(xg[int(i * BAR * sr):int((i + 1) * BAR * sr)])) - db(rms(xc[int(i * BAR * sr):int((i + 1) * BAR * sr)]))) for i in range(64)]
R['G_vs_C']['per_bar_G_minus_C_db'] = [round(v, 2) for v in pb]
P('G minus C, RMS per bar (64 bars):', ' '.join(f'{v:+.1f}' for v in pb))
# json G vs C: all numbers identical except pitch fields
zg = json.load(open(f'{SRC}/zaman_G.json')); zc = json.load(open(f'{SRC}/zaman_C.json'))
ng, nc = zg['ezgi_notalari'], zc['ezgi_notalari']
same_t = len(ng) == len(nc) and all(all(x[k] == y[k] for k in ('parti', 'enstruman', 'olcu', 'vurus', 'baslangic', 'sure', 'hiz')) for x, y in zip(sorted(ng, key=lambda m: (m['olcu'], m['vurus'], m['enstruman'], m['parti'], m['midi'] % 1000)), sorted(nc, key=lambda m: (m['olcu'], m['vurus'], m['enstruman'], m['parti'], m['midi'] % 1000))))
iv = {}
for x in ng: iv.setdefault((x['parti'], x['enstruman'], x['olcu'], x['vurus']), []).append(x['midi'])
ivc = {}
for x in nc: ivc.setdefault((x['parti'], x['enstruman'], x['olcu'], x['vurus']), []).append(x['midi'])
shift = {}
for k_ in iv:
    s = tuple(sorted(set(np.array(sorted(ivc[k_])) - np.array(sorted(iv[k_])))))
    shift.setdefault((k_[0], k_[1], s), 0); shift[(k_[0], k_[1], s)] += 1
R['G_vs_C']['json_notes_same_rhythm'] = bool(same_t); R['G_vs_C']['json_note_shift_C_minus_G'] = {f'{k[0]}/{k[1]}/{k[2]}': v for k, v in shift.items()}
P('json notes: same count/rhythm/velocity in G and C:', same_t, '| C minus G in semitones per part/instrument (count of note slots):', R['G_vs_C']['json_note_shift_C_minus_G'])
for key in ('G', 'C'): R[key].pop('_env10', None)
json.dump(R, open(OUT, 'w'), indent=1, ensure_ascii=False)
import os
for key in ('G', 'C'): os.remove(f'{OUT}.{key}.env.npy')
