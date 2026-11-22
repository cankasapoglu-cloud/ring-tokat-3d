#!/usr/bin/env python3
"""Söz denetimi: şarkıyı ElevenLabs Scribe ile yazıya döker, söz dosyasıyla sözcük sözcük karşılaştırır,
satır başlangıçlarını şarkı üretiminin verdiği sözcük zamanlarıyla kıyaslar ve ses yüksekliğini ölçer.
Kullanım: python3 soz_denetle.py <şarkı klasörü> <şarkı adı (örn. deneme_1)>
Çıktı: <ad>.scribe.json ve ekrana özet. API anahtarı ağ geçidinde eklenir (başlıktaki değer yer tutucudur)."""
import difflib, json, os, re, subprocess, sys
D = os.path.abspath(sys.argv[1]); AD = sys.argv[2]; P = os.path.join(D, AD)
S = json.load(open(os.path.join(D, "sozler.json"), encoding="utf8"))
def sade(s): return re.sub(r"[^a-zçğıöşüâ0-9]", "", s.replace("I", "ı").replace("İ", "i").lower().replace("â", "a"))
if not os.path.exists(P + ".scribe.json"):
    r = subprocess.run(["curl", "-sS", "-m", "300", "-X", "POST", "https://api.elevenlabs.io/v1/speech-to-text", "-H", "xi-api-key: proxy-injected",
                        "-F", "model_id=scribe_v1", "-F", "language_code=tr", "-F", "timestamps_granularity=word", "-F", "tag_audio_events=true",
                        "-F", "file=@" + P + ".mp3", "-o", P + ".scribe.json", "-w", "%{http_code}"], capture_output=True, text=True)
    if r.stdout.strip() != "200": print("HATA", r.stdout, open(P + ".scribe.json").read()[:300]); os.unlink(P + ".scribe.json"); sys.exit(1)
sc = json.load(open(P + ".scribe.json", encoding="utf8"))
duyulan = [(sade(w["text"]), w["start"]) for w in sc["words"] if w.get("type") == "word" and sade(w["text"])]
olay = [w["text"] for w in sc["words"] if w.get("type") == "audio_event"]
W = json.load(open(P + ".json", encoding="utf8"))["words_timestamps"]
satirlar, beklenen, i = [], [], 0
for b in S["bolumler"]:
    for satir in b["satirlar"]:
        n = len(satir.split()); satirlar.append((satir, i, n, W[i]["start_ms"] / 1000 if i < len(W) else None)); beklenen += [sade(x) for x in satir.split()]; i += n
uretim_sozcuk = [sade(w["word"]) for w in W]
print(f"== {os.path.basename(D)} / {AD}: beklenen {len(beklenen)} sözcük, üretimin zaman listesi {len(W)}, Scribe {len(duyulan)}" + ("" if uretim_sozcuk == beklenen else "  !! zaman listesi sözlerle birebir değil"))
es = difflib.SequenceMatcher(a=beklenen, b=[d[0] for d in duyulan], autojunk=False)
karsilik = {}
for a0, b0, n in es.get_matching_blocks():
    for k in range(n): karsilik[a0 + k] = b0 + k
yanlis, kayma = 0, []
for satir, i0, n, t_uretim in satirlar:
    eksik = [satir.split()[k] for k in range(n) if i0 + k not in karsilik]
    yanlis += len(eksik)
    if i0 in karsilik and t_uretim is not None: kayma.append(duyulan[karsilik[i0]][1] - t_uretim)
    if eksik:
        b_ilk = min([karsilik[i0 + k] for k in range(n) if i0 + k in karsilik], default=None)
        duy = " ".join(d[0] for d in duyulan[b_ilk:b_ilk + n + 1]) if b_ilk is not None else "(hiç eşleşme yok)"
        print(f"  farklı duyulan: «{satir}»  eşleşmeyen: {eksik}  | Scribe o yerde: {duy}")
fazla = len(duyulan) - len(karsilik)
print(f"  eşleşmeyen sözcük {yanlis}/{len(beklenen)}, Scribe'ın fazladan duyduğu {fazla}; ses olayları: {olay[:6]}")
if kayma: print(f"  satır başı farkı (Scribe - üretim zamanı): ortalama {sum(kayma) / len(kayma):+.2f} sn, en büyük {max(kayma, key=abs):+.2f} sn ({len(kayma)}/{len(satirlar)} satır)")
olc = subprocess.run(["ffmpeg", "-v", "info", "-i", P + ".mp3", "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True).stderr
print("  ses:", re.findall(r"I:\s+(-?[\d.]+) LUFS", olc)[-1], "LUFS, tepe", re.findall(r"Peak:\s+(-?[\d.]+) dBFS", olc)[-1], "dBFS, ilk söz", f"{W[0]['start_ms'] / 1000:.2f} sn, son söz biter {W[-1]['end_ms'] / 1000:.2f} sn")
json.dump({"eslesmeyen": yanlis, "beklenen": len(beklenen), "fazla": fazla, "kayma_en_buyuk": max(kayma, key=abs) if kayma else None}, open(P + ".denetim.json", "w"))
