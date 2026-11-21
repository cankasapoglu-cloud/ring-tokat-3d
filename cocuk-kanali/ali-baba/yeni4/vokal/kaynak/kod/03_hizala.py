# Lag and clock difference of a separated stem against v2_2.mp3 decoded by ffmpeg (44.1 kHz).
#   usage: python3 03_hizala.py <name> <vocals.wav> [<instrumental.wav>]   -> gecici/hizala_<name>.json
# Convention everywhere: lag > 0  <=>  the stem is LATE against the mix (stem(t) = mix(t - lag)).
# Methods
#  S  "sum check": vocals + instrumental against the stereo mix, generalised cross-correlation with 32x
#     interpolation in 5 s windows over the whole song (works when the separator's two stems add up to its input).
#  W  band-limited waveform cross-correlation mix <-> vocal stem per sung segment (250-3000 Hz, +-30 ms),
#     as yeni3/analiz/tempo/kod/09_align_fine.py (1), with 32x interpolation.
#  E  envelope cross-correlation per segment (1-4 kHz RMS envelope, 8-sample hop), as 09_align_fine.py (2).
#  D  stem-weighted correlation of log-magnitude time derivatives per segment, as 12_align_spectro.py.
# Clock difference = slope of lag against time, in ppm (1 ppm = 1e-3 ms per 1000 s = 1e-6 s/s).
import sys, json, numpy as np, scipy.signal as ss
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from common import *

name, pv = sys.argv[1], sys.argv[2]
pi = sys.argv[3] if len(sys.argv) > 3 and sys.argv[3] not in ('', 'None') else None
xs = load_mix(True); x = xs.mean(1)
vs = load_stem(pv, mono=False)
if vs.ndim == 1: vs = np.stack([vs, vs], 1)
n = min(len(x), len(vs)); v = vs[:n].mean(1)
res = dict(name=name, vocals=pv, instrumental=pi, n_samples_stem=int(len(vs)), n_samples_mix=int(len(x)),
           convention='lag > 0: stem late against the mix')
UP = 32


def gcc_lag(a, b, maxlag, up=UP, lo=None, hi=None):
    """delay of b against a (b(t) = a(t - lag)) in samples, sub-sample by zero-padded FFT interpolation;
    returns lag, normalised correlation at the peak"""
    N = len(a); M = 1 << int(np.ceil(np.log2(2 * N)))
    Fa = np.fft.rfft(a, M); Fb = np.fft.rfft(b, M)
    C = Fb * np.conj(Fa)
    if lo is not None or hi is not None:
        f = np.fft.rfftfreq(M, 1 / SR); band = np.ones(len(f), bool)
        if lo is not None: band &= f >= lo
        if hi is not None: band &= f <= hi
        C = C * band
        ea = (np.abs(Fa[band]) ** 2).sum(); eb = (np.abs(Fb[band]) ** 2).sum()
    else:
        ea = (np.abs(Fa) ** 2).sum(); eb = (np.abs(Fb) ** 2).sum()
    Cp = np.zeros(M * up // 2 + 1, complex); Cp[:len(C)] = C
    c = np.fft.irfft(Cp, M * up) * up
    L = maxlag * up
    cc = np.concatenate([c[-L:], c[:L + 1]])
    k = int(np.argmax(cc))
    norm = np.sqrt(ea * eb) * 2 / M          # rfft energy -> time-domain energy (Parseval, one-sided)
    return (k - L) / up, float(cc[k] / norm)


# ---------- S: sum check ----------
if pi:
    ins = load_stem(pi, mono=False)
    if ins.ndim == 1: ins = np.stack([ins, ins], 1)
    # The separator writes  instrumental = g*mix - c*vocals  (g = its input normalisation, c = the model's "compensate"
    # factor: 1.021 for UVR-MDX-NET-Voc_FT, 1 for the Roformer).  Both are estimated by least squares, so that
    # c*vocals + instrumental can be compared with the mix sample by sample.
    X = np.stack([xs[:n].ravel(), vs[:n].ravel()], 1)
    (g, mc), *_ = np.linalg.lstsq(X, ins[:n].ravel(), rcond=None)
    g = float(g); comp = float(-mc)
    s = (comp * vs[:n] + ins[:n])
    r0 = s - g * xs[:n]
    s1 = vs[:n] + ins[:n]; g1 = float((s1 * xs[:n]).sum() / (xs[:n] ** 2).sum())
    res['sum_check'] = dict(gain_mix_g=g, gain_mix_db=float(20 * np.log10(abs(g))), compensate_c=comp,
                            stem_scale_g_over_c=g / comp, stem_scale_db=float(20 * np.log10(g / comp)),
                            gain_stems_over_mix=g / comp,          # scale of the vocal file relative to a vocal on the mix scale
                            residual_db_re_mix_at_lag0=float(rms_db(r0) - rms_db(g * xs[:n])),
                            plain_sum_gain=g1, plain_sum_residual_db_re_mix=float(rms_db(s1 - g1 * xs[:n]) - rms_db(g1 * xs[:n])),
                            corr_at_lag0=float((s * xs[:n]).sum() / np.sqrt((s ** 2).sum() * (xs[:n] ** 2).sum())),
                            mix_peak=float(np.abs(xs).max()), expected_g_0p9_over_peak=float(0.9 / np.abs(xs).max()) if np.abs(xs).max() > 0.9 else 1.0)
    win = int(5.0 * SR); rows = []
    sm = s.mean(1)
    for a in range(0, n - win + 1, win):
        lag, c = gcc_lag(x[a:a + win], sm[a:a + win], 64)
        rows.append(dict(t=(a + win / 2) / SR, lag_samples=lag, lag_ms=lag / SR * 1000, corr=c))
    tt = np.array([r['t'] for r in rows]); ll = np.array([r['lag_ms'] for r in rows])
    b, a0 = np.polyfit(tt, ll, 1)
    res['sum_check'].update(windows=rows, median_lag_ms=float(np.median(ll)), median_lag_samples=float(np.median(ll) * SR / 1000),
                            min_corr=float(min(r['corr'] for r in rows)),
                            trend_ms_per_s=float(b), clock_ppm=float(b * 1000), intercept_ms=float(a0),
                            lag_at_0s_ms=float(a0), lag_at_105s_ms=float(a0 + b * 105))
    print(f"[{name}] S sum check: mix gain g {g:.5f} ({20*np.log10(abs(g)):+.3f} dB), compensate c {comp:.4f}, stem scale g/c {g/comp:.5f}, residual {res['sum_check']['residual_db_re_mix_at_lag0']:.1f} dB re mix, "
          f"median lag {np.median(ll)*SR/1000:+.3f} samples ({np.median(ll):+.4f} ms), clock {b*1000:+.2f} ppm, min corr {res['sum_check']['min_corr']:.4f}")

# ---------- per sung segment ----------
segs = TEMPO['segments']
xb = bandpass(x[:n], 250, 3000, 4); vb = bandpass(v, 250, 3000, 4)
sos2 = ss.butter(4, [1000, 4000], btype='band', fs=SR, output='sos')


def envf(y):
    z = ss.sosfiltfilt(sos2, y) ** 2
    nw = int(0.004 * SR); e = np.sqrt(np.convolve(z, np.ones(nw) / nw, mode='same'))
    return e[::8]


ex = envf(x[:n]); ev = envf(v); hop = 8
NF = 1024; HP = 16


def lspec(y, a, b):
    f, t, S = ss.stft(y[a:b], SR, window='hann', nperseg=NF, noverlap=NF - HP, boundary=None, padded=False)
    return f, np.abs(S)


rows = []
for L in segs:
    t0, t1 = L['onset'], L['end']
    a = int(t0 * SR); b = int(t1 * SR)
    # W
    lagW, cW = gcc_lag(xb[a:b], vb[a:b], int(0.03 * SR))
    # E
    ae = int(t0 * SR / hop) - int(0.1 * SR / hop); be = int(t1 * SR / hop) + int(0.1 * SR / hop)
    X = np.log(ex[ae:be] + 1e-4); V = np.log(ev[ae:be] + 1e-4); X = X - X.mean(); V = V - V.mean()
    c = ss.correlate(V, X, mode='full', method='fft'); lags = ss.correlation_lags(len(V), len(X))
    sel = np.abs(lags) <= int(0.03 * SR / hop); cs = c[sel] / np.sqrt((X ** 2).sum() * (V ** 2).sum()); ls = lags[sel]
    k = int(np.argmax(cs)); d = 0.0
    if 0 < k < len(cs) - 1:
        y0, y1, y2 = cs[k - 1], cs[k], cs[k + 1]; d = 0.5 * (y0 - y2) / (y0 - 2 * y1 + y2)
    lagE = (ls[k] + d) * hop / SR * 1000; cE = float(cs[k])
    # D
    a2 = int((t0 - 0.1) * SR); b2 = int((t1 + 0.1) * SR)
    f, Sm = lspec(x, a2, b2); f, Sv = lspec(v, a2, b2)
    band = (f >= 200) & (f <= 4000)
    Lm = np.log(Sm[band] + 1e-3 * Sm.max()); Lv = np.log(Sv[band] + 1e-3 * Sv.max())
    dd = 8
    Dm = Lm[:, dd:] - Lm[:, :-dd]; Dv = Lv[:, dd:] - Lv[:, :-dd]
    W = (Sv[band][:, dd:] > 0.1 * Sv[band].max()); Dv = Dv * W
    maxlag = int(0.02 * SR / HP); cs2 = []
    for lag in range(-maxlag, maxlag + 1):       # lag>0: stem late  -> Dv(t) ~ Dm(t-lag)
        if lag >= 0: p = (Dv[:, lag:] * Dm[:, :Dm.shape[1] - lag]).sum()
        else: p = (Dv[:, :lag] * Dm[:, -lag:]).sum()
        cs2.append(p)
    cs2 = np.array(cs2); k2 = int(np.argmax(cs2)); d2 = 0.0
    if 0 < k2 < len(cs2) - 1:
        y0, y1, y2 = cs2[k2 - 1], cs2[k2], cs2[k2 + 1]; d2 = 0.5 * (y0 - y2) / (y0 - 2 * y1 + y2)
    lagD = (k2 - maxlag + d2) * HP / SR * 1000
    rows.append(dict(verse=L['verse'], name=L['name'], t=float(t0), wave_lag_samples=float(lagW), wave_lag_ms=float(lagW / SR * 1000),
                     wave_corr=float(cW), env_lag_ms=float(lagE), env_corr=cE, dspec_lag_ms=float(lagD),
                     dspec_peak_over_mean=float(cs2[k2] / (np.abs(cs2).mean() + 1e-9))))
tm = np.array([r['t'] for r in rows])
out = {}
for key in ('wave_lag_ms', 'env_lag_ms', 'dspec_lag_ms'):
    y = np.array([r[key] for r in rows]); b, a0 = np.polyfit(tm, y, 1); rsd = (y - (a0 + b * tm)).std()
    out[key] = dict(median_ms=float(np.median(y)), mean_ms=float(y.mean()), sd_ms=float(y.std()), min_ms=float(y.min()), max_ms=float(y.max()),
                    trend_ms_per_s=float(b), clock_ppm=float(b * 1000), intercept_ms=float(a0), residual_sd_ms=float(rsd),
                    trend_se_ppm=float(1000 * rsd / (tm.std() * np.sqrt(len(tm)))))
    print(f"[{name}] {key:13s}: median {np.median(y):+.4f} ms  sd {y.std():.4f}  range {y.min():+.3f}..{y.max():+.3f}  clock {b*1000:+.2f} ppm (se {out[key]['trend_se_ppm']:.2f})")
wc = np.array([r['wave_corr'] for r in rows])
print(f"[{name}] waveform corr mix<->stem per segment: median {np.median(wc):.3f}, min {wc.min():.3f}")
res['per_segment'] = rows; res['per_segment_summary'] = out
res['per_segment_summary']['wave_corr_median'] = float(np.median(wc)); res['per_segment_summary']['wave_corr_min'] = float(wc.min())
json.dump(res, open(f'{CACHE}/hizala_{name}.json', 'w'), indent=1)
