#!/usr/bin/env python3
"""Otobüs Şarkısı (Pıtır'ın Otobüsü) kurgusu. Ses: deneme_2.mp3 (onaylanan 2. deneme). Kesimler şarkının sözcük zamanlarına göre
(deneme_2.json): her satır başlamadan yaklaşık 0,25 sn önce sahne değişir.
Kullanım: python3 kurgu.py [çıktı adı]"""
import subprocess, os, sys
D = os.path.dirname(os.path.abspath(__file__))
FPS, SON, KLIP_SN = 24, 95.42, 5.8
# (kaynak, başlangıç, bitiş, klipte başlangıç sn, efekt)   kaynak "kare:<ad>" = duran kare
SAHNE = [("kare:02_kanca_b", 0.0, 3.90, 0, "yaklas"),
         ("01_kanca_a", 3.90, 7.60, 0, "duz"), ("02_kanca_b", 7.60, 11.20, 0, "duz"),                                   # nakarat
         ("03_durak", 11.20, 14.95, 0, "duz"), ("04_kapi", 14.95, 18.60, 0, "duz"), ("03_durak", 18.60, 22.35, 1.5, "yaklas"), ("05_icerde", 22.35, 26.00, 0, "duz"),
         ("06_teker", 26.00, 29.75, 0, "duz"), ("07_direksiyon", 29.75, 33.40, 0, "duz"), ("06_teker", 33.40, 37.10, 1.5, "yaklas"), ("08_yol", 37.10, 40.75, 0, "duz"),
         ("01_kanca_a", 40.75, 44.50, 1.0, "yaklas"), ("02_kanca_b", 44.50, 48.20, 1.2, "uzaklas"),                     # nakarat
         ("09_ordekler", 48.20, 51.85, 0, "duz"), ("10_korna", 51.85, 55.55, 0, "duz"), ("09_ordekler", 55.55, 59.25, 1.5, "yaklas"), ("11_yolver", 59.25, 62.95, 0, "duz"),
         ("12_yagmur", 62.95, 66.65, 0, "duz"), ("13_silecek", 66.65, 70.30, 0, "duz"), ("12_yagmur", 70.30, 74.05, 1.5, "yaklas"), ("14_gokkusagi", 74.05, 77.75, 0, "duz"),
         ("01_kanca_a", 77.75, 81.45, 0.5, "uzaklas"), ("02_kanca_b", 81.45, 85.10, 0.6, "yaklas"),                     # nakarat
         ("15_veda", 85.10, 88.85, 0, "duz"), ("16_guleguler", 88.85, SON, 0, "yaklas")]
YAZI = [("baslik", 0.4, 3.6), ("bin", 4.1, 5.7), ("hop", 11.4, 13.0), ("hop", 18.8, 20.4), ("fir", 26.2, 27.8), ("fir", 33.6, 35.2), ("bin", 41.0, 42.6),
        ("dut", 48.4, 50.0), ("dut", 55.7, 57.3), ("sip", 63.1, 64.7), ("sip", 70.5, 72.1), ("bin", 77.9, 79.5), ("gule", 89.0, 91.5), ("baslik", 92.2, SON)]
CIKTI = os.path.join(D, sys.argv[1] if len(sys.argv) > 1 else "otobus-sarkisi.mp4")
girdi, filtre = [], []; n = len(SAHNE)
for k, (ad, t0, t1, bas, efekt) in enumerate(SAHNE):
    hedef = t1 - t0 + (0.4 if k == n - 1 else 0)
    if efekt == "yaklas": zoom = f"scale=w='2*trunc(960*(1.00+0.08*t/{hedef:.3f}))':h=-2:eval=frame,crop=1920:1080"
    elif efekt == "uzaklas": zoom = f"scale=w='2*trunc(960*(1.08-0.08*t/{hedef:.3f}))':h=-2:eval=frame,crop=1920:1080"
    else: zoom = "scale=1920:1080:flags=lanczos"
    if ad.startswith("kare:"):
        girdi += ["-loop", "1", "-framerate", str(FPS), "-t", f"{hedef:.3f}", "-i", os.path.join(D, "kare", ad[5:] + ".png")]
        filtre.append(f"[{k}:v]scale=1920:1080:flags=lanczos,fps={FPS},setpts=PTS-STARTPTS,{zoom},setsar=1,trim=0:{hedef:.3f},setpts=PTS-STARTPTS[v{k}]"); continue
    ham = KLIP_SN - bas; hiz = min(1.15, max(0.85, ham / hedef)); eksik = max(0.0, hedef - ham / hiz)
    girdi += ["-i", os.path.join(D, "klip", ad + ".mp4")]
    filtre.append(f"[{k}:v]trim={bas}:{bas + min(ham, hedef * hiz):.3f},setpts=(PTS-STARTPTS)/{hiz:.4f},fps={FPS},scale=1920:1080:flags=lanczos,"
                  f"tpad=stop_mode=clone:stop_duration={eksik + 0.1:.2f},trim=0:{hedef:.3f},setpts=PTS-STARTPTS,{zoom},setsar=1[v{k}]")
    print(f"{t0:6.2f}-{t1:6.2f} {ad:14s} hız {hiz:.2f} sonda dondurma {eksik:.2f} {efekt}")
filtre.append("".join(f"[v{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0[vid]"); son = "vid"
for k, (ad, t0, t1) in enumerate(YAZI):
    girdi += ["-loop", "1", "-t", f"{SON}", "-i", os.path.join(D, "yazi", ad + ".png")]
    filtre.append(f"[{n + k}:v]format=rgba,fade=in:st={t0:.2f}:d=0.25:alpha=1,fade=out:st={t1 - 0.25:.2f}:d=0.25:alpha=1[y{k}]")
    filtre.append(f"[{son}][y{k}]overlay=0:{-40 if ad == 'baslik' else 700}:enable='between(t,{t0:.2f},{t1:.2f})'[o{k}]"); son = f"o{k}"
filtre.append(f"[{son}]fade=in:st=0:d=0.4,fade=out:st={SON - 1.0:.2f}:d=1.0[v]")
girdi += ["-i", os.path.join(D, "deneme_2.mp3")]
subprocess.run(["ffmpeg", "-y", "-v", "error", *girdi, "-filter_complex", ";".join(filtre), "-map", "[v]", "-map", f"{n + len(YAZI)}:a",
                "-af", f"volume=-2.4dB,alimiter=limit=0.89:level=disabled,afade=in:d=0.2,afade=out:st={SON - 1.0:.2f}:d=1.0", "-t", f"{SON}",
                "-c:v", "libx264", "-profile:v", "main", "-level", "4.0", "-preset", "slow", "-crf", "21", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", CIKTI], check=True)
print("video:", CIKTI, f"{os.path.getsize(CIKTI) / 1e6:.1f} MB")
