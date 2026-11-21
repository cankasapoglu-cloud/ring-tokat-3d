#!/usr/bin/env python3
"""El Yıkama Şarkısı kurgusu. Ses: coskulu_2.mp3 (hareketli sürüm, kesilmeden). Zamanlar yazıya dökümden."""
import subprocess, os
D = os.path.dirname(os.path.abspath(__file__))
FPS, SON = 24, 70.0
# (klip, başlangıç, bitiş, klipte başlangıç sn, baştaki ilk kareyi bekletme sn)
SAHNE = [("01_giris", 0, 10.0, 0, 3.2), ("02_musluk", 10.0, 20.28, 0, 3.5), ("03_sabun", 20.28, 25.5, 0, 0),
         ("05_parmak", 25.5, 32.56, 0, 0), ("04_avuc", 32.56, 36.6, 0, 0), ("05_parmak", 36.6, 40.74, 1.5, 0),
         ("06_ust", 40.74, 44.72, 0.8, 0), ("03_sabun", 44.72, 48.66, 1.6, 0), ("07_durula", 48.66, 52.84, 0, 0),
         ("08_havlu", 52.84, 56.98, 0, 0), ("09_temiz", 56.98, 61.0, 0, 0), ("10_dans", 61.0, SON, 0, 0)]
YAZI = [("baslik", 0.4, 7.5), ("sir", 18.1, 20.1), ("kopuk", 22.5, 25.3), ("fis", 34.5, 36.4), ("fis", 43.1, 44.7),
        ("kopuk", 46.9, 48.5), ("sip", 50.7, 52.6), ("pat", 54.8, 56.8), ("piril", 58.6, 60.8)]
girdi, filtre = [], []
n = len(SAHNE)
for k, (ad, t0, t1, bas, on) in enumerate(SAHNE):
    hedef = t1 - t0 + (0.3 if k == n - 1 else 0)
    ham = 5.8 - bas
    hiz = min(1.15, max(0.85, ham / (hedef - on)))
    eksik = max(0.0, hedef - on - ham / hiz)
    girdi += ["-i", os.path.join(D, "klip", ad + ".mp4")]
    onf = f"tpad=start_mode=clone:start_duration={on}," if on else ""
    filtre.append(f"[{k}:v]trim={bas}:{bas + min(ham, (hedef - on) * hiz):.3f},setpts=(PTS-STARTPTS)/{hiz:.4f},fps={FPS},scale=1920:1080:flags=lanczos,setsar=1,"
                  f"{onf}tpad=stop_mode=clone:stop_duration={eksik + 0.1:.2f},trim=0:{hedef:.3f},setpts=PTS-STARTPTS[v{k}]")
    print(f"{t0:6.2f}-{t1:6.2f} {ad:10s} hız {hiz:.2f} sonda dondurma {eksik:.2f}")
filtre.append("".join(f"[v{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0[vid]")
son = "vid"
for k, (ad, t0, t1) in enumerate(YAZI):
    girdi += ["-loop", "1", "-t", f"{SON}", "-i", os.path.join(D, "yazi", ad + ".png")]
    filtre.append(f"[{n + k}:v]format=rgba,fade=in:st={t0:.2f}:d=0.25:alpha=1,fade=out:st={t1 - 0.25:.2f}:d=0.25:alpha=1[y{k}]")
    filtre.append(f"[{son}][y{k}]overlay=0:740:enable='between(t,{t0:.2f},{t1:.2f})'[o{k}]")
    son = f"o{k}"
filtre.append(f"[{son}]fade=in:st=0:d=0.4,fade=out:st={SON - 1.0:.2f}:d=1.0[v]")
girdi += ["-i", os.path.join(D, "coskulu_2.mp3")]
cikti = os.path.join(D, "el-yikama-sarkisi.mp4")
subprocess.run(["ffmpeg", "-y", "-v", "error", *girdi, "-filter_complex", ";".join(filtre),
                "-map", "[v]", "-map", f"{n + len(YAZI)}:a", "-af", f"loudnorm=I=-15:TP=-1.5,afade=in:d=0.3,afade=out:st={SON - 1.0:.2f}:d=1.0",
                "-t", f"{SON}", "-c:v", "libx264", "-profile:v", "main", "-level", "4.0", "-preset", "slow", "-crf", "21",
                "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", cikti], check=True)
print("video:", cikti, f"{os.path.getsize(cikti) / 1e6:.1f} MB")
