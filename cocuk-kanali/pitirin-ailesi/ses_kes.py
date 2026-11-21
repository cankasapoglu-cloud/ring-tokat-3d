#!/usr/bin/env python3
"""yavas_2.mp3 kıtalar arasında 20 sn'lik çalgı boşluklarıyla 185 sn çıktı.
Her kıtayı 12 sn'lik (4 ölçü, ölçü = 3 sn) blok olarak kesip art arda dizer -> sarki_kisa.wav (84 sn)."""
import subprocess, os
D = os.path.dirname(os.path.abspath(__file__))
# (başlangıç, bitiş) kaynak saniyeleri: giriş+1. kıta, 2-6. kıtalar, çalgılı kapanış
BLOK = [(0, 18.08), (40.60, 52.60), (72.06, 84.06), (108.04, 120.04), (138.04, 150.04), (174.04, 185.04), (149.04, 156.04)]
f = []
for k, (a, b) in enumerate(BLOK):
    s = b - a
    son = f"afade=out:st={s - 3.5:.2f}:d=3.5" if k == len(BLOK) - 1 else f"afade=out:st={s - 0.02:.2f}:d=0.02"
    f.append(f"[0:a]atrim={a}:{b},asetpts=PTS-STARTPTS,afade=in:d=0.02,{son}[a{k}]")
f.append("".join(f"[a{k}]" for k in range(len(BLOK))) + f"concat=n={len(BLOK)}:v=0:a=1[a]")
c = os.path.join(D, "sarki_kisa.wav")
subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", os.path.join(D, "yavas_2.mp3"), "-filter_complex", ";".join(f), "-map", "[a]", c], check=True)
print(c, sum(b - a for a, b in BLOK))
