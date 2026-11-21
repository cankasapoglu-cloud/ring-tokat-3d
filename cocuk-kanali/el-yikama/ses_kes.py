#!/usr/bin/env python3
"""sarki_1.mp3'teki iki çalgı boşluğunu (birer ve ikişer ölçü) keser -> sarki_kisa.wav (66 sn). Dizeler 6 sn aralıkla dizilir."""
import subprocess, os
D = os.path.dirname(os.path.abspath(__file__))
BLOK = [(0, 17.7), (20.7, 44.6), (50.6, 75.02)]
f = [f"[0:a]atrim={a}:{b},asetpts=PTS-STARTPTS,afade=in:d=0.02,afade=out:st={b - a - 0.02:.2f}:d=0.02[a{k}]" for k, (a, b) in enumerate(BLOK)]
f.append("".join(f"[a{k}]" for k in range(len(BLOK))) + f"concat=n={len(BLOK)}:v=0:a=1[a]")
subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", os.path.join(D, "sarki_1.mp3"), "-filter_complex", ";".join(f), "-map", "[a]", os.path.join(D, "sarki_kisa.wav")], check=True)
