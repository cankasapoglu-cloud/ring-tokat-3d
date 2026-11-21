#!/usr/bin/env python3
"""Beş Küçük Maymun kurgusu. Kıta başına: N maymun zıplıyor -> biri düştü -> anne arıyor -> doktor.
Düşme, anne ve doktor klipleri her kıtada (farklı yerinden) yeniden kullanılır."""
import subprocess, os
D = os.path.dirname(os.path.abspath(__file__))
FPS, OLCU = 24, 2.19
SON = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", os.path.join(D, "sarki_kisa.wav")],
                           capture_output=True, text=True, check=True).stdout)
T = [2 * OLCU + k * 6 * OLCU for k in range(5)]          # kıta başlangıçları
E = T[4] + 6 * OLCU                                       # ninni bölümü
ZIPLA = ["02_bes", "03_dort", "04_uc", "05_iki", "06_bir"]
# (klip, başlangıç, bitiş, klibin içinden başlama sn, hız; None = otomatik)
S = [("01_giris", 0, T[0], 0.4, None), (ZIPLA[0], T[0], T[0] + 2.2, 0.3, 1.0)]
for k in range(5):
    t, cift = T[k], k % 2
    S += [("07_dustu", t + 2.2, t + 4.42, 2.4 if cift else 0.0, 1.0),
          ("08_anne", t + 4.42, t + 6.5, 2.6 if cift else 0.2, 1.0),
          ("09_doktor", t + 6.5, t + 9.7, 1.6 if cift else 0.0, 1.0)]
    if k < 4:
        S.append((ZIPLA[k + 1], t + 9.7, T[k + 1] + 2.2, 0, None))      # kalan maymunlar zıplamaya devam eder
    else:
        S.append(("08_anne", t + 9.7, E, 1.4, 1.0))
S.append(("10_uyku", E, SON, 0, 0.62))                                  # ninni: ağır çekim uyku
YAZI = [("baslik", 0.4, T[0] - 0.3, 930, 0)] + [(f"s{5 - k}", T[k] + 0.1, T[k] + 2.2, 210, 620) for k in range(5)]


def sure(f):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f],
                                capture_output=True, text=True, check=True).stdout)


girdi, filtre = [], []
for k, (ad, t0, t1, bas, hiz) in enumerate(S):
    f = os.path.join(D, "klip", ad + ".mp4")
    hedef, ham = t1 - t0, sure(f) - 0.1 - bas
    if hiz is None:
        hiz = min(1.2, max(0.86, ham / hedef))
    son = k == len(S) - 1
    eksik = max(0.0, hedef - ham / hiz) + (0.3 if son else 0)
    ek = f",tpad=stop_mode=clone:stop_duration={eksik:.2f}" if eksik > 0.01 else ""
    girdi += ["-i", f]
    filtre.append(f"[{k}:v]trim={bas}:{bas + min(ham, hedef * hiz):.3f},setpts=(PTS-STARTPTS)/{hiz:.4f},fps={FPS},scale=1920:1080,setsar=1{ek},"
                  f"trim=0:{hedef + (0.3 if son else 0):.3f},setpts=PTS-STARTPTS[v{k}]")
n = len(S)
filtre.append("".join(f"[v{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0[vid]")
son = "vid"
for k, (ad, t0, t1, y, x) in enumerate(YAZI):
    girdi += ["-loop", "1", "-t", f"{SON:.2f}", "-i", os.path.join(D, "yazi", ad + ".png")]
    filtre.append(f"[{n + k}:v]format=rgba,fade=in:st={t0:.2f}:d=0.25:alpha=1,fade=out:st={t1 - 0.25:.2f}:d=0.25:alpha=1[y{k}]")
    filtre.append(f"[{son}][y{k}]overlay={x}:{y - 190}:enable='between(t,{t0:.2f},{t1:.2f})'[o{k}]")
    son = f"o{k}"
filtre.append(f"[{son}]fade=in:st=0:d=0.4,fade=out:st={SON - 1.5:.2f}:d=1.5[v]")
girdi += ["-i", os.path.join(D, "sarki_kisa.wav")]
cikti = os.path.join(D, "bes-kucuk-maymun.mp4")
subprocess.run(["ffmpeg", "-y", "-v", "error", *girdi, "-filter_complex", ";".join(filtre),
                "-map", "[v]", "-map", f"{n + len(YAZI)}:a", "-af", "loudnorm=I=-15:TP=-1.5,afade=in:d=0.3",
                "-t", f"{SON:.2f}", "-c:v", "libx264", "-profile:v", "main", "-level", "4.0", "-preset", "slow", "-crf", "21",
                "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", cikti], check=True)
print("video:", cikti, f"{os.path.getsize(cikti) / 1e6:.1f} MB", f"{sure(cikti):.2f} sn")
