#!/usr/bin/env python3
"""Ortak yardimcilar (yollar, ses okuma, duzey olcumu, yukseltilmis kosinus gecisler)."""
import os, json, numpy as np, soundfile as sf

V = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))            # .../yeni3/vokal
A = os.path.dirname(os.path.dirname(V))                                    # .../ali-baba
VOKAL = os.path.join(A, "dinle_2_vokal.wav")
KESIM = os.path.join(A, "yeni3", "analiz", "kesim", "kesim.json")
TEMPO = os.path.join(A, "yeni3", "analiz", "tempo", "tempo.json")
CIKTI_WAV = os.path.join(V, "vokal_dogal.wav")
CIKTI_JSON = os.path.join(V, "yerlesim.json")

SR = 44100


def oku_vokal():
    x, sr = sf.read(VOKAL, dtype="float64")
    assert sr == SR and x.ndim == 1, (sr, x.shape)
    return x


def oku_json(p):
    with open(p, encoding="utf8") as f:
        return json.load(f)


def db(v):
    return 20.0 * np.log10(max(float(v), 1e-10))


def rms_db(x, t0, t1, sr=SR):
    a, b = max(0, int(round(t0 * sr))), min(len(x), int(round(t1 * sr)))
    if b <= a:
        return -200.0
    return db(np.sqrt(np.mean(x[a:b] ** 2)))


def zarf(x, pencere_ms=1.0, sr=SR):
    """Kayan RMS zarfi (dogrusal); ornek basina bir deger, pencere ortalanmis."""
    n = max(1, int(round(pencere_ms * 1e-3 * sr)))
    c = np.cumsum(np.concatenate([[0.0], x ** 2]))
    e = (c[n:] - c[:-n]) / n
    out = np.zeros(len(x))
    h = n // 2
    out[h:h + len(e)] = e
    return np.sqrt(out)


def kos_yuksel(n):
    """0 -> 1 yukseltilmis kosinus (n ornek)."""
    if n <= 0:
        return np.zeros(0)
    return 0.5 - 0.5 * np.cos(np.pi * (np.arange(n) + 0.5) / n)


def kos_alcal(n):
    return kos_yuksel(n)[::-1]
