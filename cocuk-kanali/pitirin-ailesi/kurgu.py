#!/usr/bin/env python3
"""Pıtır'ın Ailesi kurgusu. Her kıta 12 sn: 1. dize aile üyesi selam verir, 2. dize hareketini yapar.
Ses: ses_kes.py'nin ürettiği sarki_kisa.wav (yavas_2.mp3'ün boşlukları kesilmiş hali)."""
import subprocess, os
D = os.path.dirname(os.path.abspath(__file__))
FPS, SON = 24, 84.08
K = [6.08, 18.08, 30.08, 42.08, 54.08, 66.08]        # kıta başlangıçları
D2 = [5.98, 6.28, 6.30, 6.30, 6.32, 6.34]            # kıta içinde 2. dizenin başlangıcı
UYE = ["bebek", "anne", "baba", "nine", "dede"]
KLIP = [("02_bebek", "03_bebek_zipla"), ("04_anne", "05_anne_saril"), ("06_baba", "07_baba_kaldir"),
        ("08_nine", "09_nine_orgu"), ("10_dede", "11_dede_masal")]
# (klip, başlangıç, bitiş, klipte kullanılacak aralık)
SAHNE = [("01_aile", 0, K[0], (0, 4.94))]
for k in range(5):
    a, b = KLIP[k]
    SAHNE.append((a, K[k], K[k] + D2[k], (0, 4.94)))
    if k == 2:   # baba kaldırma klibinde 3.2-4.0 sn arası bozuk: atlanır
        SAHNE += [(b, K[k] + D2[k], K[k] + D2[k] + 4.0, (0, 3.2)), (b, K[k] + D2[k] + 4.0, K[k + 1], (4.0, 4.94))]
    else:
        SAHNE.append((b, K[k] + D2[k], K[k + 1], (0, 4.94)))
SAHNE += [("12_dans", K[5], K[5] + D2[5], (0, 4.94)), ("13_kucak", K[5] + D2[5], 78.3, (0, 4.94)), ("01_aile", 78.3, SON, (0, 4.94))]
YAZI = [("baslik", 0.4, 5.8, 930), ("baslik", 78.8, SON, 930)] + [(UYE[k], K[k] + 0.2, K[k] + D2[k] - 0.3, 930) for k in range(5)]

girdi, filtre = [], []
for k, (ad, t0, t1, (bas, bit)) in enumerate(SAHNE):
    hedef = t1 - t0 + (0.3 if k == len(SAHNE) - 1 else 0)
    ham = bit - bas
    hiz = min(1.2, max(0.8, ham / hedef))
    eksik = max(0.0, hedef - ham / hiz)
    ek = f",tpad=stop_mode=clone:stop_duration={eksik + 0.1:.2f}" if eksik > 0.01 else ""
    girdi += ["-i", os.path.join(D, "klip", ad + ".mp4")]
    filtre.append(f"[{k}:v]trim={bas}:{bas + min(ham, hedef * hiz):.3f},setpts=(PTS-STARTPTS)/{hiz:.4f},fps={FPS},scale=1920:1080,setsar=1{ek},"
                  f"trim=0:{hedef:.3f},setpts=PTS-STARTPTS[v{k}]")
    print(f"{t0:6.2f}-{t1:6.2f} {ad:16s} hız {hiz:.2f} dondurma {eksik:.2f}")
n = len(SAHNE)
filtre.append("".join(f"[v{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0[vid]")
son = "vid"
for k, (ad, t0, t1, y) in enumerate(YAZI):
    girdi += ["-loop", "1", "-t", f"{SON}", "-i", os.path.join(D, "yazi", ad + ".png")]
    filtre.append(f"[{n + k}:v]format=rgba,fade=in:st={t0}:d=0.3:alpha=1,fade=out:st={t1 - 0.3:.2f}:d=0.3:alpha=1[y{k}]")
    filtre.append(f"[{son}][y{k}]overlay=0:{y - 190}:enable='between(t,{t0},{t1})'[o{k}]")
    son = f"o{k}"
filtre.append(f"[{son}]fade=in:st=0:d=0.4,fade=out:st={SON - 0.7:.2f}:d=0.7[v]")
girdi += ["-i", os.path.join(D, "sarki_kisa.wav")]
cikti = os.path.join(D, "pitirin-ailesi.mp4")
subprocess.run(["ffmpeg", "-y", "-v", "error", *girdi, "-filter_complex", ";".join(filtre),
                "-map", "[v]", "-map", f"{n + len(YAZI)}:a", "-af", "loudnorm=I=-15:TP=-1.5,afade=in:d=0.3",
                "-t", f"{SON}", "-c:v", "libx264", "-profile:v", "main", "-level", "4.0", "-preset", "slow", "-crf", "21",
                "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", cikti], check=True)
print("video:", cikti, f"{os.path.getsize(cikti) / 1e6:.1f} MB")
