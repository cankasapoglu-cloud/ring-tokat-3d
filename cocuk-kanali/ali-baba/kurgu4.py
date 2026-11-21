#!/usr/bin/env python3
"""Ali Baba'nın Çiftliği — ilk kaydın yerinde düzeltilmiş sesi (yeni5/sarki_duzeltilmis) için video kurgusu.
Zamanlar yeni5/zaman.json'dan okunur. Kıta içi ölçüler (her biri 2,286 sn):
  ö0 "Ali Baba'nın bir çiftliği var"   ö1 "çiftliğinde ... var"   ö2-ö3 gerçek hayvan sesi (iki kez)
  ö4 "diye bağırır"   ö5 "çiftliğinde Ali Baba'nın"   ö6-ö7 çalgı arası
Kullanım: python3 kurgu4.py [ses dosyası] [çıktı adı]"""
import json, subprocess, os, sys
D = os.path.dirname(os.path.abspath(__file__))
SES = sys.argv[1] if len(sys.argv) > 1 else os.path.join(D, "yeni5", "sarki_duzeltilmis.mp3")
CIKTI = os.path.join(D, sys.argv[2] if len(sys.argv) > 2 else "ali-babanin-ciftligi-duzeltilmis.mp4")
Z = json.load(open(os.path.join(D, "yeni5", "zaman.json"), encoding="utf8"))
FPS, SON, KLIP_SN = 24, Z["sure_sn"], 4.94
# kıta sırası: (yazı adı, tanıtım klibi, ses klibi, dans klibi)
KITA = [("inek", 2, 3, 4), ("koyun", 5, 6, 7), ("at", 16, 17, 18), ("horoz", 19, 20, 21),
        ("ordek", 8, 9, 10), ("kopek", 11, 12, 13), ("kedi", 14, 15, None)]
K = Z["kitalar"]
# sahne: (kaynak, t0, t1, kaynakta başlangıç sn, efekt)   kaynak: klip no | "kare"
ilk = K[0]["olcu_baslari"]
sahne = [("kare", 0.0, 4.0, 0, "yaklas"), (1, 4.0, ilk[1], 0, "duz")]          # giriş + 1. kıtanın ilk dizesi: Ali Baba ve Pıtır
yazi = [("baslik", 0.4, 3.8, 150)]
for k, (ad, ks, kses, kd) in enumerate(KITA):
    ob = K[k]["olcu_baslari"]; bar = Z["olcu_sn"]
    sonraki = K[k + 1]["olcu_baslari"][1] if k < 6 else SON                     # çalgı arasının sonu + sıradaki kıtanın ilk dizesi
    sahne.append((ks, ob[1], ob[2], 0, "duz"))                                  # hayvan tanıtılır
    sahne.append((kses, ob[2], ob[4], 0, "duz"))                                # gerçek hayvan sesi (iki kez)
    if kd:
        sahne.append((kd, ob[4], ob[6], 0, "duz"))                              # "diye bağırır, çiftliğinde Ali Baba'nın": dans
    else:                                                                       # kedinin dans klibi yok
        sahne.append((ks, ob[4], ob[5], 2.5, "duz")); sahne.append((kses, ob[5], ob[6], 2.4, "yaklas"))
    sahne.append((ks, ob[6], ob[7], 2.5 if kd else 0.3, "duz"))                 # çalgı arası: hayvan
    sahne.append((1, ob[7], sonraki, 0, "yaklas" if k % 2 else "uzaklas"))      # çalgı arası sonu + sıradaki dize: Ali Baba ve Pıtır
    yazi.append((ad, ob[1] + 0.1, ob[4] - 0.1, 120))
yazi.append(("baslik", K[6]["olcu_baslari"][7] + 0.2, SON, 150))


def sure(f):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f],
                                capture_output=True, text=True, check=True).stdout)


girdi, filtre = [], []
n = len(sahne)
for k, (no, t0, t1, bas, efekt) in enumerate(sahne):
    hedef = t1 - t0 + (0.4 if k == n - 1 else 0)
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
    hiz = min(1.15, max(0.80, ham / hedef))
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
filtre.append(f"[{son}]fade=in:st=0:d=0.3,fade=out:st={SON - 0.8:.2f}:d=0.8[v]")
girdi += ["-i", SES]
subprocess.run(["ffmpeg", "-y", "-v", "error", *girdi, "-filter_complex", ";".join(filtre),
                "-map", "[v]", "-map", f"{n + len(yazi)}:a", "-af", f"afade=out:st={SON - 0.5:.2f}:d=0.5",
                "-t", f"{SON:.2f}", "-c:v", "libx264", "-profile:v", "main", "-level", "4.0", "-preset", "slow", "-crf", "21",
                "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", CIKTI], check=True)
print("video:", CIKTI, f"{os.path.getsize(CIKTI) / 1e6:.1f} MB", f"{sure(CIKTI):.2f} sn")
