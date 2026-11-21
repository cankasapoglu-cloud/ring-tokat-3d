#!/usr/bin/env python3
"""El Yıkama Şarkısı kurgusu. Ses: ses_kes.py'nin ürettiği sarki_kisa.wav. Her dize bir sahne (yaklaşık 6 sn)."""
import subprocess, os
D = os.path.dirname(os.path.abspath(__file__))
FPS, SON = 24, 66.02
T = [6.02, 11.98, 17.92, 24.00, 29.98, 36.06, 41.96, 47.98, 54.04, 59.98, SON]   # dize başlangıçları
KLIP = ["01_giris", "02_musluk", "03_sabun", "04_avuc", "05_parmak", "06_ust", "07_durula", "08_havlu", "09_temiz", "10_dans"]
YAZI = [("baslik", 0.4, 5.7), ("sir", T[1] + 2.6, T[2] - 0.3), ("kopuk", T[2] + 2.6, T[3] - 0.3), ("fis", T[3] + 2.6, T[4] - 0.3),
        ("fis", T[5] + 2.8, T[6] - 0.3), ("sip", T[6] + 2.4, T[7] - 0.3), ("pat", T[7] + 2.6, T[8] - 0.3), ("piril", T[8] + 2.2, T[9] - 0.3)]
girdi = ["-loop", "1", "-t", f"{T[0]}", "-i", os.path.join(D, "kare", "01_giris.png")]
filtre = [f"[0:v]scale=2304:1296:flags=lanczos,zoompan=z='1+0.0008*on':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={round(T[0] * FPS)}:s=1920x1080:fps={FPS},"
          f"trim=0:{T[0]},setpts=PTS-STARTPTS,setsar=1[v0]"]
for k, ad in enumerate(KLIP):
    hedef = T[k + 1] - T[k] + (0.3 if k == 9 else 0)
    ham = 5.8
    hiz = min(1.15, max(0.85, ham / hedef))
    eksik = max(0.0, hedef - ham / hiz)
    girdi += ["-i", os.path.join(D, "klip", ad + ".mp4")]
    filtre.append(f"[{k + 1}:v]trim=0:{min(ham, hedef * hiz):.3f},setpts=(PTS-STARTPTS)/{hiz:.4f},fps={FPS},scale=1920:1080:flags=lanczos,setsar=1,"
                  f"tpad=stop_mode=clone:stop_duration={eksik + 0.1:.2f},trim=0:{hedef:.3f},setpts=PTS-STARTPTS[v{k + 1}]")
n = 11
filtre.append("".join(f"[v{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0[vid]")
son = "vid"
for k, (ad, t0, t1) in enumerate(YAZI):
    girdi += ["-loop", "1", "-t", f"{SON}", "-i", os.path.join(D, "yazi", ad + ".png")]
    filtre.append(f"[{n + k}:v]format=rgba,fade=in:st={t0:.2f}:d=0.3:alpha=1,fade=out:st={t1 - 0.3:.2f}:d=0.3:alpha=1[y{k}]")
    filtre.append(f"[{son}][y{k}]overlay=0:740:enable='between(t,{t0:.2f},{t1:.2f})'[o{k}]")
    son = f"o{k}"
filtre.append(f"[{son}]fade=in:st=0:d=0.4,fade=out:st={SON - 0.6:.2f}:d=0.6[v]")
girdi += ["-i", os.path.join(D, "sarki_kisa.wav")]
cikti = os.path.join(D, "el-yikama-sarkisi.mp4")
subprocess.run(["ffmpeg", "-y", "-v", "error", *girdi, "-filter_complex", ";".join(filtre),
                "-map", "[v]", "-map", f"{n + len(YAZI)}:a", "-af", f"loudnorm=I=-15:TP=-1.5,afade=in:d=0.3,afade=out:st={SON - 0.5:.2f}:d=0.5",
                "-t", f"{SON}", "-c:v", "libx264", "-profile:v", "main", "-level", "4.0", "-preset", "slow", "-crf", "21",
                "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", cikti], check=True)
print("video:", cikti, f"{os.path.getsize(cikti) / 1e6:.1f} MB")
