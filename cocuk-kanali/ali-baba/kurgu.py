#!/usr/bin/env python3
"""Ali Baba'nın Çiftliği kurgusu: 15 klibi şarkı sözlerinin zamanına oturtur, başlık karesi,
hayvan adları ve sesi ekler."""
import subprocess, os
D = os.path.dirname(os.path.abspath(__file__))
FPS, SON = 24, 75.0
# (klip no, başlangıç, bitiş) — şarkının yazıya dökülmüş söz zamanlarından
SAHNE = [(1, 4.2, 9.14), (2, 9.14, 13.5), (3, 13.5, 17.98), (4, 17.98, 22.86), (5, 22.86, 27.2), (6, 27.2, 31.7),
         (7, 31.7, 36.56), (8, 36.56, 40.95), (9, 40.95, 45.42), (10, 45.42, 50.3), (11, 50.3, 54.7), (12, 54.7, 59.3),
         (13, 59.3, 64.0), (14, 64.0, 68.4), (15, 68.4, 72.86)]
YAZI = [("baslik", 0.5, 8.6, 150), ("inek", 13.5, 17.8, 120), ("koyun", 27.2, 31.5, 120), ("ordek", 40.95, 45.2, 120),
        ("kopek", 54.7, 59.1, 120), ("kedi", 68.4, 72.6, 120)]
KIRP = {}   # kusurlu kliplerde kullanılacak en uzun süre (sn), ör. {1: 3.3}


def sure(f):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f],
                                capture_output=True, text=True, check=True).stdout)


girdi = ["-loop", "1", "-t", "4.2", "-i", os.path.join(D, "kare", "01.png")]
kare = round(4.2 * FPS)
filtre = [f"[0:v]scale=2304:1296,zoompan=z='1+0.0010*on':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={kare}:s=1920x1080:fps={FPS},"
          f"trim=0:4.2,setpts=PTS-STARTPTS,setsar=1[v0]"]
for k, (no, t0, t1) in enumerate(SAHNE, start=1):
    f = os.path.join(D, "klip", f"{no:02d}.mp4")
    hedef, ham = t1 - t0, min(sure(f) - 0.1, KIRP.get(no, 99))
    hiz = min(1.25, max(0.88, ham / hedef))
    girdi += ["-i", f]
    ek = f",tpad=stop_mode=clone:stop_duration={SON - t1 + 0.2:.2f}" if no == 15 else ""
    filtre.append(f"[{k}:v]trim=0:{hedef * hiz:.3f},setpts=(PTS-STARTPTS)/{hiz:.4f},fps={FPS},scale=1920:1080,setsar=1{ek}[v{k}]")
n = len(SAHNE) + 1
filtre.append("".join(f"[v{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0[vid]")
son = "vid"
for k, (ad, t0, t1, y) in enumerate(YAZI):
    girdi += ["-loop", "1", "-t", str(SON), "-i", os.path.join(D, "yazi", ad + ".png")]
    filtre.append(f"[{n + k}:v]format=rgba,fade=in:st={t0}:d=0.3:alpha=1,fade=out:st={t1 - 0.3}:d=0.3:alpha=1[y{k}]")
    filtre.append(f"[{son}][y{k}]overlay=0:{y - 190}:enable='between(t,{t0},{t1})'[o{k}]")
    son = f"o{k}"
filtre.append(f"[{son}]fade=in:st=0:d=0.4,fade=out:st={SON - 0.7}:d=0.7[v]")
girdi += ["-i", os.path.join(D, "sarki.mp3")]
cikti = os.path.join(D, "ali-babanin-ciftligi.mp4")
subprocess.run(["ffmpeg", "-y", "-v", "error", *girdi, "-filter_complex", ";".join(filtre),
                "-map", "[v]", "-map", f"{n + len(YAZI)}:a", "-af", f"loudnorm=I=-15:TP=-1.5,afade=in:d=0.3,afade=out:st={SON - 1}:d=1",
                "-t", str(SON), "-c:v", "libx264", "-profile:v", "main", "-level", "4.0", "-preset", "slow", "-crf", "21",
                "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", cikti], check=True)
print("video:", cikti, f"{os.path.getsize(cikti) / 1e6:.1f} MB", f"{sure(cikti):.2f} sn")
