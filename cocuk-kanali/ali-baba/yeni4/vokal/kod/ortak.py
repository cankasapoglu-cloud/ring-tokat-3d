#!/usr/bin/env python3
"""Ortak yardimcilar: yollar, sarki formu (ornek cinsinden TAM sayilar), ses okuma, duzey olcumu, yukseltilmis kosinus gecisler.
(yeni3/vokal/kod/ortak.py'den uyarlandi.)"""
import os, json, numpy as np, soundfile as sf

V = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))            # .../yeni4/vokal
A = os.path.dirname(os.path.dirname(V))                                    # .../ali-baba
VOKAL = os.path.join(V, "kaynak", "v2_2_vokal.wav")
KESIM = os.path.join(A, "yeni4", "analiz", "kesim", "kesim.json")
TEMPO = os.path.join(A, "yeni4", "analiz", "tempo", "tempo.json")
KAFES = os.path.join(A, "yeni4", "analiz", "tempo", "lattice.json")
CIKTI_WAV = os.path.join(V, "vokal_dogal.wav")
CIKTI_JSON = os.path.join(V, "yerlesim.json")
ARA = os.path.join(V, "ara")

SR = 44100

# ------------------------------------------------------------------ sarki formu (105.000 BPM; 44.1 kHz'te tam sayi)
BPM = 105.0
BEAT_N = 25200                      # 60/105 s * 44100 = 25200 ornek (tam)
BAR_N = 100800                      # 240/105 s * 44100 = 100800 ornek (tam)
GIRIS_N = 4410                      # 0.100 s on bosluk
BEAT = BEAT_N / SR
BAR = BAR_N / SR
GIRIS = GIRIS_N / SR
INTRO, KITA_OLCU, N_KITA, SON = 4, 8, 7, 4
TOPLAM_OLCU = INTRO + KITA_OLCU * N_KITA + SON           # 64
KUYRUK_N = 110250                   # 2.5 s
N_OUT = GIRIS_N + TOPLAM_OLCU * BAR_N + KUYRUK_N         # 6 565 860 ornek = 148.885714 s
TEPE_DBFS = -3.0
# parca -> kita icindeki hedef olcu (parca 3 = 'diye bagirir' + L4: 'diye'yi iceren kaynak olcusu -> olcu 5)
PARCA_OLCUSU = {1: 0, 2: 2, 3: 5}
# parca -> kita icindeki KAYNAK olcusu (mp3 zaman cizgisi; kita = 4 soylenen + 2 calgi olcusu)
PARCA_KAYNAK_OLCUSU = {1: 0, 2: 1, 3: 2}


def olcu_basi_n(olcu):
    """Hedef dosyada n. olcunun vurus-1 ornegi."""
    return GIRIS_N + olcu * BAR_N


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


def kaynak_olcu_basi(kafes, kita_no, olcu):
    """mp3 zaman cizgisinde kita_no (1..7) kitasinin 'olcu'. olcusunun vurus-1 ani (s); 105.003 BPM kafesinden, yuvarlamasiz."""
    vurus = 15 + 24 * (kita_no - 1) + 4 * olcu
    return kafes["phase_first_beat_s"] + vurus * kafes["beat_period_s"]
