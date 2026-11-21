#!/usr/bin/env python3
"""dinle_2.mp3'ün kıta aralarına gerçek hayvan seslerini ikişer kez yerleştirir -> sarki_hayvanli.mp3.
Kıta bitişleri ("dinle bak"ın sonu) yazıya dökümden alındı."""
import subprocess, os, json
D = os.path.dirname(os.path.abspath(__file__))
K = os.path.join(D, "yeni", "ses", "kirpilmis")
BITIS = [("inek", 14.46), ("koyun", 26.74), ("at", 41.10), ("horoz", 54.80), ("ordek", 67.58), ("kopek", 82.20), ("kedi", 94.38)]
SONRAKI = [18.62, 33.12, 46.56, 59.48, 73.96, 86.40, 100.84]


def sure(f):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f], capture_output=True, text=True, check=True).stdout)


girdi, f, etiket, zaman = ["-i", os.path.join(D, "dinle_2.mp3")], [], [], []
kis = "+".join(f"between(t,{b + 0.1:.2f},{s - 0.15:.2f})" for (_, b), s in zip(BITIS, SONRAKI))
f.append(f"[0:a]volume='if({kis},0.45,1)':eval=frame[m]")
n = 1
for (ad, b), s in zip(BITIS, SONRAKI):
    f1, f2 = os.path.join(K, ad + "_1.wav"), os.path.join(K, ad + "_2.wav")
    d1, d2 = sure(f1), sure(f2)
    bosluk = s - b
    ara = max(0.08, min(0.35, (bosluk - 0.35 - d1 - d2) / 2))
    t1 = b + 0.2; t2 = t1 + d1 + ara
    zaman.append({"hayvan": ad, "ses1": round(t1, 2), "ses2": round(t2, 2), "bitis": round(t2 + d2, 2), "sonraki_kita": s})
    for dosya, t in ((f1, t1), (f2, t2)):
        girdi += ["-i", dosya]
        f.append(f"[{n}:a]aformat=sample_rates=44100:channel_layouts=stereo,volume=1.5,adelay={int(t * 1000)}:all=1[s{n}]"); etiket.append(f"[s{n}]"); n += 1
f.append("[m]" + "".join(etiket) + f"amix=inputs={n}:normalize=0:duration=first,loudnorm=I=-14:TP=-1.5[o]")
subprocess.run(["ffmpeg", "-y", "-v", "error", *girdi, "-filter_complex", ";".join(f), "-map", "[o]", "-b:a", "192k", os.path.join(D, "sarki_hayvanli.mp3")], check=True)
json.dump(zaman, open(os.path.join(D, "sarki_hayvanli_zaman.json"), "w"), ensure_ascii=False, indent=1)
for z in zaman: print(z)
