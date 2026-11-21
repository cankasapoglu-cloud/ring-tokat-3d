#!/usr/bin/env python3
"""Ali Baba'nın Çiftliği — ONAYLANAN şarkı için video kurgusu (yeni7: Old MacDonald ezgisi, boşluksuz düzen).
Zamanlar yeni7/altyapi/zaman_G.json'dan okunur. Kıta: satır 1 | satır 2 | iki gerçek hayvan sesi | "diye bağırır" | satır 4 | 2 ölçü çalgı arası.
  satır 1 (ve bir önceki aranın son ölçüsü): Ali Baba ile Pıtır      satır 2: hayvan tanıtılır      hayvan sesi: ses klibi
  "diye bağırır" + satır 4: dans                                      çalgı arasının ilk ölçüsü: hayvan
Kullanım: python3 kurgu5.py [ses dosyası] [çıktı adı] [zaman json]"""
import json, subprocess, os, sys
D = os.path.dirname(os.path.abspath(__file__))
SES = sys.argv[1] if len(sys.argv) > 1 else os.path.join(D, "yeni7", "sarki_OM.mp3")
CIKTI = os.path.join(D, sys.argv[2] if len(sys.argv) > 2 else "ali-babanin-ciftligi.mp4")
Z = json.load(open(sys.argv[3] if len(sys.argv) > 3 else os.path.join(D, "yeni7", "altyapi", "zaman_G.json"), encoding="utf8"))
FPS, KLIP_SN = 24, 4.94
SON, K, BIT, B = Z["dosya_suresi_sn"], Z["kitalar"], Z["bitis"]["baslangic"], Z["olcu_sn"]
# kıta sırası: (yazı adı, tanıtım klibi, ses klibi, dans klibi)
KITA = [("inek", 2, 3, 4), ("koyun", 5, 6, 7), ("at", 16, 17, 18), ("horoz", 19, 20, 21),
        ("ordek", 8, 9, 10), ("kopek", 11, 12, 13), ("kedi", 14, 15, None)]
# sahne: (kaynak, t0, t1, kaynakta başlangıç sn, efekt)   kaynak: klip no | "kare"
sahne = [("kare", 0.0, B, 0, "yaklas"), (1, B, K[0]["satir2"]["baslangic"], 0, "duz")]      # giriş: başlık, sonra Ali Baba ve Pıtır (1. kıtanın ilk satırıyla)
yazi = [("baslik", 0.4, K[0]["satir1"]["baslangic"] - 0.3, 150)]
for k, (ad, ks, kses, kd) in enumerate(KITA):
    v = K[k]; s2, h1, dy, s4 = v["satir2"]["baslangic"], v["hayvan_sesi"]["ses1_baslangic"], v["diye_bagirir"]["baslangic"], v["satir4"]["baslangic"]
    a0, a1 = v["ara"]["baslangic"], v["ara"]["bitis"]; orta = (a0 + a1) / 2
    sahne.append((ks, s2, h1, 0, "duz"))                                        # hayvan tanıtılır
    sahne.append((kses, h1, dy, 0, "duz"))                                      # gerçek hayvan sesi (iki kez)
    if kd:
        sahne.append((kd, dy, a0, 0, "duz"))                                    # "diye bağırır çiftliğinde Ali Baba'nın": dans
        sahne.append((ks, a0, orta, 2.5, "duz"))                                # çalgı arası: hayvan
    else:                                                                       # kedinin dans klibi yok
        sahne.append((ks, dy, s4, 2.5, "duz")); sahne.append((kses, s4, a0, 2.4, "yaklas")); sahne.append((ks, a0, orta, 0.3, "duz"))
    sonraki = K[k + 1]["satir2"]["baslangic"] if k < len(KITA) - 1 else BIT
    sahne.append((1, orta, sonraki, 0, "yaklas" if k % 2 else "uzaklas"))       # aranın sonu + sıradaki kıtanın ilk satırı: Ali Baba ve Pıtır
    yazi.append((ad, s2 + 0.1, dy - 0.1, 120))
t = BIT                                                                         # bitiş: yedi hayvandan yarım ölçülük görüntüler, sonra Ali Baba ve Pıtır
for (ad, ks, kses, kd) in KITA:
    sahne.append((kd or kses, t, t + B / 2, 1.6, "duz")); t += B / 2
sahne.append((1, t, SON, 0.6, "yaklas")); yazi.append(("baslik", t + 0.1, SON, 150))


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
