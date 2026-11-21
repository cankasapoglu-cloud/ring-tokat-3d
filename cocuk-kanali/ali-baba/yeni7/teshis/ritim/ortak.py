#!/usr/bin/env python3
"""Ortak yollar ve yardımcılar (ritim / zamanlama teşhisi). Hiçbir mevcut dosyayı değiştirmez; yalnız okur."""
import json, os, subprocess, numpy as np, soundfile as sf
from scipy import signal

D = os.path.dirname(os.path.abspath(__file__))
A = os.path.abspath(os.path.join(D, "..", "..", ".."))          # ali-baba
KOK = os.path.dirname(A)                                         # cocuk-kanali
ARA = os.path.join(D, "ara"); os.makedirs(ARA, exist_ok=True)
SEP = "/tmp/claude-0/-home-user-ring-tokat-3d/bd9d6832-1bf0-57ca-8544-ce6f4befd453/scratchpad/sep/out_mdx"

RED_MP3 = os.path.join(A, "yeni6", "sarki_A_ozgun_ses.mp3")
RED_VOK = os.path.join(A, "yeni6", "vokal_psola.wav")
RED_BAND = os.path.join(A, "yeni4", "altyapi", "altyapi_G.wav")
RED_EZGI = os.path.join(A, "yeni4", "altyapi", "ezgi_alti_G.wav")
ZAMAN = os.path.join(A, "yeni4", "altyapi", "zaman_G.json")
YERLESIM = os.path.join(A, "yeni4", "vokal", "yerlesim.json")
HEDEF = os.path.join(A, "yeni6", "hedefler.json")
REF_MP3 = os.path.join(A, "v2_2.mp3")
REF_VOK = os.path.join(SEP, "v2_2_(Vocals)_UVR-MDX-NET-Voc_FT.wav")
REF_ENS = os.path.join(SEP, "v2_2_(Instrumental)_UVR-MDX-NET-Voc_FT.wav")
LATTICE = os.path.join(A, "yeni4", "analiz", "tempo", "lattice.json")

FS = 44100
ON = 0.100                       # reddedilen karışımda her şeyin başındaki sessizlik
VURUS = 60.0 / 105.0             # reddedilen karışım: tam 105.000
OLCU = 4 * VURUS
_L = json.load(open(LATTICE))
REF_VURUS = _L["beat_period_s"]; REF_FAZ = _L["phase_first_beat_s"]   # referans: vuruş n = FAZ + n * REF_VURUS


def oku_mono(yol, fs=FS):
    x, f = sf.read(yol, always_2d=True); x = x.mean(axis=1)
    if f != fs: x = signal.resample_poly(x, fs, f)
    return x.astype(np.float64)


def mp3_coz(yol, cikti, fs=FS):
    if not os.path.exists(cikti):
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", yol, "-ar", str(fs), "-ac", "1", "-c:a", "pcm_s16le", cikti], check=True)
    return oku_mono(cikti, fs)


def bant(x, lo, hi, fs=FS, n=4):
    if lo is None: sos = signal.butter(n, hi, "lowpass", fs=fs, output="sos")
    elif hi is None: sos = signal.butter(n, lo, "highpass", fs=fs, output="sos")
    else: sos = signal.butter(n, [lo, hi], "bandpass", fs=fs, output="sos")
    return signal.sosfiltfilt(sos, x)


def zarf(x, fs=FS, ms=5.0, adim_ms=1.0):
    """RMS zarfı: ms'lik pencere, adim_ms adımla (1 kHz zarf)."""
    w = int(ms * fs / 1000); k = np.ones(w) / w
    e = np.sqrt(np.maximum(signal.fftconvolve(x * x, k, "same"), 0))
    h = int(adim_ms * fs / 1000)
    return e[::h], fs / h


def ozet(a, ad=""):
    a = np.asarray(a, float); a = a[~np.isnan(a)]
    if len(a) == 0: return {"ad": ad, "n": 0}
    return {"ad": ad, "n": int(len(a)), "ortanca": round(float(np.median(a)), 1), "ortalama": round(float(a.mean()), 1), "ss": round(float(a.std()), 1),
            "p10": round(float(np.percentile(a, 10)), 1), "p25": round(float(np.percentile(a, 25)), 1), "p75": round(float(np.percentile(a, 75)), 1), "p90": round(float(np.percentile(a, 90)), 1),
            "mutlak_ortanca": round(float(np.median(np.abs(a))), 1), "yuzde_30ms_ici": round(float((np.abs(a) <= 30).mean() * 100), 1), "yuzde_50ms_ici": round(float((np.abs(a) <= 50).mean() * 100), 1),
            "en_kucuk": round(float(a.min()), 1), "en_buyuk": round(float(a.max()), 1)}
