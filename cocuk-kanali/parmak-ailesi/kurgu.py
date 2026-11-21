#!/usr/bin/env python3
"""Parmak Ailesi kurgusu. Her kıta: aile arıyor (soru) -> kukla yakın çekim (cevap) -> aile dansı (ara).
Zamanlar şarkının yazıya dökümünden (sarki_2_words.json) alındı."""
import subprocess, os
D = os.path.dirname(os.path.abspath(__file__))
FPS, SON = 24, 95.04
# Yavaş şarkı (yavas_2.mp3). Kıta: soru + bekleme (aile arıyor) -> cevap (kukla yakın çekim) -> ara (aile dansı)
Q = [6.74, 22.14, 37.54, 52.96, 68.28]      # soru başlangıçları
A = [12.52, 27.92, 43.32, 58.70, 74.10]     # "Buradayım" başlangıçları
KUKLA = ["baba", "anne", "abi", "abla", "bebek"]
VEDA = 82.52
SAHNE = [("kare", 0, 1.8, 0), ("aile_selam", 1.8, Q[0], 0)]
for k in range(5):
    sonraki = Q[k + 1] if k < 4 else VEDA
    SAHNE += [("aile_ara1" if k % 2 == 0 else "aile_ara2", Q[k], A[k], 0), (KUKLA[k], A[k], A[k] + 5.3, 0),
              ("aile_dans", A[k] + 5.3, sonraki, 0)]
SAHNE += [("aile_veda", VEDA, 88.1, 0), ("aile_selam", 88.1, SON, 0)]
YAZI = [("baslik", 0.4, 6.3, 930)] + [(KUKLA[k], A[k], A[k] + 5.1, 120) for k in range(5)]


def sure(f):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f],
                                capture_output=True, text=True, check=True).stdout)


girdi, filtre = [], []
for k, (ad, t0, t1, bas) in enumerate(SAHNE):
    hedef = t1 - t0
    if ad == "kare":
        girdi += ["-loop", "1", "-t", f"{hedef:.3f}", "-i", os.path.join(D, "kare", "00_aile.png")]
        filtre.append(f"[{k}:v]scale=2304:1296,zoompan=z='1+0.0010*on':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={round(hedef * FPS)}:s=1920x1080:fps={FPS},"
                      f"trim=0:{hedef:.3f},setpts=PTS-STARTPTS,setsar=1[v{k}]")
        continue
    f = os.path.join(D, "klip", ad + ".mp4")
    ham = sure(f) - 0.1 - bas
    hiz = min(1.2, max(0.86, ham / hedef))
    eksik = max(0.0, hedef - ham / hiz) + (0.3 if k == len(SAHNE) - 1 else 0)
    ek = f",tpad=stop_mode=clone:stop_duration={eksik:.2f}" if eksik > 0.01 else ""
    girdi += ["-i", f]
    filtre.append(f"[{k}:v]trim={bas}:{bas + min(ham, hedef * hiz):.3f},setpts=(PTS-STARTPTS)/{hiz:.4f},fps={FPS},scale=1920:1080,setsar=1{ek},"
                  f"trim=0:{hedef + (0.3 if k == len(SAHNE) - 1 else 0):.3f},setpts=PTS-STARTPTS[v{k}]")
n = len(SAHNE)
filtre.append("".join(f"[v{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0[vid]")
son = "vid"
for k, (ad, t0, t1, y) in enumerate(YAZI):
    girdi += ["-loop", "1", "-t", f"{SON}", "-i", os.path.join(D, "yazi", ad + ".png")]
    filtre.append(f"[{n + k}:v]format=rgba,fade=in:st={t0}:d=0.3:alpha=1,fade=out:st={t1 - 0.3:.2f}:d=0.3:alpha=1[y{k}]")
    filtre.append(f"[{son}][y{k}]overlay=0:{y - 190}:enable='between(t,{t0},{t1})'[o{k}]")
    son = f"o{k}"
filtre.append(f"[{son}]fade=in:st=0:d=0.4,fade=out:st={SON - 0.7:.2f}:d=0.7[v]")
girdi += ["-i", os.path.join(D, "yavas_2.mp3")]
cikti = os.path.join(D, "parmak-ailesi.mp4")
subprocess.run(["ffmpeg", "-y", "-v", "error", *girdi, "-filter_complex", ";".join(filtre),
                "-map", "[v]", "-map", f"{n + len(YAZI)}:a", "-af", f"loudnorm=I=-15:TP=-1.5,afade=in:d=0.3,afade=out:st={SON - 1:.2f}:d=1",
                "-t", f"{SON}", "-c:v", "libx264", "-profile:v", "main", "-level", "4.0", "-preset", "slow", "-crf", "21",
                "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", cikti], check=True)
print("video:", cikti, f"{os.path.getsize(cikti) / 1e6:.1f} MB", f"{sure(cikti):.2f} sn")
