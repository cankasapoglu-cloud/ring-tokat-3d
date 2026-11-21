#!/usr/bin/env python3
"""Şarkıdaki uzun müzik boşluklarını ölçü sınırlarından keserek kısaltır -> sarki_kisa.wav
Her kıta: 4 ölçü söz + 2 ölçü ara. Sonda ninni dizesi."""
import subprocess, wave, os
import numpy as np
D = os.path.dirname(os.path.abspath(__file__))
SR = 44100
OLCU = 2.19                                    # bir ölçü (sn), satır aralıklarından
KITA = [7.06, 36.52, 67.12, 97.64, 128.16]     # kıta başlangıçları (yazıya dökümden)
NINNI = 156.56                                 # "Maymunlar uyudu" başlangıcı
raw = subprocess.run(["ffmpeg", "-v", "error", "-i", os.path.join(D, "sarki_1.mp3"), "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"],
                     check=True, capture_output=True).stdout
a = np.frombuffer(raw, dtype=np.float32).reshape(-1, 2).astype(np.float64)
ON = 0.12                                      # sözün hemen öncesinden başla
parca = [(KITA[0] - 2 * OLCU - ON, KITA[0] - ON)] + [(k - ON, k - ON + 6 * OLCU) for k in KITA] + [(NINNI - OLCU - ON, len(a) / SR - 2.0)]
gecis = int(0.08 * SR)
cikti = np.zeros((0, 2))
for (t0, t1) in parca:
    p = a[int(t0 * SR):int(t1 * SR) + gecis].copy()
    if len(cikti):
        r = np.linspace(0, 1, gecis)[:, None]
        cikti[-gecis:] = cikti[-gecis:] * (1 - r) + p[:gecis] * r
        p = p[gecis:]
    cikti = np.vstack([cikti, p])
son = int(1.5 * SR)
cikti[-son:] *= np.linspace(1, 0, son)[:, None]
cikti = cikti / np.abs(cikti).max() * 0.95
with wave.open(os.path.join(D, "sarki_kisa.wav"), "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((cikti * 32767).astype(np.int16).tobytes())
print(f"sarki_kisa.wav: {len(cikti) / SR:.2f} sn")
