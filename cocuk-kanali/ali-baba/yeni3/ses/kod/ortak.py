# -*- coding: utf-8 -*-
"""Ortak yardimcilar: kaynak okuma, zarf (envelope), bolut bulma, spektral istatistik."""
import os, subprocess, numpy as np

A = '/home/user/ring-tokat-3d/cocuk-kanali/ali-baba'
ALT = os.path.join(A, 'yeni', 'ses', 'alternatif')
OUT = os.path.join(A, 'yeni3', 'ses')
SR = 44100
HOP = 0.005      # zarf adimi (s)
WIN = 0.020      # zarf penceresi (s)


def oku(yol, sr=SR):
    """ffmpeg ile mono float32 okur (stereo ise iki kanalin ortalamasi)."""
    cmd = ['ffmpeg', '-v', 'error', '-i', yol, '-ac', '1', '-ar', str(sr), '-f', 'f32le', '-']
    raw = subprocess.run(cmd, check=True, capture_output=True).stdout
    return np.frombuffer(raw, dtype=np.float32).astype(np.float64)


def zarf(x, sr=SR, hop=HOP, win=WIN):
    """RMS zarfi (dBFS). Kare t zamani = pencere merkezi."""
    h = int(round(hop * sr)); w = int(round(win * sr))
    pad = w // 2
    xp = np.concatenate([np.zeros(pad), x, np.zeros(pad)])
    c = np.concatenate([[0.0], np.cumsum(xp ** 2)])
    n = 1 + (len(x) - 1) // h
    idx = np.arange(n) * h
    e = (c[idx + w] - c[idx]) / w
    t = idx / sr
    return t, 10 * np.log10(np.maximum(e, 1e-14))


def bolutler(t, db, esik_db, min_bosluk=0.08, min_sure=0.03):
    """esik_db ustundeki araliklar; min_bosluk'tan kisa bosluklar birlestirilir."""
    on = db > esik_db
    seg = []
    i = 0
    n = len(on)
    while i < n:
        if on[i]:
            j = i
            while j + 1 < n and on[j + 1]:
                j += 1
            seg.append([t[i], t[j] + HOP])
            i = j + 1
        else:
            i += 1
    # birlestir
    bir = []
    for s in seg:
        if bir and s[0] - bir[-1][1] < min_bosluk:
            bir[-1][1] = s[1]
        else:
            bir.append(s)
    return [s for s in bir if s[1] - s[0] >= min_sure]


def genislet(t, db, s, e, esik_db, sinir=(0.0, None)):
    """[s,e] araligini zarf esik_db altina dusene kadar iki yana genisletir."""
    hi = sinir[1] if sinir[1] is not None else t[-1] + HOP
    i0 = int(np.searchsorted(t, s)); i1 = int(np.searchsorted(t, e)) - 1
    i0 = min(max(i0, 0), len(t) - 1); i1 = min(max(i1, 0), len(t) - 1)
    while i0 > 0 and db[i0 - 1] > esik_db and t[i0 - 1] >= sinir[0]:
        i0 -= 1
    while i1 + 1 < len(t) and db[i1 + 1] > esik_db and t[i1 + 1] < hi:
        i1 += 1
    return t[i0], t[i1] + HOP


def rms_db(x):
    return 10 * np.log10(max(float(np.mean(x ** 2)), 1e-14))


def tepe_db(x):
    return 20 * np.log10(max(float(np.max(np.abs(x))), 1e-7))
