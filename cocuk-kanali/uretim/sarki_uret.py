#!/usr/bin/env python3
"""Şarkı üretimi (genel): ElevenLabs Music ile üretim. Sözler bölüm bölüm ve süreleriyle verilir (composition_plan, music_v2_5),
böylece model sözleri değiştiremez ve şarkı uzayıp boşluk bırakamaz. Yanıttaki sözcük zamanları da kaydedilir.

Kullanım: python3 sarki_uret.py <şarkı klasörü> <çıktı adı> <stil kümesi: tr | en | en+ (sozler.json içindeki ek_stil eklenir)> [tohum]
  <klasör>/sozler.json okunur; çıktı: <ad>.mp3, <ad>.json (plan + sözcük zamanları), <ad>.plan.json (gönderilen istek)
API anahtarı ağ geçidinde eklenir (başlıktaki değer yer tutucudur)."""
import json, os, subprocess, sys
D = os.path.abspath(sys.argv[1])
AD, STIL = sys.argv[2], sys.argv[3]; TOHUM = int(sys.argv[4]) if len(sys.argv) > 4 else None
S = json.load(open(os.path.join(D, "sozler.json"), encoding="utf8"))
STILLER = {
    "tr": (["coşkulu Türkçe çocuk şarkısı", "hızlı tempo, dakikada 130 vuruş", "neşeli ve enerjik kadın vokal", "net ve doğal Türkçe telaffuz",
            "ukulele, alkış, tef, zıplayan bas, canlı davul", "glockenspiel", "nakaratta çocuk korosu", "zıplatan, dans ettiren, birlikte söylenen",
            "yüksek prodüksiyon kalitesi"], ["ninni", "yavaş", "hüzünlü"]),
    "en": (["upbeat Turkish children's song", "fast, 130 BPM", "energetic joyful female lead vocal, native Turkish singer", "clear natural Turkish pronunciation",
            "ukulele, hand claps, tambourine, bouncy bass, live drums", "glockenspiel", "kids choir on the chorus", "sing-along, danceable, bouncy",
            "great production quality"], ["lullaby", "slow", "ballad", "foreign accent"]),
}
EK = STIL.endswith("+"); STIL = STIL.rstrip("+")
poz, neg = STILLER[STIL]
if EK: poz = poz + S.get("ek_stil", [])
chunks = [{"text": "[Instrumental Intro]", "duration_ms": S.get("giris_ms", 4000), "positive_styles": poz, "negative_styles": neg}]
for b in S["bolumler"]:
    chunks.append({"text": f"[{b['etiket']}]\n" + "\n".join(b["satirlar"]), "duration_ms": b["sure_ms"],
                   "positive_styles": poz[:4] + b.get("stiller_" + STIL, []), "negative_styles": neg})
chunks.append({"text": "[Instrumental Outro]", "duration_ms": S.get("bitis_ms", 3000), "positive_styles": [("kısa, neşeli bitiş, son vuruş" if STIL == "tr" else "short happy ending, final hit")], "negative_styles": neg})
istek = {"model_id": S.get("model", "music_v2_5"), "composition_plan": {"chunks": chunks}, "with_timestamps": True}
if TOHUM is not None: istek["seed"] = TOHUM
P = os.path.join(D, AD); json.dump(istek, open(P + ".plan.json", "w", encoding="utf8"), ensure_ascii=False, indent=1)
print("toplam süre %.1f sn, bölüm %d" % (sum(c["duration_ms"] for c in chunks) / 1000, len(chunks)))
r = subprocess.run(["curl", "-sS", "-m", "900", "-X", "POST", "https://api.elevenlabs.io/v1/music/detailed?output_format=mp3_48000_192",
                    "-H", "xi-api-key: proxy-injected", "-H", "Content-Type: application/json", "--data-binary", "@" + P + ".plan.json",
                    "-D", P + ".basliklar.txt", "-o", P + ".yanit.bin", "-w", "%{http_code}"], capture_output=True, text=True)
kod = r.stdout.strip(); govde = open(P + ".yanit.bin", "rb").read(); bas = open(P + ".basliklar.txt", encoding="latin1").read()
if kod != "200": print("HATA", kod, govde[:600].decode("utf8", "replace")); sys.exit(1)
ct = [l for l in bas.splitlines() if l.lower().startswith("content-type:")][-1]; sinir = ct.split("boundary=")[1].strip().strip('"').encode()
for parca in govde.split(b"--" + sinir):
    if b"\r\n\r\n" not in parca: continue
    h, icerik = parca.split(b"\r\n\r\n", 1); icerik = icerik.rstrip(b"\r\n"); h = h.decode("latin1").lower()
    if "application/json" in h: open(P + ".json", "wb").write(icerik)
    elif "audio/" in h: open(P + ".mp3", "wb").write(icerik)
os.unlink(P + ".yanit.bin")
print(AD, "tamam:", [l.strip() for l in bas.splitlines() if l.lower().startswith(("song-id", "character-cost", "request-id"))], os.path.getsize(P + ".mp3"), "bayt")
