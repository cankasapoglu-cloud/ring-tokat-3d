#!/usr/bin/env python3
"""Ali Baba'nın Çiftliği (7 kıta) kurgusu. Sahne zamanlarını şarkının kelime dökümünden
(words.json) kendisi çıkarır: her kıtada sunum / hayvan sesi / ara dans sahnesi.
Kullanım: python3 kurgu2.py v2_1   (v2_1.mp3 ve v2_1_words.json kullanılır)"""
import subprocess, os, sys, json
D = os.path.dirname(os.path.abspath(__file__))
AD = sys.argv[1] if len(sys.argv) > 1 else "v2_1"
FPS = 24
# kıta sırası: (yazı adı, sunum klibi, ses klibi, dans klibi)
KITA = [("inek", 2, 3, 4), ("koyun", 5, 6, 7), ("at", 16, 17, 18), ("horoz", 19, 20, 21),
        ("ordek", 8, 9, 10), ("kopek", 11, 12, 13), ("kedi", 14, 15, 1)]   # kapanışta giriş sahnesi yeniden kullanılır


def sure(f):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f],
                                capture_output=True, text=True, check=True).stdout)


w = json.load(open(os.path.join(D, AD + "_words.json"), encoding="utf8"))
w = w["words"] if isinstance(w, dict) else w
w = [x for x in w if x.get("type", "word") == "word"]
t = lambda x: x["text"].lower().strip('".,!? ')
bas = [i for i in range(len(w) - 2) if t(w[i]) == "ali" and t(w[i + 1]).startswith("baba") and t(w[i + 2]) == "bir"]
assert len(bas) == len(KITA), f"{len(bas)} kıta bulundu, {len(KITA)} bekleniyordu"
SON = sure(os.path.join(D, AD + ".mp3"))
sahne, yazi = [], []          # (klip no | 'kare', t0, t1)
giris = w[bas[0]]["start"]
if giris > 5.6:
    sahne.append(("kare", 0, giris - 4.94)); sahne.append((1, giris - 4.94, giris))
else:
    sahne.append((1, 0, giris))
yazi.append(("baslik", 0.5, giris - 0.4, 150))
for k, (ad, ka, kb, kc) in enumerate(KITA):
    i0, i1 = bas[k], (bas[k + 1] if k + 1 < len(bas) else len(w))
    kelime = w[i0:i1]
    vs, ve = kelime[0]["start"], kelime[-1]["end"]
    varlar = [x for x in kelime if t(x) == "var"]
    ses = (varlar[1]["end"] + 0.1) if len(varlar) >= 2 else vs + (ve - vs) * 0.5
    sonraki = w[i1]["start"] if i1 < len(w) else SON
    sahne.append((ka, vs, ses))
    if kc and sonraki - ve >= 2.5:
        sahne.append((kb, ses, ve + 0.15)); sahne.append((kc, ve + 0.15, sonraki))
    else:
        sahne.append((kb, ses, sonraki))
    yazi.append((ad, ses, ve, 120))
for s in sahne:
    print(f"  {str(s[0]):>4}  {s[1]:6.2f} - {s[2]:6.2f}  ({s[2] - s[1]:.2f} sn)")

girdi, filtre = [], []
for k, (no, t0, t1) in enumerate(sahne):
    hedef = t1 - t0
    if no == "kare":
        girdi += ["-loop", "1", "-t", f"{hedef:.3f}", "-i", os.path.join(D, "kare", "01.png")]
        filtre.append(f"[{k}:v]scale=2304:1296,zoompan=z='1+0.0010*on':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={round(hedef * FPS)}:s=1920x1080:fps={FPS},"
                      f"trim=0:{hedef:.3f},setpts=PTS-STARTPTS,setsar=1[v{k}]")
        continue
    f = os.path.join(D, "klip", f"{no:02d}.mp4")
    ham = sure(f) - 0.1
    hiz = min(1.25, max(0.88, ham / hedef))
    eksik = max(0.0, hedef - ham / hiz) + (0.3 if k == len(sahne) - 1 else 0)     # klip yetmezse son kareyi dondur
    ek = f",tpad=stop_mode=clone:stop_duration={eksik:.2f}" if eksik > 0.01 else ""
    girdi += ["-i", f]
    filtre.append(f"[{k}:v]trim=0:{min(ham, hedef * hiz):.3f},setpts=(PTS-STARTPTS)/{hiz:.4f},fps={FPS},scale=1920:1080,setsar=1{ek},trim=0:{hedef + (0.3 if k == len(sahne) - 1 else 0):.3f}[v{k}]")
n = len(sahne)
filtre.append("".join(f"[v{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0[vid]")
son = "vid"
for k, (ad, t0, t1, y) in enumerate(yazi):
    girdi += ["-loop", "1", "-t", f"{SON:.2f}", "-i", os.path.join(D, "yazi", ad + ".png")]
    filtre.append(f"[{n + k}:v]format=rgba,fade=in:st={t0:.2f}:d=0.3:alpha=1,fade=out:st={t1 - 0.3:.2f}:d=0.3:alpha=1[y{k}]")
    filtre.append(f"[{son}][y{k}]overlay=0:{y - 190}:enable='between(t,{t0:.2f},{t1:.2f})'[o{k}]")
    son = f"o{k}"
filtre.append(f"[{son}]fade=in:st=0:d=0.4,fade=out:st={SON - 0.7:.2f}:d=0.7[v]")
girdi += ["-i", os.path.join(D, AD + ".mp3")]
cikti = os.path.join(D, "ali-babanin-ciftligi-7-hayvan.mp4")
subprocess.run(["ffmpeg", "-y", "-v", "error", *girdi, "-filter_complex", ";".join(filtre),
                "-map", "[v]", "-map", f"{n + len(yazi)}:a", "-af", f"loudnorm=I=-15:TP=-1.5,afade=in:d=0.3,afade=out:st={SON - 1:.2f}:d=1",
                "-t", f"{SON:.2f}", "-c:v", "libx264", "-profile:v", "main", "-level", "4.0", "-preset", "slow", "-crf", "22",
                "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", cikti], check=True)
print("video:", cikti, f"{os.path.getsize(cikti) / 1e6:.1f} MB", f"{sure(cikti):.2f} sn")
