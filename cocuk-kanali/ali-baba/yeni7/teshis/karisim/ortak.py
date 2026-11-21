#!/usr/bin/env python3
"""Karışım teşhisi için ortak ölçüm işlevleri. Her ölçüm reddedilen karışıma, beğenilen referansa ve onaylı şarkılara AYNI biçimde uygulanır."""
import os, json, numpy as np, soundfile as sf, pyloudnorm
from scipy.signal import butter, sosfiltfilt, sosfilt, welch, resample_poly
D = os.path.dirname(os.path.abspath(__file__)); ARA = os.path.join(D, "ara"); FS = 44100
KOK = os.path.abspath(os.path.join(D, "..", "..", "..", "..")); A = os.path.join(KOK, "ali-baba")
B_RED = 240 / 105.0; ON = 0.100                                   # reddedilen: ölçü süresi, baştaki boşluk
REF_K0, REF_KITA = 8.5713, 13.7139                                # referans: kıta başları 8.5713 + k * 13.7139

def yukle(ad):
    x, fs = sf.read(os.path.join(ARA, ad + ".wav"), always_2d=True); assert fs == FS, (ad, fs)
    if x.shape[1] == 1: x = np.repeat(x, 2, axis=1)
    return x.astype(np.float64)
def esitle(*xs):
    n = min(len(x) for x in xs); return [x[:n] for x in xs]
def dbp(p): return 10 * np.log10(np.maximum(p, 1e-20))
def guc(x): return float(np.mean(np.square(x)))                    # iki kanalın ortalama gücü (çift-mono vokalde = mono güç)
def duzey(x, m=None):
    return float(dbp(guc(x if m is None else x[m])))
def kayan_guc(x, sn):
    """x (n,2) -> pencere içi ortalama güç (n,), ortalanmış pencere"""
    p = np.mean(np.square(x), axis=1) if x.ndim == 2 else np.square(x); w = max(1, int(sn * FS))
    c = np.concatenate([[0.0], np.cumsum(p)]); h = w // 2; i = np.arange(len(p)); a = np.clip(i - h, 0, len(p)); b = np.clip(i - h + w, 0, len(p))
    return (c[b] - c[a]) / w
def sesli_maske(vokal, esik_db=-20.0):
    """04_karisim.py ile aynı tanım: 50 ms zarf > en yüksek zarfın %10'u (-20 dB). Mono toplam üzerinden."""
    env = np.sqrt(kayan_guc(vokal.mean(axis=1), 0.05)); return env > env.max() * 10 ** (esik_db / 20)
_olc = pyloudnorm.Meter(FS)
def kagirlik(x):
    y = x.copy()
    for f in _olc._filters.values(): y = f.apply_filter(y) if hasattr(f, "apply_filter") else y
    return y
def butunlesik(x): return float(_olc.integrated_loudness(x))
def anlik(xk, pencere=0.4, adim=0.1):
    """K-ağırlıklı işaretten anlık (400 ms) ya da kısa süreli (3 s) ses yüksekliği dizisi (LUFS) ve pencere merkez zamanları."""
    p = np.sum(np.square(xk), axis=1); w = int(pencere * FS); h = int(adim * FS); c = np.concatenate([[0.0], np.cumsum(p)])
    bas = np.arange(0, len(p) - w + 1, h); return -0.691 + dbp((c[bas + w] - c[bas]) / w), (bas + w / 2) / FS
def pencere_orani(maske, pencere=0.4, adim=0.1):
    w = int(pencere * FS); h = int(adim * FS); c = np.concatenate([[0], np.cumsum(maske.astype(np.int64))]); bas = np.arange(0, len(maske) - w + 1, h)
    return (c[bas + w] - c[bas]) / w
def lra(xk):
    """EBU Tech 3342: 3 sn pencere, 0.1 sn adım, -70 LUFS mutlak kapı, -20 LU göreli kapı, P95 - P10."""
    st, _ = anlik(xk, 3.0, 0.1); st = st[st > -70]
    if len(st) == 0: return float("nan")
    ort = dbp(np.mean(10 ** (st / 10))); st = st[st > ort - 20]; return float(np.percentile(st, 95) - np.percentile(st, 10))
def gercek_tepe(x): return float(20 * np.log10(np.abs(resample_poly(x, 4, 1, axis=0)).max() + 1e-12))
OKTAV = [31.5, 63, 125, 250, 500, 1000, 2000, 4000, 8000, 16000]
def psd(x, m=None):
    """Welch güç yoğunluğu (iki kanalın ortalaması), maskelenmiş örnekler üzerinden."""
    y = x if m is None else x[m]; f, P = welch(y, FS, nperseg=8192, noverlap=4096, axis=0); return f, P.mean(axis=1)
def oktav_guc(f, P, merkezler=OKTAV):
    df = f[1] - f[0]; return np.array([P[(f >= c / 2 ** 0.5) & (f < c * 2 ** 0.5)].sum() * df for c in merkezler])
def bant_guc(f, P, a, b): return float(P[(f >= a) & (f < b)].sum() * (f[1] - f[0]))
def bant(x, a, b, sifir_faz=True):
    if a is None: sos = butter(4, b, "lowpass", fs=FS, output="sos")
    elif b is None: sos = butter(4, a, "highpass", fs=FS, output="sos")
    else: sos = butter(4, [a, b], "bandpass", fs=FS, output="sos")
    return sosfiltfilt(sos, x, axis=0) if sifir_faz else sosfilt(sos, x, axis=0)
def orta_yan(x, m=None):
    y = x if m is None else x[m]; M = (y[:, 0] + y[:, 1]) / 2; S = (y[:, 0] - y[:, 1]) / 2
    pm, ps = np.mean(M ** 2), np.mean(S ** 2); r = float(np.corrcoef(y[:, 0], y[:, 1])[0, 1]) if np.std(y[:, 0] - y[:, 1]) > 1e-9 else 1.0
    return {"yan_eksi_orta_db": round(float(dbp(ps) - dbp(pm)), 2) if ps > 1e-18 else None, "sol_sag_iliski": round(r, 3),
            "sol_eksi_sag_db": round(float(dbp(np.mean(y[:, 0] ** 2)) - dbp(np.mean(y[:, 1] ** 2))), 2)}
def R(v, n=2): return None if v is None or (isinstance(v, float) and not np.isfinite(v)) else round(float(v), n)
def yaz(ad, veri):
    json.dump(veri, open(os.path.join(ARA, ad + ".json"), "w"), ensure_ascii=False, indent=1)
