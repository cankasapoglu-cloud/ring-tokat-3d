#!/usr/bin/env python3
"""Balon Şarkısı kurgusu: 12 klibi şarkı sözlerinin zamanına oturtur, yazıları ve sesi ekler."""
import subprocess, os, json
D = os.path.dirname(os.path.abspath(__file__))
# sahne sınırları (saniye): şarkının yazıya dökülmüş söz zamanlarından
SINIR = [0, 3.3, 8.7, 13.05, 17.3, 21.8, 25.0, 29.4, 33.75, 38.1, 42.5, 46.3, 50.0]
YAZI = [("baslik", 0.6, 7.6, 150), ("kirmizi", 8.7, 12.9, 60), ("mavi", 13.05, 17.1, 60), ("sari", 17.3, 21.6, 60), ("yesil", 21.8, 23.9, 60)]
FPS = 24


def sure(f):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f],
                                capture_output=True, text=True, check=True).stdout)


girdi, filtre = [], []
for i in range(12):
    f = os.path.join(D, "klip", f"{i + 1:02d}.mp4")
    hedef, ham = SINIR[i + 1] - SINIR[i], sure(f)
    hiz = min(1.25, max(0.9, (ham - 0.1) / hedef))          # kısa sahnelerde hafif hızlandır, gerisini kırp
    girdi += ["-i", f]
    filtre.append(f"[{i}:v]trim=0:{hedef * hiz:.3f},setpts=(PTS-STARTPTS)/{hiz:.4f},fps={FPS},scale=1920:1080,setsar=1[v{i}]")
filtre.append("".join(f"[v{i}]" for i in range(12)) + "concat=n=12:v=1:a=0[vid]")
son = "vid"
for k, (ad, t0, t1, y) in enumerate(YAZI):
    girdi += ["-loop", "1", "-t", "50", "-i", os.path.join(D, "yazi", ad + ".png")]
    filtre.append(f"[{12 + k}:v]format=rgba,fade=in:st={t0}:d=0.3:alpha=1,fade=out:st={t1 - 0.3}:d=0.3:alpha=1[y{k}]")
    filtre.append(f"[{son}][y{k}]overlay=0:{y - 190 + 60}:enable='between(t,{t0},{t1})'[o{k}]")
    son = f"o{k}"
filtre.append(f"[{son}]fade=in:st=0:d=0.4,fade=out:st=49.3:d=0.7[v]")
girdi += ["-i", os.path.join(D, "sarki.mp3")]
ses = len(YAZI) + 12
cikti = os.path.join(D, "balon-sarkisi.mp4")
subprocess.run(["ffmpeg", "-y", "-v", "error", *girdi, "-filter_complex", ";".join(filtre),
                "-map", "[v]", "-map", f"{ses}:a", "-af", "loudnorm=I=-15:TP=-1.5,afade=in:d=0.3,afade=out:st=49:d=1",
                "-t", "50", "-c:v", "libx264", "-profile:v", "main", "-level", "4.0", "-preset", "slow", "-crf", "21",
                "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", cikti], check=True)
print("video:", cikti, f"{os.path.getsize(cikti) / 1e6:.1f} MB", f"{sure(cikti):.2f} sn")
