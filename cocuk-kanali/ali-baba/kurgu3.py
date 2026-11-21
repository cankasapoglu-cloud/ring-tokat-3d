#!/usr/bin/env python3
"""Ali Baba'nın Çiftliği — yeni şarkı düzenine göre video kurgusu (105 vuruş/dk, 64 ölçü).
Şarkı düzeni (yeni4): 0,100 sn ön boşluk; giriş 4 ölçü; 7 kıta x 8 ölçü; bitiş 4 ölçü; 2,5 sn kuyruk.
Kıta içi ölçüler: 0 = "Ali Baba'nın bir çiftliği var", 1 = trompet cevabı, 2 = "çiftliğinde ... var",
3-4 = gerçek hayvan sesi (iki kez), 5 = davul geçişi + "diye bağırır", 6 = "çiftliğinde Ali Baba'nın", 7 = trompet cevabı.

Kullanım: python3 kurgu3.py <ses dosyası> [çıktı adı]
  örn.  python3 kurgu3.py yeni4/mix/sarki_dogal.mp3 ali-babanin-ciftligi-yeni.mp4
"""
import subprocess, os, sys
D = os.path.dirname(os.path.abspath(__file__))
SES = sys.argv[1] if len(sys.argv) > 1 else os.path.join(D, "yeni4", "mix", "sarki_dogal.mp3")
CIKTI = os.path.join(D, sys.argv[2] if len(sys.argv) > 2 else "ali-babanin-ciftligi-yeni.mp4")
FPS, ON, B = 24, 0.100, 240 / 105.0
olcu = lambda n: ON + n * B                      # n. ölçünün başı (sn)
SON = olcu(64) + 2.5
KLIP_SN = 4.94                                   # kliplerin kullanılabilir süresi
# kıta sırası: (yazı adı, sunum klibi, ses klibi, dans klibi)
KITA = [("inek", 2, 3, 4), ("koyun", 5, 6, 7), ("at", 16, 17, 18), ("horoz", 19, 20, 21),
        ("ordek", 8, 9, 10), ("kopek", 11, 12, 13), ("kedi", 14, 15, None)]

# sahne: (kaynak, t0, t1, kaynakta başlangıç sn, efekt)   kaynak: klip no | "kare"
sahne = [("kare", 0.0, olcu(2), 0, "yaklas"), (1, olcu(2), olcu(4), 0, "duz")]
yazi = [("baslik", 0.4, olcu(2) - 0.2, 150)]
for k, (ad, ks, kses, kd) in enumerate(KITA):
    s = 4 + 8 * k
    sahne.append((1, olcu(s), olcu(s + 2), 0, "yaklas" if k % 2 == 0 else "uzaklas"))   # Ali Baba ve Pıtır
    sahne.append((ks, olcu(s + 2), olcu(s + 3), 0, "duz"))                               # hayvan tanıtılır
    sahne.append((kses, olcu(s + 3), olcu(s + 5), 0, "duz"))                             # hayvan sesi (iki kez)
    if kd:
        sahne.append((kd, olcu(s + 5), olcu(s + 7), 0, "duz"))                           # dans
        sahne.append((ks, olcu(s + 7), olcu(s + 8), 2.5, "duz"))                         # tanıtımın ikinci yarısı
    else:                                                                                 # kedinin dans klibi yok
        sahne.append((ks, olcu(s + 5), olcu(s + 6), 2.5, "duz"))
        sahne.append((1, olcu(s + 6), olcu(s + 8), 0, "uzaklas"))
    yazi.append((ad, olcu(s + 2) + 0.1, olcu(s + 5) - 0.1, 120))
# bitiş: yedi hayvandan yarım ölçülük kısa görüntüler, sonra Ali Baba ve Pıtır
t = olcu(60)
for (ad, ks, kses, kd) in KITA:
    sahne.append((kd or kses, t, t + B / 2, 1.6, "duz")); t += B / 2
sahne.append((1, t, SON, 0.6, "yaklas"))
yazi.append(("baslik", t + 0.1, SON, 150))


def sure(f):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f],
                                capture_output=True, text=True, check=True).stdout)


girdi, filtre = [], []
n = len(sahne)
for k, (no, t0, t1, bas, efekt) in enumerate(sahne):
    hedef = t1 - t0 + (0.4 if k == n - 1 else 0)
    kare_say = max(1, round(hedef * FPS))
    if efekt == "yaklas":
        zoom = f"scale=w='2*trunc(960*(1.00+0.10*t/{hedef:.3f}))':h=-2:eval=frame,crop=1920:1080"
    elif efekt == "uzaklas":
        zoom = f"scale=w='2*trunc(960*(1.10-0.10*t/{hedef:.3f}))':h=-2:eval=frame,crop=1920:1080"
    else:
        zoom = "scale=1920:1080"
    if no == "kare":
        girdi += ["-loop", "1", "-framerate", str(FPS), "-t", f"{hedef:.3f}", "-i", os.path.join(D, "kare", "01.png")]
        filtre.append(f"[{k}:v]scale=1920:1080,fps={FPS},setpts=PTS-STARTPTS,{zoom},setsar=1,trim=0:{hedef:.3f},setpts=PTS-STARTPTS[v{k}]")
        continue
    f = os.path.join(D, "klip", f"{no:02d}.mp4")
    ham = KLIP_SN - bas
    hiz = min(1.15, max(0.85, ham / hedef))
    eksik = max(0.0, hedef - ham / hiz)
    ek = f",tpad=stop_mode=clone:stop_duration={eksik + 0.1:.2f}" if eksik > 0.01 else ""
    girdi += ["-i", f]
    filtre.append(f"[{k}:v]trim={bas}:{bas + min(ham, hedef * hiz):.3f},setpts=(PTS-STARTPTS)/{hiz:.4f},fps={FPS},scale=1920:1080{ek},"
                  f"trim=0:{hedef:.3f},setpts=PTS-STARTPTS,{zoom},setsar=1[v{k}]")
    print(f"{t0:7.2f}-{t1:7.2f}  {str(no):>4}  hız {hiz:.2f}  dondurma {eksik:.2f}  {efekt}")
filtre.append("".join(f"[v{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0[vid]")
son = "vid"
for k, (ad, t0, t1, y) in enumerate(yazi):
    girdi += ["-loop", "1", "-t", f"{SON:.2f}", "-i", os.path.join(D, "yazi", ad + ".png")]
    filtre.append(f"[{n + k}:v]format=rgba,fade=in:st={t0:.2f}:d=0.25:alpha=1,fade=out:st={t1 - 0.25:.2f}:d=0.25:alpha=1[y{k}]")
    filtre.append(f"[{son}][y{k}]overlay=0:{y - 190}:enable='between(t,{t0:.2f},{t1:.2f})'[o{k}]")
    son = f"o{k}"
filtre.append(f"[{son}]fade=in:st=0:d=0.3,fade=out:st={SON - 1.2:.2f}:d=1.2[v]")
girdi += ["-i", SES]
subprocess.run(["ffmpeg", "-y", "-v", "error", *girdi, "-filter_complex", ";".join(filtre),
                "-map", "[v]", "-map", f"{n + len(yazi)}:a", "-af", f"afade=out:st={SON - 1.0:.2f}:d=1.0",
                "-t", f"{SON:.2f}", "-c:v", "libx264", "-profile:v", "main", "-level", "4.0", "-preset", "slow", "-crf", "21",
                "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", CIKTI], check=True)
print("video:", CIKTI, f"{os.path.getsize(CIKTI) / 1e6:.1f} MB", f"{sure(CIKTI):.2f} sn")
