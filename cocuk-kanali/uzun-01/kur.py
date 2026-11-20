#!/usr/bin/env python3
"""Uzun bölüm kurucu: ses kliplerini ölçer, soru/cevap yerinden böler, zaman
çizelgesini (zaman.json) hesaplar, müzik + efektlerle ses/mix.wav üretir ve
dudak hareketi için zarf.json yazar."""
import json, subprocess, wave, os
import numpy as np

D = os.path.dirname(os.path.abspath(__file__))
SR, FPS = 44100, 30
DUSUN = 3.2       # çocuğun cevap vermesi için bekleme
TUR_SONU = 1.8    # cevaptan sonra nefes payı
YAP = 4.0         # hareket etkinliğinde birlikte yapma süresi


def yukle(ad, normal=True):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", os.path.join(D, "ses", ad + ".mp3"),
                          "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"], check=True, capture_output=True).stdout
    a = np.frombuffer(raw, dtype=np.float32).astype(np.float64)
    return a / max(1e-6, np.abs(a).max()) * 0.9 if normal else a


def sessizlikler(a, esik_db=-38, en_az=0.15):
    pen = int(0.01 * SR)
    n = len(a) // pen
    rms = np.sqrt(np.mean(a[:n * pen].reshape(n, pen) ** 2, axis=1))
    sessiz = rms < 10 ** (esik_db / 20)
    out, i = [], 0
    while i < n:
        if sessiz[i]:
            j = i
            while j < n and sessiz[j]:
                j += 1
            if (j - i) * 0.01 >= en_az:
                out.append((i * 0.01, j * 0.01))
            i = j
        else:
            i += 1
    return out


def bol(ad):
    """Klibi en uzun iç sessizlikten ikiye böler ([long pause] işareti)."""
    a = yukle(ad)
    sure = len(a) / SR
    ic = [s for s in sessizlikler(a) if s[0] > 0.2 and s[1] < sure - 0.2]
    s0, s1 = max(ic, key=lambda s: s[1] - s[0])
    assert s1 - s0 > 0.7, f"{ad}: belirgin duraklama yok ({s1 - s0:.2f})"
    return a[: int((s0 + 0.12) * SR)], a[int((s1 - 0.06) * SR):]


def baslangiclar(c, n):
    """Parçadaki ilk n söz başlangıcı + sonraki cümlenin başlangıcı."""
    sure = len(c) / SR
    son = [e for (s, e) in sessizlikler(c, en_az=0.14) if s > 0.15 and e < sure - 0.1]
    b = [0.0] + son
    assert len(b) >= n, f"yalnızca {len(b)} başlangıç bulundu, {n} gerekli"
    return b[:n], (b[n] if len(b) > n else sure)


N = int(16 * 60 * SR)
konusma, sarkilar, efekt = np.zeros(N), np.zeros(N), np.zeros(N)
muzik_bolge = []   # fon müziğinin çalacağı aralıklar


def ekle(hedef, sinyal, t, kazanc=1.0):
    i = int(t * SR)
    s = sinyal[: len(hedef) - i]
    hedef[i:i + len(s)] += s * kazanc
    return t + len(sinyal) / SR


def nota(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def marimba(f, sure=0.9):
    t = np.arange(int(sure * SR)) / SR
    s = np.sin(2 * np.pi * f * t) * np.exp(-t * 6) + 0.35 * np.sin(4 * np.pi * f * t) * np.exp(-t * 10)
    s[:60] *= np.linspace(0, 1, 60)
    return s


def zil(f, sure=1.2):
    t = np.arange(int(sure * SR)) / SR
    s = np.sin(2 * np.pi * f * t) * np.exp(-t * 4) + 0.5 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t * 7)
    s[:40] *= np.linspace(0, 1, 40)
    return s


def kayma(f0, f1, sure=0.28):
    t = np.arange(int(sure * SR)) / SR
    f = f0 + (f1 - f0) * (t / sure) ** 2
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * t / sure) ** 2


def tik(f=950):
    t = np.arange(int(0.09 * SR)) / SR
    return np.sin(2 * np.pi * f * t) * np.exp(-t * 60)


def sap():
    t = np.arange(int(0.12 * SR)) / SR
    g = np.random.RandomState(7).randn(len(t))
    return g * np.exp(-t * 45) * 0.8


def duz(ad, t):
    return ekle(konusma, yukle(ad), t)


def tur(q, c, t):
    soru = t + 0.4
    soru_bit = ekle(konusma, q, soru)
    cevap = soru_bit + DUSUN
    cevap_bit = ekle(konusma, c, cevap)
    ekle(efekt, kayma(280, 880), t + 0.05, 0.30)
    for k in range(4):
        ekle(efekt, tik(), soru_bit + 0.5 + k * 0.62, 0.22)
    ekle(efekt, zil(1318.5), cevap - 0.08, 0.28)
    ekle(efekt, zil(1975.5), cevap + 0.04, 0.20)
    return dict(t=t, soru=soru, soruBit=soru_bit, cevap=cevap, cevapBit=cevap_bit, bit=cevap_bit + TUR_SONU)


def ozet(ad, t, n):
    q, c = bol(ad)
    bit_q = ekle(konusma, q, t + 0.3)
    liste = bit_q + 0.5
    bit = ekle(konusma, c, liste)
    b, son = baslangiclar(c, n)
    for k, v in enumerate(b):
        ekle(efekt, marimba(nota([72, 74, 76, 79, 81, 84][k % 6]), 0.9), liste + v - 0.03, 0.6)
    return dict(t=t, liste=liste, vuruslar=[round(liste + v, 3) for v in b], son=round(liste + son, 3), bit=bit + 1.2)


def giris(ad, t):
    bit = duz(ad, t + 1.0)
    return dict(t=t + 1.0, bit=bit)


bolumler = []
t = 0.0


def bolum(tip, baslik=None, fon=True, **kw):
    b = dict(tip=tip, baslik=baslik, t0=t, **kw)
    bolumler.append(b)
    return b


def kapat(b, bit, fon=True):
    global t
    b["t1"] = round(bit, 3)
    if fon:
        muzik_bolge.append((b["t0"], b["t1"]))
    t = b["t1"]


# ---- 1. tema şarkısı ----
tema = min((yukle(f"tema_{k}", False) for k in (1, 2, 3, 4)), key=lambda a: np.sqrt(np.mean(a[-int(0.6 * SR):] ** 2)))
tema = tema / np.abs(tema).max() * 0.9
b = bolum("tema")
b["sarki"] = 0.3
kapat(b, ekle(sarkilar, tema, 0.3) + 0.2, fon=False)

# ---- 2. selam ----
b = bolum("selam")
b["giris"] = dict(t=t + 0.5, bit=duz("a0_selam", t + 0.5))
kapat(b, b["giris"]["bit"] + 0.8)

# ---- 3. renkler ----
b = bolum("renkler", "Renkler")
b["giris"] = giris("b0_giris", t)
c = b["giris"]["bit"] + 0.5
b["turlar"] = []
for q, a in (("02_soru1", "03_kirmizi"), ("04_soru2", "05_mavi"), ("06_soru3", "07_sari"), ("08_soru4", "09_yesil")):
    b["turlar"].append(tur(yukle(q), yukle(a), c)); c = b["turlar"][-1]["bit"]
for ad in ("b5_turuncu", "b6_mor"):
    b["turlar"].append(tur(*bol(ad), c)); c = b["turlar"][-1]["bit"]
b["ozet"] = ozet("b7_ozet", c, 6)
kapat(b, b["ozet"]["bit"])

# ---- 4. sayılar ----
b = bolum("sayilar", "Sayılar")
b["giris"] = giris("c0_giris", t)
c = b["giris"]["bit"] + 0.5
b["turlar"] = []
for k in range(1, 6):
    b["turlar"].append(tur(*bol(f"c{k}"), c)); c = b["turlar"][-1]["bit"]
b["ozet"] = ozet("c6_ozet", c, 5)
kapat(b, b["ozet"]["bit"])

# ---- 5. balon şarkısı ----
sarki = yukle("sarki_1", False)
sarki = min((yukle(f"sarki_{k}", False) for k in (1, 2, 3, 4)), key=lambda a: np.sqrt(np.mean(a[-int(0.6 * SR):] ** 2)))
sarki = sarki / np.abs(sarki).max() * 0.9
b = bolum("sarki", "Şarkı Zamanı")
b["giris"] = giris("d0_sarki_giris", t)
b["sarki"] = b["giris"]["bit"] + 0.5
muzik_bolge.append((b["t0"], b["sarki"] - 0.3))
kapat(b, ekle(sarkilar, sarki, b["sarki"]) + 0.3, fon=False)

# ---- 6. şekiller ----
b = bolum("sekiller", "Şekiller")
b["giris"] = giris("e0_giris", t)
c = b["giris"]["bit"] + 0.5
b["turlar"] = []
for k in range(1, 5):
    b["turlar"].append(tur(*bol(f"e{k}"), c)); c = b["turlar"][-1]["bit"]
b["ozet"] = ozet("e5_ev", c, 4)
b["ozet"]["bit"] += 1.5
kapat(b, b["ozet"]["bit"])

# ---- 7. hareket etkinliği ----
b = bolum("hareket", "Hareket Zamanı")
b["giris"] = giris("f0_giris", t)
c = b["giris"]["bit"] + 0.6
b["turlar"] = []
for k in range(1, 6):
    bit = duz(f"f{k}", c + 0.3)
    b["turlar"].append(dict(t=c, hareket=c + 1.0, konusmaBit=bit, bit=bit + YAP))
    if k == 1:
        for v in np.arange(c + 1.3, bit + YAP - 0.3, 1 / 3.0):
            ekle(efekt, sap(), v, 0.10)
    c = bit + YAP
kapat(b, c)

# ---- 8. hayvanlar ----
b = bolum("hayvanlar", "Hayvanlar")
b["giris"] = giris("g0_giris", t)
c = b["giris"]["bit"] + 0.5
b["turlar"] = []
for k in range(1, 5):
    b["turlar"].append(tur(*bol(f"g{k}"), c)); c = b["turlar"][-1]["bit"]
bit = duz("g5_ozet", c + 0.4)
b["ozet"] = dict(t=c + 0.4, bit=bit)
kapat(b, bit + 1.2)

# ---- 9. taşıtlar ----
b = bolum("tasitlar", "Taşıtlar")
b["giris"] = giris("j0_giris", t)
c = b["giris"]["bit"] + 0.5
b["turlar"] = []
for k in range(1, 5):
    b["turlar"].append(tur(*bol(f"j{k}"), c)); c = b["turlar"][-1]["bit"]
bit = duz("j5_ozet", c + 0.4)
b["ozet"] = dict(t=c + 0.4, bit=bit)
kapat(b, bit + 1.2)

# ---- 10. hafıza oyunu ----
b = bolum("oyun", "Oyun Zamanı")
b["giris"] = giris("h0_giris", t)
c = b["giris"]["bit"] + 0.5
b["turlar"] = []
for k, eksik in zip(range(1, 4), (2, 1, 0)):
    r = tur(*bol(f"h{k}"), c)
    r["eksik"] = eksik
    b["turlar"].append(r); c = r["bit"]
kapat(b, c)

# ---- 11. kapanış ----
b = bolum("kapanis")
b["giris"] = dict(t=t + 0.6, bit=duz("i0_kapanis", t + 0.6))
b["sarki"] = b["giris"]["bit"] + 0.4
muzik_bolge.append((b["t0"], b["sarki"] - 0.3))
son = tema[: int(17 * SR)].copy()
son[-int(3 * SR):] *= np.linspace(1, 0, int(3 * SR))
kapat(b, ekle(sarkilar, son, b["sarki"]) + 0.5, fon=False)

SURE = round(t, 2)
N = int(SURE * SR)
konusma, sarkilar, efekt = konusma[:N], sarkilar[:N], efekt[:N]

# ---- fon müziği (yalnızca konuşmalı bölümlerde) ----
vurus = 0.6
akorlar = [(48, [60, 64, 67]), (45, [57, 60, 64]), (41, [57, 60, 65]), (43, [59, 62, 67])] * 2
ezgi = [[76, 79, 84, 79], [81, 84, 81, 76], [77, 81, 84, 81], [79, 83, 86, None],
        [84, 79, 76, 79], [81, 76, 72, 76], [77, 79, 81, 84], [79, 74, 79, None]]
fon = np.zeros(N)
t0 = 0.0
while t0 < SURE:
    for o in range(8):
        bas, akor = akorlar[o]
        for v in range(4):
            tt = t0 + (o * 4 + v) * vurus
            if tt >= SURE - 1:
                break
            if ezgi[o][v] is not None:
                ekle(fon, marimba(nota(ezgi[o][v])), tt, 0.55)
            if v in (0, 2):
                ekle(fon, marimba(nota(bas), 1.1), tt, 0.9)
            else:
                for n in akor:
                    ekle(fon, marimba(nota(n), 0.6), tt, 0.22)
    t0 += 8 * 4 * vurus
maske = np.zeros(N)
for a, z in muzik_bolge:
    maske[int(a * SR):int(z * SR)] = 1
pen = int(0.5 * SR)
maske = np.convolve(maske, np.ones(pen) / pen, mode="same")

# ---- dudak zarfı ----
kare = SR // FPS
nk = int(SURE * FPS)


def kare_rms(a):
    return np.array([np.sqrt(np.mean(a[i * kare:(i + 1) * kare] ** 2)) for i in range(nk)])


rk, rs = kare_rms(konusma), kare_rms(sarkilar)
rms = np.clip(rk / np.percentile(rk[rk > 0.01], 85), 0, 1)
rms_s = np.clip(rs / np.percentile(rs[rs > 0.01], 90), 0, 1) ** 2 * 0.8
ham = np.maximum(rms, rms_s)
zarf = np.zeros(nk)
for i in range(1, nk):
    zarf[i] = ham[i] if ham[i] > zarf[i - 1] else zarf[i - 1] * 0.55 + ham[i] * 0.45
json.dump([round(float(x), 3) for x in zarf], open(os.path.join(D, "zarf.json"), "w"))

aktif = np.repeat((rms > 0.05).astype(float), kare)
aktif = np.pad(aktif, (0, N - len(aktif)))
aktif = np.convolve(aktif, np.ones(int(0.35 * SR)) / int(0.35 * SR), mode="same")
fon_kazanc = (0.20 - 0.11 * np.clip(aktif * 1.5, 0, 1)) * maske
mix = konusma + sarkilar * 0.8 + fon * fon_kazanc + efekt
mix[: int(0.3 * SR)] *= np.linspace(0, 1, int(0.3 * SR))
mix[-int(1.0 * SR):] *= np.linspace(1, 0, int(1.0 * SR))
mix = np.tanh(mix * 1.1)
mix = mix / np.abs(mix).max() * 0.95
with wave.open(os.path.join(D, "ses", "mix.wav"), "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    pcm = (mix * 32767).astype(np.int16)
    w.writeframes(np.column_stack([pcm, pcm]).tobytes())


def yuvarla(o):
    if isinstance(o, float):
        return round(o, 3)
    if isinstance(o, dict):
        return {k: yuvarla(v) for k, v in o.items()}
    if isinstance(o, list):
        return [yuvarla(v) for v in o]
    return o


json.dump(yuvarla(dict(fps=FPS, sure=SURE, bolumler=bolumler)), open(os.path.join(D, "zaman.json"), "w"),
          ensure_ascii=False, indent=1)
print(f"toplam süre: {SURE:.1f} sn = {SURE / 60:.2f} dk, kare: {nk}")
for b in bolumler:
    print(f"  {b['tip']:10s} {b['t0']:7.1f} - {b['t1']:7.1f}  ({b['t1'] - b['t0']:.1f} sn)")
