#!/usr/bin/env python3
"""Ortak zarflar ve perde izleri (kesim.py, atlari.py ve cizim icin). Hepsi ozellik.npz'nin 2 ms'lik izgarasinda.
yeni3/analiz/kesim/kod/kesim.py'nin bas kismindan ayrildi."""
import numpy as np, soundfile as sf
from scipy.signal import butter, sosfiltfilt
from ortak import VOKAL, ozellik

z = ozellik()
t = z["t"]; DT = float(t[1] - t[0]); HOP = int(z["hop"])
x, fs = sf.read(VOKAL)
if x.ndim > 1:
    x = x.mean(axis=1)
x = x.astype(np.float64)


def fi(v):
    return int(round(v / DT))


def zarf(lo, hi, pencere_ms):
    """Bant geciren + kare + Hann yumusatma -> 2 ms izgarada dB zarf."""
    if lo is None:
        y = x
    else:
        sos = butter(4, [lo, hi], btype="band", fs=fs, output="sos"); y = sosfiltfilt(sos, x)
    n = int(pencere_ms / 1000 * fs) | 1
    h = np.hanning(n + 2)[1:-1]; h /= h.sum()
    p = np.convolve(y ** 2, h, "same")
    idx = np.minimum(np.arange(len(t)) * HOP, len(x) - 1)
    return 10 * np.log10(p[idx] + 1e-12)


db_ham = 20 * np.log10(z["rms"] + 1e-9)        # 10 ms RMS
E12 = zarf(300, 3400, 12)        # sinir cukurlari icin
E30 = zarf(300, 3400, 30)        # cekirdek (tepe) icin
ELOW = zarf(100, 1000, 20)       # temel + F1 bandi
ELOW8 = zarf(100, 1000, 8)       # ayni bant, ince zaman cozunurlugu (otum baslangici / unlu bitisi)
F2B = zarf(1000, 3400, 12)       # F2-F3 bandi: unlu ile l / n / m arasindaki fark
EHI = zarf(4000, 12000, 5)       # s, ç, t patlamasi
R5 = zarf(None, None, 5)         # tam bant, 5 ms
FLX = np.convolve(z["fluxabs"], np.hanning(7) / np.hanning(7).sum(), "same")
FLXP = np.convolve(z["flux"], np.hanning(7) / np.hanning(7).sum(), "same")
LMEL = z["logmel"].astype(np.float64)
MEL_KENAR = z["mel_edges"]
th = z["th"]; f0h = z["f0h"]; f0s = z["f0s"]; FP = float(th[1] - th[0])
midi = lambda f: 69 + 12 * np.log2(np.asarray(f, dtype=float) / 440.0)
NOTA = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def nota_adi(m):
    r = int(round(m)); return "%s%d" % (NOTA[r % 12], r // 12 - 1)


def r4(v):
    return None if v is None else round(float(v), 4)


def r1(v):
    return None if v is None else round(float(v), 1)


def r2(v):
    return None if v is None else round(float(v), 2)
