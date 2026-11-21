#!/usr/bin/env python3
"""ezgi_ortak: 'ezgi' vokali icin ortak yardimcilar.

- vokal_dogal.wav + yerlesim.json okuma, parca (chunk) listesi
- f0 / seslilik cozumlemesi (harvest + stonemask, 1 ms kare; alcak geciren bantta
  donemsellik olcusu ile seslilik karari)
- hedef notalar ve hece basina kaydirma (yarim ses)
Hicbir sey yazmaz (yalniz ezgi_ara/ altina onbellek)."""
import os, json, numpy as np, soundfile as sf, pyworld as pw
from scipy.signal import butter, sosfiltfilt

V = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))      # .../yeni3/vokal
ARA = os.path.join(V, "ezgi_ara")
DOGAL = os.path.join(V, "vokal_dogal.wav")
YER = os.path.join(V, "yerlesim.json")
SR = 44100
PAD = int(0.10 * SR)          # parca basina/sonuna eklenen sessizlik (cozumleme kenar etkisi icin)
FP = 1.0                      # f0 kare araligi (ms)
KOPYA_ESIK = 0.30             # |kaydirma| <= bu ise (yarim ses) ozgun ornekler kopyalanir


def oku():
    x, sr = sf.read(DOGAL, dtype="float64")
    assert sr == SR and x.ndim == 1
    with open(YER, encoding="utf8") as f:
        Y = json.load(f)
    return x, Y


def parcalar(Y):
    out = []
    for c in Y["chunks"]:
        ls = sorted([L for L in Y["lines"] if L["chunk"] == c["id"]], key=lambda L: L["line"])
        assert ls, c["id"]
        out.append(dict(id=c["id"], verse=c["verse"], a=int(c["dest_in_sample"]), b=int(c["dest_out_sample"]), lines=ls))
    return out


def midi(f):
    f = np.asarray(f, dtype=float)
    return np.where(f > 0, 69.0 + 12.0 * np.log2(np.maximum(f, 1e-6) / 440.0), np.nan)


def hz(m):
    return 440.0 * 2.0 ** ((np.asarray(m, dtype=float) - 69.0) / 12.0)


_SOS_LP = butter(4, 1200.0, "low", fs=SR, output="sos")


def f0_analiz(seg, fp=FP, f0_floor=150.0, f0_ceil=700.0):
    """Donus: t (s), f0 (Hz; sessiz/otumsuz = 0), ham f0, ncc (donemsellik 0..1), duzey (dBFS, 10 ms RMS).
    Seslilik: guclu (ncc>=0.80, duzey>=-45) cekirdeklerden zayif (ncc>=0.55, duzey>=-52) karelere
    dogru buyutulur; <=12 ms bosluklar kopruleme ile doldurulur; <20 ms adalar atilir."""
    f0h, t = pw.harvest(seg, SR, f0_floor=f0_floor, f0_ceil=f0_ceil, frame_period=fp)
    f0r = pw.stonemask(seg, f0h, t, SR)
    xl = sosfiltfilt(_SOS_LP, seg)
    n = len(t)
    ncc = np.zeros(n); lev = np.full(n, -200.0)
    h = int(0.005 * SR)
    c2 = np.concatenate([[0.0], np.cumsum(seg ** 2)])
    for i in range(n):
        k = int(round(t[i] * SR))
        a, b = max(0, k - h), min(len(seg), k + h)
        if b > a:
            lev[i] = 10 * np.log10((c2[b] - c2[a]) / (b - a) + 1e-20)
        if f0r[i] <= 0:
            continue
        P = int(round(SR / f0r[i])); best = 0.0
        for PP in (P - 1, P, P + 1):
            u0 = k - PP
            if u0 < 0 or k + 2 * PP > len(xl):
                continue
            u = xl[u0:k + PP]; v = xl[u0 + PP:k + 2 * PP]
            d = np.sqrt(np.dot(u, u) * np.dot(v, v))
            if d > 1e-14:
                best = max(best, float(np.dot(u, v) / d))
        ncc[i] = best
    strong = (f0r > 0) & (ncc >= 0.80) & (lev >= -45.0)
    weak = (f0r > 0) & (ncc >= 0.55) & (lev >= -52.0)
    voiced = strong.copy()
    # ileri / geri buyutme
    for rng in (range(1, n), range(n - 2, -1, -1)):
        for i in rng:
            j = i - 1 if rng.step == 1 else i + 1
            if weak[i] and voiced[j] and not voiced[i]:
                voiced[i] = True
    # kisa bosluklari kopruleme
    f0 = np.where(voiced, f0r, 0.0)
    i = 0; gap_max = int(round(12.0 / fp))
    while i < n:
        if not voiced[i]:
            j = i
            while j < n and not voiced[j]:
                j += 1
            if 0 < i and j < n and (j - i) <= gap_max and lev[i:j].min() > -42.0:
                lf = np.interp(np.arange(i, j), [i - 1, j], [np.log(f0[i - 1]), np.log(f0[j])])
                f0[i:j] = np.exp(lf); voiced[i:j] = True
            i = j
        else:
            i += 1
    # kisa adalari at
    i = 0; isl_min = int(round(20.0 / fp))
    while i < n:
        if voiced[i]:
            j = i
            while j < n and voiced[j]:
                j += 1
            if j - i < isl_min:
                voiced[i:j] = False; f0[i:j] = 0.0
            i = j
        else:
            i += 1
    return t, f0, f0r, ncc, lev


def parca_cozumle(x, c, yeniden=False):
    """Parcanin (PAD ile) f0 cozumlemesi; ezgi_ara/ altinda onbelleklenir."""
    os.makedirs(ARA, exist_ok=True)
    p = os.path.join(ARA, "f0_%s.npz" % c["id"].replace("+", "_"))
    seg = np.concatenate([np.zeros(PAD), x[c["a"]:c["b"]], np.zeros(PAD)])
    if os.path.exists(p) and not yeniden:
        d = np.load(p)
        if int(d["n"]) == len(seg):
            return seg, d["t"], d["f0"], d["f0r"], d["ncc"], d["lev"]
    t, f0, f0r, ncc, lev = f0_analiz(seg)
    np.savez(p, t=t, f0=f0, f0r=f0r, ncc=ncc, lev=lev, n=len(seg))
    return seg, t, f0, f0r, ncc, lev


def seg_zaman(c):
    """Parca-ici zaman (s) = dosya zamani - bu deger."""
    return c["a"] / SR - PAD / SR


# ---------------------------------------------------------------- hedefler
def hedef_listesi(L):
    """Dize icin hece basina (hedef_midi veya None, tekduze_kaydirma veya None)."""
    n = len(L["syllables"])
    if L["line"] == 1:
        assert n == 10, (L["verse"], n)
        tg = [67] * 5 + [62] + [64] * 3 + [62]
        return [(m, None) for m in tg]
    if L["line"] == 2:
        assert n >= 7 and L["syllables"][-1]["text"] == "var", (L["verse"], n)
        tg = [67] * 4 + [62] + [64] * (n - 6) + [62]
        return [(m, None) for m in tg]
    if L["line"] == 3:
        return [(None, 3.0)] * n
    if L["line"] == 4:
        return [(None, 7.0)] * n
    raise ValueError(L["line"])


def yukselen_kos(u):
    """0..1 yukseltilmis kosinus."""
    u = np.clip(u, 0.0, 1.0)
    return 0.5 - 0.5 * np.cos(np.pi * u)
