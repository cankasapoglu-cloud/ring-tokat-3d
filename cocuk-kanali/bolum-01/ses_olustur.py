#!/usr/bin/env python3
"""Seslendirme kliplerini zaman cizelgesine yerlestirir, muzik ve efektleri
sentezler; ses/mix.wav ve dudak hareketi icin zarf.json uretir."""
import json, subprocess, wave, os
import numpy as np

D = os.path.dirname(os.path.abspath(__file__))
TL = json.load(open(os.path.join(D, "zaman.json")))
SR = 44100
N = int(TL["sure"] * SR)
FPS = TL["fps"]


def klip(ad):
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", os.path.join(D, "ses", ad + ".mp3"),
         "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"],
        check=True, capture_output=True).stdout
    a = np.frombuffer(raw, dtype=np.float32).astype(np.float64)
    return a / max(1e-6, np.abs(a).max()) * 0.9


def ekle(hedef, sinyal, t, kazanc=1.0):
    i = int(t * SR)
    if i >= len(hedef):
        return
    s = sinyal[: len(hedef) - i]
    hedef[i:i + len(s)] += s * kazanc


def nota(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


def marimba(f, sure=0.9):
    t = np.arange(int(sure * SR)) / SR
    s = np.sin(2 * np.pi * f * t) * np.exp(-t * 6)
    s += 0.35 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t * 10)
    s += 0.12 * np.sin(2 * np.pi * 4 * f * t) * np.exp(-t * 18)
    s[:60] *= np.linspace(0, 1, 60)
    return s


def zil(f, sure=1.2):
    t = np.arange(int(sure * SR)) / SR
    s = np.sin(2 * np.pi * f * t) * np.exp(-t * 4)
    s += 0.5 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t * 7)
    s[:40] *= np.linspace(0, 1, 40)
    return s


def kayma(f0, f1, sure=0.28):
    t = np.arange(int(sure * SR)) / SR
    f = f0 + (f1 - f0) * (t / sure) ** 2
    s = np.sin(2 * np.pi * np.cumsum(f) / SR)
    return s * np.sin(np.pi * t / sure) ** 2


def tik():
    t = np.arange(int(0.09 * SR)) / SR
    return np.sin(2 * np.pi * 950 * t) * np.exp(-t * 60)


# ---------- seslendirme ----------
konusma = np.zeros(N)
ekle(konusma, klip(TL["giris"]["ses"]), TL["giris"]["t"])
for tur in TL["turlar"]:
    ekle(konusma, klip(tur["soru"]), tur["t"] + TL["tur"]["soru"])
    ekle(konusma, klip(tur["cevap"]), tur["t"] + TL["tur"]["cevap"])
ekle(konusma, klip(TL["sayma"]["ses"]), TL["sayma"]["t"])
ekle(konusma, klip(TL["kapanis"]["ses"]), TL["kapanis"]["t"])

# ---------- muzik (8 olculuk dongu, 100 BPM, Do major) ----------
vurus = 0.6
akorlar = [(48, [60, 64, 67]), (45, [57, 60, 64]), (41, [57, 60, 65]), (43, [59, 62, 67])] * 2
ezgi = [
    [76, 79, 84, 79], [81, 84, 81, 76], [77, 81, 84, 81], [79, 83, 86, None],
    [84, 79, 76, 79], [81, 76, 72, 76], [77, 79, 81, 84], [79, 74, 79, None],
]
muzik = np.zeros(N)
dongu = 8 * 4 * vurus
t0 = 0.0
while t0 < TL["sure"]:
    for o in range(8):
        bas, akor = akorlar[o]
        for v in range(4):
            t = t0 + (o * 4 + v) * vurus
            if ezgi[o][v] is not None:
                ekle(muzik, marimba(nota(ezgi[o][v])), t, 0.55)
            if v in (0, 2):
                ekle(muzik, marimba(nota(bas), 1.1), t, 0.9)
            else:
                for n in akor:
                    ekle(muzik, marimba(nota(n), 0.6), t, 0.22)
    t0 += dongu

# ---------- efektler ----------
efekt = np.zeros(N)
P = TL["tur"]
for tur in TL["turlar"]:
    T = tur["t"]
    ekle(efekt, kayma(280, 880), T + 0.05, 0.35)                # balon geliyor
    for k in range(4):                                           # dusunme tikleri
        ekle(efekt, tik(), T + P["dusun"] + 0.3 + k * 0.6, 0.25)
    ekle(efekt, zil(1318.5), T + P["cevap"] - 0.08, 0.30)       # dogru cevap
    ekle(efekt, zil(1975.5), T + P["cevap"] + 0.04, 0.22)
    ekle(efekt, kayma(500, 1100, 0.16), T + P["nesne"], 0.25)   # nesne beliriyor
    ekle(efekt, kayma(900, 420, 0.5), T + P["tasi"], 0.18)      # balon yerine ucuyor
S = TL["sayma"]
for k, v in enumerate(S["vuruslar"]):
    ekle(efekt, marimba(nota([72, 76, 79, 84][k]), 1.0), S["t"] + v - 0.03, 0.75)
K = TL["kapanis"]
for k, n in enumerate([72, 76, 79, 84, 88]):
    ekle(efekt, zil(nota(n), 1.0), K["t"] - 0.35 + k * 0.09, 0.22)
for k, v in enumerate(K["renkler"]):
    ekle(efekt, marimba(nota([72, 76, 79, 84][k]), 0.8), K["t"] + v, 0.45)

# ---------- dudak zarfi (kare basina konusma siddeti) ----------
kare = SR // FPS
nk = int(TL["sure"] * FPS)
rms = np.array([np.sqrt(np.mean(konusma[i * kare:(i + 1) * kare] ** 2)) for i in range(nk)])
rms = np.clip(rms / np.percentile(rms[rms > 0.01], 85), 0, 1)
zarf = np.zeros(nk)
for i in range(1, nk):
    zarf[i] = rms[i] if rms[i] > zarf[i - 1] else zarf[i - 1] * 0.55 + rms[i] * 0.45
json.dump([round(float(x), 3) for x in zarf], open(os.path.join(D, "zarf.json"), "w"))

# ---------- karistirma: konusma varken muzigi kis ----------
aktif = np.repeat((rms > 0.05).astype(float), kare)
aktif = np.pad(aktif, (0, N - len(aktif)))
pencere = int(0.35 * SR)
aktif = np.convolve(aktif, np.ones(pencere) / pencere, mode="same")
muzik_kazanc = 0.20 - 0.11 * np.clip(aktif * 1.5, 0, 1)
mix = konusma + muzik * muzik_kazanc + efekt
mix[: int(0.3 * SR)] *= np.linspace(0, 1, int(0.3 * SR))
son = int(2.0 * SR)
mix[-son:] *= np.linspace(1, 0, son)
mix = np.tanh(mix * 1.1)
mix = mix / np.abs(mix).max() * 0.95

with wave.open(os.path.join(D, "ses", "mix.wav"), "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    pcm = (mix * 32767).astype(np.int16)
    w.writeframes(np.column_stack([pcm, pcm]).tobytes())
print("mix.wav yazildi:", round(len(mix) / SR, 2), "sn; kare:", nk)
