#!/usr/bin/env python3
"""Genel kurgu: şarkının sözcük zamanlarından (ElevenLabs Music yanıtı) kesim listesini kendisi çıkarır.
Her satır başlamadan 0,25 sn önce o satırın sahnesine geçilir; ilk satıra kadar başlık karesi gösterilir.

<klasör>/sozler.json içinde her bölüm için:  satirlar: [...], sahneler: [her satır için kare adı],
  yazi: [her satır için: null | "anahtar" (satır başında 1,7 sn) | [[sıra, "anahtar"(, x, y)], ...]]
        sıra 0,1,2.. = o sözcük söylenirken belirir; -1 = satır başında; 0-1 arası kesir = satırın o oranında. x,y verilirse yazının merkezi oraya konur (1920x1080).
  efekt (isteğe bağlı): [her satır için: null | "kare" (klip yerine duran kare) | "duz" (klip yakınlaştırmasız)]  -> nesnelerin üstüne etiket koymak için
Gerekenler: <klasör>/<şarkı>.mp3 ve .json (sözcük zamanları), kare/<ad>.png, klip/<ad>.mp4, yazi/<anahtar>.png, yazi/baslik.png
Kullanım: python3 kurgu.py <şarkı klasörü> <şarkı adı (örn. deneme_2)> <çıktı adı (örn. banyo-sarkisi)>"""
import json, os, re, subprocess, sys
D = os.path.abspath(sys.argv[1]); SARKI = sys.argv[2]; CIKTI = os.path.join(D, sys.argv[3] + ".mp4")
S = json.load(open(os.path.join(D, "sozler.json"), encoding="utf8")); W = json.load(open(os.path.join(D, SARKI + ".json"), encoding="utf8"))["words_timestamps"]
SES = os.path.join(D, SARKI + ".mp3"); FPS, KLIP_SN = 24, 5.8
SON = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", SES], capture_output=True, text=True).stdout)

# ---- satır zamanları -----------------------------------------------------------------------------------------------
satirlar, i = [], 0
for b in S["bolumler"]:
    for j, satir in enumerate(b["satirlar"]):
        n = len(satir.split()); bas, bit = W[i]["start_ms"] / 1000, W[i + n - 1]["end_ms"] / 1000; i += n
        satirlar.append({"metin": satir, "bas": bas, "bit": bit, "sahne": b["sahneler"][j], "yazi": (b.get("yazi") or [None] * 99)[j], "efekt": (b.get("efekt") or [None] * 99)[j],
                         "soz": [w["start_ms"] / 1000 for w in W[i - n:i]]})
assert i == len(W), (i, len(W))
kes = [max(0.0, s["bas"] - 0.25) for s in satirlar] + [SON]

# ---- sahne ve yazı listesi -------------------------------------------------------------------------------------------
BAS = [0, 1.5, 0.6, 1.0]; EFEKT = ["duz", "yaklas", "uzaklas", "yaklas"]; kullanim = {}
sahne = [("kare:" + S.get("baslik_karesi", satirlar[0]["sahne"]), 0.0, kes[0], 0, "yaklas")]
yazi = [("baslik", 0.4, max(1.2, kes[0] - 0.3), None)]
for k, s in enumerate(satirlar):
    u = kullanim.get(s["sahne"], 0); kullanim[s["sahne"]] = u + 1
    sure = kes[k + 1] - kes[k]
    if s["efekt"] == "kare": sahne.append(("kare:" + s["sahne"], kes[k], kes[k + 1], 0, "duz"))          # duran kare (üstüne etiket konacak)
    elif s["efekt"] == "duz": sahne.append((s["sahne"], kes[k], kes[k + 1], 0, "duz"))                    # klip, yakınlaştırmasız (etiketler yerinde kalsın)
    else: sahne.append((s["sahne"], kes[k], kes[k + 1], BAS[u % 4] if sure <= KLIP_SN - BAS[u % 4] + 0.6 else 0, EFEKT[u % 4]))
    if isinstance(s["yazi"], str): yazi.append((s["yazi"], s["bas"] - 0.1, s["bas"] + 1.6, None))
    elif s["yazi"]:   # [[sıra, anahtar(, x, y)], ...]  sıra: 0,1,2.. = o sözcük söylenirken; -1 = satır başında; 0-1 arası kesir = satırın o oranında
        for oge in s["yazi"]:
            sira, anahtar = oge[0], oge[1]; konum = tuple(oge[2:4]) if len(oge) >= 4 else None
            t0 = kes[k] + 0.05 if sira == -1 else (s["bas"] + sira * (kes[k + 1] - s["bas"]) if isinstance(sira, float) else s["soz"][sira] - 0.08)
            yazi.append((anahtar, t0, kes[k + 1] - 0.03 if konum else min(kes[k + 1] - 0.05, s["bit"] + 0.7), konum))
yazi.append(("baslik", max(satirlar[-1]["bit"] + 0.3, SON - 3.4), SON, None))

girdi, filtre = [], []; n = len(sahne)
for k, (ad, t0, t1, bas, efekt) in enumerate(sahne):
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
    print(f"{t0:6.2f}-{t1:6.2f} {ad:16s} hız {hiz:.2f} dondurma {eksik:.2f} {efekt}")
filtre.append("".join(f"[v{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0[vid]"); son = "vid"
from PIL import Image
import tempfile
GEC = tempfile.mkdtemp(); kirpik = {}
for k, (ad, t0, t1, konum) in enumerate(yazi):
    if ad not in kirpik:                                # yazı resmini dolu kısmına kırp (kaplama hızlı olsun)
        im = Image.open(os.path.join(D, "yazi", ad + ".png")); kutu = im.getbbox(); yol = os.path.join(GEC, ad + ".png"); im.crop(kutu).save(yol); kirpik[ad] = (yol, kutu[0], kutu[1])
    yol, sol, ust = kirpik[ad]
    x, y = (konum[0] - 960 + sol, konum[1] - 190 + ust) if konum else (sol, (-40 if ad == "baslik" else 700) + ust)
    gir, cik = (0.12, 0.12) if konum else (0.25, 0.25)
    girdi += ["-loop", "1", "-t", f"{SON}", "-i", yol]
    filtre.append(f"[{n + k}:v]format=rgba,fade=in:st={t0:.2f}:d={gir}:alpha=1,fade=out:st={t1 - cik:.2f}:d={cik}:alpha=1[y{k}]")
    filtre.append(f"[{son}][y{k}]overlay={x}:{y}:enable='between(t,{t0:.2f},{t1:.2f})'[o{k}]"); son = f"o{k}"
filtre.append(f"[{son}]fade=in:st=0:d=0.4,fade=out:st={SON - 1.0:.2f}:d=1.0[v]")
# ---- ses: -14 LUFS dolayına getir -------------------------------------------------------------------------------------
olc = subprocess.run(["ffmpeg", "-v", "info", "-i", SES, "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True).stderr
I = float(re.findall(r"I:\s+(-?[\d.]+) LUFS", olc)[-1]); kazanc = max(-8.0, min(4.0, -14.2 - I))
girdi += ["-i", SES]
subprocess.run(["ffmpeg", "-y", "-v", "error", *girdi, "-filter_complex", ";".join(filtre), "-map", "[v]", "-map", f"{n + len(yazi)}:a",
                "-af", f"volume={kazanc:.2f}dB,alimiter=limit=0.89:level=disabled,afade=in:d=0.2,afade=out:st={SON - 1.0:.2f}:d=1.0", "-t", f"{SON}",
                "-c:v", "libx264", "-profile:v", "main", "-level", "4.0", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", CIKTI], check=True)
print("video:", CIKTI, f"{os.path.getsize(CIKTI) / 1e6:.1f} MB, {SON:.1f} sn, ses {I:.1f} LUFS -> kazanç {kazanc:+.1f} dB")
